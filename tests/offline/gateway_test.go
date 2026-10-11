package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// The runner copies this test alongside the actual cloud gateway source. All
// mounts, storage and failures here are synthetic and confined to t.TempDir().
type offlineStore struct {
	root, id    string
	remote      map[string][]byte
	writable    bool
	conflicting map[string][]byte
	commits     int
}

func (s *offlineStore) Open(_ context.Context, _ bool) (Workspace, error) {
	for name, data := range s.remote {
		if err := os.WriteFile(filepath.Join(s.root, name), data, 0600); err != nil {
			return nil, err
		}
	}
	return s, nil
}
func (s *offlineStore) Mounts(context.Context) ([]Mount, error) {
	return []Mount{{ID: s.id, Kind: "vault", Name: "Synthetic offline vault", Root: s.root, Writable: s.writable}}, nil
}
func (s *offlineStore) Release() {}
func (s *offlineStore) Commit(_ context.Context, file string) error {
	if s.conflicting != nil {
		s.remote = s.conflicting
		s.conflicting = nil
		for name, data := range s.remote {
			if err := os.WriteFile(filepath.Join(s.root, name), data, 0600); err != nil {
				return err
			}
		}
		return fail("STORAGE_CONFLICT", "synthetic provider changed since read; restored authoritative scratch state")
	}
	data, err := os.ReadFile(file)
	if err != nil {
		return err
	}
	s.remote[filepath.Base(file)] = append([]byte(nil), data...)
	s.commits++
	return nil
}

type offlineFixture struct {
	Create    map[string]any   `json:"create"`
	Patches   []map[string]any `json:"patches"`
	Retrieval []map[string]any `json:"retrieval"`
	Readback  []map[string]any `json:"readback"`
}
type offlineHarness struct {
	t     *testing.T
	g     *gateway
	store *offlineStore
	path  string
	doc   map[string]any
}

func cloneMap(v map[string]any) map[string]any {
	b, _ := json.Marshal(v)
	var out map[string]any
	_ = json.Unmarshal(b, &out)
	return out
}
func callArguments(v map[string]any) map[string]any {
	if args, ok := v["arguments"].(map[string]any); ok {
		return cloneMap(args)
	}
	if args, ok := v["args"].(map[string]any); ok {
		return cloneMap(args)
	}
	args := cloneMap(v)
	for _, key := range []string{"name", "tool", "label", "description"} {
		delete(args, key)
	}
	return args
}
func (h *offlineHarness) call(tool string, args map[string]any) map[string]any {
	h.t.Helper()
	result, err := h.g.run(context.Background(), tool, args)
	if err != nil {
		h.t.Fatalf("%s: %v", tool, err)
	}
	// Mirror JSON-RPC encoding so direct gateway results have the public shapes.
	result = cloneMap(result)
	if doc, ok := result["doc"].(map[string]any); ok {
		h.doc = doc
	}
	if tool == "gram_create" || tool == "gram_patch" {
		if result["sync"].(map[string]any)["state"] != "synced" {
			h.t.Fatalf("unsynced write: %#v", result)
		}
	}
	return result
}
func (h *offlineHarness) fail(tool string, args map[string]any, code string) {
	h.t.Helper()
	_, err := h.g.run(context.Background(), tool, args)
	failure, ok := err.(*ToolFailure)
	if !ok || failure.Code != code {
		h.t.Fatalf("%s wanted %s, got %v", tool, code, err)
	}
}
func (h *offlineHarness) patch(args map[string]any) map[string]any {
	args = callArguments(args)
	args["path"], args["base_revision"], args["expected_hash"] = h.path, h.doc["rev"], h.doc["hash"]
	return args
}
func (h *offlineHarness) simplePatch(id string, operations ...any) map[string]any {
	return h.patch(map[string]any{"request_id": id, "operations": operations})
}
func (h *offlineHarness) entity(id string, revision ...int) map[string]any {
	args := map[string]any{"path": h.path, "entity": id, "fields": []any{"t", "d", "x", "p", "owner", "tag", "due", "at", "value", "unit", "observed", "source", "ref", "s", "view", "motion", "color"}, "links": true}
	if len(revision) > 0 {
		args["revision"] = revision[0]
	}
	return h.call("gram_get", args)["entity"].(map[string]any)
}
func field(e map[string]any, key string) any {
	if fields, ok := e["fields"].(map[string]any); ok {
		return fields[key]
	}
	return nil
}
func first(e map[string]any, key string) string {
	values, _ := field(e, key).([]any)
	if len(values) > 0 {
		return fmt.Sprint(values[0])
	}
	return ""
}
func (h *offlineHarness) assertField(id, key string, want any, revision ...int) {
	h.t.Helper()
	got := field(h.entity(id, revision...), key)
	if !reflect.DeepEqual(got, want) {
		h.t.Fatalf("%s.%s: want %#v, got %#v", id, key, want, got)
	}
}
func hasLink(e map[string]any, pred, target string) bool {
	for _, raw := range asSlice(e["links"]) {
		pair := asSlice(raw)
		if len(pair) == 2 && pair[0] == pred && pair[1] == target {
			return true
		}
	}
	return false
}
func (h *offlineHarness) body() string {
	h.t.Helper()
	outline := h.call("gram_read", map[string]any{"path": h.path})
	var sections []string
	for _, raw := range asSlice(outline["outline"]) {
		row := asSlice(raw)
		if len(row) < 3 || row[2] == nil {
			continue
		}
		out := h.call("gram_read", map[string]any{"path": h.path, "section": row[2]})
		if out["more"] != nil {
			h.t.Fatal("synthetic section unexpectedly exceeds budget")
		}
		sections = append(sections, fmt.Sprint(out["md"]))
	}
	return strings.Join(sections, "\n\n")
}
func (h *offlineHarness) verifyOperations(args map[string]any) {
	h.t.Helper()
	for _, raw := range asSlice(args["operations"]) {
		op := raw.(map[string]any)
		switch op["op"] {
		case "edit-text":
			if !strings.Contains(strings.Join(strings.Fields(h.body()), " "), strings.Join(strings.Fields(op["new"].(string)), " ")) {
				h.t.Fatalf("body edit missing: %#v", op)
			}
		case "set":
			h.assertField(op["entity"].(string), op["key"].(string), []any{op["value"]})
		case "link":
			if !hasLink(h.entity(op["entity"].(string)), op["predicate"].(string), op["target"].(string)) {
				h.t.Fatalf("missing link: %#v", op)
			}
		case "add":
			record := op["record"].(map[string]any)
			id := record["id"].(string)
			entity := h.entity(id)
			if entity["type"] != record["type"] {
				h.t.Fatalf("wrong type for %s", id)
			}
			for key, want := range record["fields"].(map[string]any) {
				h.assertField(id, key, want)
			}
			for _, rawLink := range asSlice(record["links"]) {
				pred, target := "", ""
				if pair, ok := rawLink.([]any); ok {
					pred, target = pair[0].(string), pair[1].(string)
				} else {
					link := rawLink.(map[string]any)
					pred, target = link["predicate"].(string), link["target"].(string)
				}
				if !hasLink(entity, pred, target) {
					h.t.Fatalf("missing %s %s on %s", pred, target, id)
				}
				if record["type"] == "event" && pred == "implements" {
					at := first(entity, "at")
					if len(at) >= 10 && h.entity(target)["implemented"] != at[:10] {
						h.t.Fatalf("decision %s implementation date does not match event %s", target, id)
					}
				}
			}
			if place, ok := op["place"].(map[string]any); ok && place["section"] != nil {
				read := h.call("gram_read", map[string]any{"path": h.path, "section": place["section"]})
				if !strings.Contains(fmt.Sprint(read["md"]), id) {
					h.t.Fatalf("record %s not placed in section", id)
				}
			}
		}
	}
}

func TestOfflineLifecycle(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("THEGRAM_LIFECYCLE_FIXTURE"))
	if err != nil {
		t.Fatal(err)
	}
	var fixture offlineFixture
	if err = json.Unmarshal(data, &fixture); err != nil {
		t.Fatal(err)
	}
	create := callArguments(fixture.Create)
	path, _ := create["path"].(string)
	parts := strings.Split(path, "/")
	if len(parts) != 3 || parts[0] != "@mounts" {
		t.Fatal("fixture must use one synthetic top-level mount document")
	}
	store := &offlineStore{root: t.TempDir(), id: parts[1], remote: map[string][]byte{}, writable: true}
	h := &offlineHarness{t: t, g: &gateway{spaces: store, core: newCore(os.Getenv("GRAM_CORE_BINARY"))}, store: store, path: path}
	t.Run("create_and_scope", func(t *testing.T) {
		h.t = t
		h.call("gram_create", create)
		h.call("gram_projects", map[string]any{})
		h.call("gram_capabilities", map[string]any{})
		bad := cloneMap(create)
		bad["path"] = "@mounts/unknown/offline.gram"
		h.fail("gram_create", bad, "E_PATH")
		bad["path"] = "@mounts/" + store.id + "/nested/offline.gram"
		h.fail("gram_create", bad, "E_PATH")
		bad = cloneMap(create)
		bad["path"] = "@mounts/" + store.id + "/readonly.gram"
		store.writable = false
		h.fail("gram_create", bad, "E_READ_ONLY")
		store.writable = true
		bad = cloneMap(create)
		bad["request_id"] = "unsupported-create-id"
		h.fail("gram_create", bad, "E_ARGUMENT")
	})
	var patchPayloads []map[string]any
	for i, raw := range fixture.Patches {
		t.Run(fmt.Sprintf("fixture_patch_%d", i+1), func(t *testing.T) {
			h.t = t
			payload := h.patch(raw)
			h.call("gram_patch", payload)
			h.verifyOperations(payload)
			patchPayloads = append(patchPayloads, payload)
		})
	}
	if len(patchPayloads) == 0 {
		t.Fatal("fixture needs patches")
	}
	t.Run("selective_retrieval", func(t *testing.T) {
		h.t = t
		commits := store.commits
		before := append([]byte(nil), store.remote[parts[2]]...)
		for _, raw := range append(fixture.Retrieval, fixture.Readback...) {
			tool, _ := raw["tool"].(string)
			if tool == "" {
				tool, _ = raw["name"].(string)
			}
			if tool == "gram_create" || tool == "gram_patch" {
				t.Fatal("retrieval fixture must be read-only")
			}
			args := callArguments(raw)
			out := h.call(tool, args)
			if tool == "gram_recall" && len(asSlice(out["hits"])) == 0 {
				t.Fatal("fixture recall found no synthetic records")
			}
			if tool == "gram_context" && len(asSlice(out["items"])) == 0 {
				t.Fatal("fixture context found no synthetic records")
			}
			if tool == "gram_relations" && len(asSlice(out["edges"])) == 0 {
				t.Fatal("fixture relations returned no explicit links")
			}
		}
		if store.commits != commits || !reflect.DeepEqual(before, store.remote[parts[2]]) {
			t.Fatal("read-only retrieval committed a write")
		}
	})
	t.Run("idempotency_and_changed_intent", func(t *testing.T) {
		h.t = t
		before := append([]byte(nil), store.remote[parts[2]]...)
		replay := h.call("gram_patch", patchPayloads[0])
		if replay["receipt"].(map[string]any)["replayed"] != true {
			t.Fatal("identical patch not replayed")
		}
		if !reflect.DeepEqual(before, store.remote[parts[2]]) {
			t.Fatal("replay changed storage")
		}
		changed := cloneMap(patchPayloads[0])
		changed["operations"] = []any{map[string]any{"op": "set", "entity": "doc", "key": "d", "value": "Different intended change"}}
		h.fail("gram_patch", changed, "E_REQUEST_REUSE")
		if !reflect.DeepEqual(before, store.remote[parts[2]]) {
			t.Fatal("changed request ID intent changed storage")
		}
	})
	t.Run("placement_and_body_edits", func(t *testing.T) {
		h.t = t
		add := map[string]any{"op": "add", "record": map[string]any{"type": "evidence", "id": "ev-offline-placement", "fields": map[string]any{"t": []any{"Synthetic placement check"}, "d": []any{"Only scratch records are used."}}}, "place": map[string]any{"section": "Log"}}
		body := map[string]any{"op": "edit-text", "entity": "doc", "kind": "rich", "old": "# Overview", "new": "# Overview\n\nSynthetic harness annotation."}
		h.fail("gram_patch", h.simplePatch("offline-invalid-combined", add, body), "E_ARGUMENT")
		h.call("gram_patch", h.simplePatch("offline-place", add))
		h.call("gram_patch", h.simplePatch("offline-body", body))
		read := h.call("gram_read", map[string]any{"path": path, "section": "Overview"})
		if !strings.Contains(fmt.Sprint(read["md"]), "Synthetic harness annotation.") {
			t.Fatal("separate body patch missing")
		}
	})
	t.Run("stale_revision_preserves_concurrent_change", func(t *testing.T) {
		h.t = t
		stale := h.simplePatch("offline-stale", map[string]any{"op": "set", "entity": "doc", "key": "d", "value": "Stale overwrite"})
		h.call("gram_patch", h.simplePatch("offline-concurrent", map[string]any{"op": "set", "entity": "doc", "key": "d", "value": "Concurrent writer caveat"}))
		h.fail("gram_patch", stale, "STALE_REVISION")
		h.assertField("doc", "d", []any{"Concurrent writer caveat"})
		h.call("gram_patch", h.simplePatch("offline-reconciled", map[string]any{"op": "set", "entity": "doc", "key": "tag", "value": "reconciled"}))
		h.assertField("doc", "d", []any{"Concurrent writer caveat"})
	})
	t.Run("storage_conflict_restores_and_reconciles", func(t *testing.T) {
		h.t = t
		remote := string(store.remote[parts[2]])
		head, err := h.g.core.request(context.Background(), map[string]any{"op": "resolve-state", "source": remote})
		if err != nil {
			t.Fatal(err)
		}
		changed, err := h.g.core.request(context.Background(), map[string]any{"op": "patch", "source": remote, "base_revision": head["revision"], "expected_hash": head["file_hash"], "request_id": "offline-provider-change", "operations": []any{map[string]any{"op": "set", "entity": "doc", "key": "d", "value": "Provider writer caveat"}}})
		if err != nil {
			t.Fatal(err)
		}
		store.conflicting = map[string][]byte{parts[2]: []byte(changed["source"].(string))}
		h.fail("gram_patch", h.simplePatch("offline-storage-conflict", map[string]any{"op": "set", "entity": "doc", "key": "d", "value": "Attempted provider overwrite"}), "STORAGE_CONFLICT")
		h.assertField("doc", "d", []any{"Provider writer caveat"})
		h.call("gram_patch", h.simplePatch("offline-provider-reconciled", map[string]any{"op": "set", "entity": "doc", "key": "tag", "value": "provider-reconciled"}))
		h.assertField("doc", "d", []any{"Provider writer caveat"})
	})
	t.Run("history_sources_relations_and_metric", func(t *testing.T) {
		h.t = t
		content := create["content"].(map[string]any)
		for _, raw := range asSlice(content["records"]) {
			record := raw.(map[string]any)
			id := record["id"].(string)
			if record["type"] == "metric" {
				fields := record["fields"].(map[string]any)
				for _, key := range []string{"value", "unit", "observed"} {
					h.assertField(id, key, fields[key], 0)
				}
				if first(h.entity(id), "observed") == fmt.Sprint(asSlice(fields["observed"])[0]) {
					t.Fatal("metric observation did not evolve")
				}
			}
		}
		state := h.call("gram_state", map[string]any{"path": path, "selector": map[string]any{"revision": 0}})
		if numberOrZero(state["at"].(map[string]any)["rev"]) != 0 {
			t.Fatal("past-state selector did not return initial revision")
		}
		rangeOut := h.call("gram_range", map[string]any{"path": path, "start": 0})
		if len(asSlice(rangeOut["events"])) < len(fixture.Patches)+1 {
			t.Fatal("missing recorded lifecycle history")
		}
		for _, raw := range asSlice(rangeOut["events"]) {
			event := raw.(map[string]any)
			if event["effective_at"] != nil {
				t.Fatal("fixture import was backdated")
			}
			if event["recorded_at"] == nil {
				t.Fatal("history lacks actual recording time")
			}
		}
		files := h.call("gram_list", map[string]any{"path": path})
		_ = files
		current, err := h.g.core.request(context.Background(), map[string]any{"op": "current", "path": filepath.Join(store.root, parts[2])})
		if err != nil {
			t.Fatal(err)
		}
		records := asSlice(current["ir"].(map[string]any)["records"])
		types := map[string]string{}
		for _, raw := range records {
			e := raw.(map[string]any)
			types[e["id"].(string)] = e["type"].(string)
		}
		for _, raw := range records {
			e := raw.(map[string]any)
			for _, source := range asSlice(e["fields"].(map[string]any)["source"]) {
				if types[source.(string)] != "source" {
					t.Fatalf("invalid source record: %v", source)
				}
			}
		}
		changes := h.call("gram_changes", map[string]any{"path": path, "since_revision": 0})
		if len(asSlice(changes["changes"])) == 0 && len(asSlice(changes["events"])) == 0 {
			t.Fatal("no subsequent changes returned")
		}
	})
}
