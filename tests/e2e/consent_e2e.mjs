// Production E2E for a brand-new person: before sign-up the agent connects to /mcp and gets CONSENT_REQUIRED; after
// sign-up it finds a Thegram vault made for it and writes inbox.gram there. It deletes the E2E mailbox account first
// so Logto creates it fresh, and deletes that account and its Thegram vault again at the end.
// Usage: NODE_PATH=<dir with puppeteer-core> node tests/e2e/consent_e2e.mjs <evidence-dir>   (env THEGRAM_SERVER, THEGRAM_E2E_MAILBOX, THEGRAM_VAULT_REPO for e2e/imap_code.py)
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const server = (process.env.THEGRAM_SERVER || 'https://vault.thegram.one').replace(/\/$/, '');
const mailbox = process.env.THEGRAM_E2E_MAILBOX || 'vaulte2ea@thegram.one';
const vaultRepo = process.env.THEGRAM_VAULT_REPO || path.join(os.homedir(), 'thegram/thegram-vault');
const evidence = process.argv[2];
if (!evidence) throw new Error('usage: consent_e2e.mjs <evidence-dir>');
const puppeteer = createRequire(import.meta.url)('puppeteer-core');
const chrome = process.env.THEGRAM_E2E_CHROME || '/Users/steve/.omp/puppeteer/chrome/mac_arm-150.0.7871.24/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const apiResource = server + '/api';
const mcpResource = server + '/mcp';
const report = { server, mailbox, result: 'failed', startedAt: new Date().toISOString(), steps: [] };
const step = (name, data) => { report.steps.push({ name, ...data }); console.log(name, JSON.stringify(data)); };

const config = await (await fetch(server + '/v1/config')).json();
const clientID = config.oidc.desktop_client_id;
const challenge401 = await fetch(server + '/mcp', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' }, body: '{"jsonrpc":"2.0","id":0,"method":"tools/list"}' });
const resourceMetadata = /resource_metadata="([^"]+)"/.exec(challenge401.headers.get('www-authenticate') || '')?.[1];
assert(resourceMetadata, 'no resource_metadata in the /mcp 401 challenge');
const prm = await (await fetch(resourceMetadata)).json();
const oidc = await (await fetch(prm.authorization_servers[0].replace(/\/$/, '') + '/.well-known/openid-configuration')).json();

// Logto asks whether to create an account for an unknown email and may require its own terms checkbox.
async function answerLogtoPrompt(page) {
  return page.evaluate(() => {
    const box = document.querySelector('[class*="terms"] input[type="checkbox"]');
    if (box && !box.checked) (box.closest('label') || box.parentElement).click();
    const modal = document.querySelector(".ReactModalPortal [role='dialog'], .ReactModal__Content");
    if (!modal) return false;
    const check = modal.querySelector("input[type='checkbox']");
    if (check && !check.checked) (check.closest('label') || check.parentElement).click();
    const confirm = [...modal.querySelectorAll('button')].at(-1);
    confirm?.click();
    return Boolean(confirm);
  });
}

async function signIn(browser, resource) {
  // A fresh context per sign-in so a deleted Logto user's session never carries into the next one.
  const context = await browser.createBrowserContext();
  const page = await context.newPage();
  let callback;
  const redirectServer = http.createServer((req, res) => {
    const u = new URL(req.url, 'http://127.0.0.1');
    res.end('done');
    if (u.pathname === '/callback') callback = Object.fromEntries(u.searchParams);
  });
  await new Promise(resolve => redirectServer.listen(0, '127.0.0.1', resolve));
  try {
    const redirectURI = `http://127.0.0.1:${redirectServer.address().port}/callback`;
    const verifier = crypto.randomBytes(32).toString('base64url');
    const state = crypto.randomBytes(16).toString('base64url');
    const url = new URL(oidc.authorization_endpoint);
    for (const [k, v] of Object.entries({ client_id: clientID, redirect_uri: redirectURI, response_type: 'code', scope: prm.scopes_supported.join(' '), resource, prompt: 'consent', first_screen: 'identifier:sign_in', ui_locales: 'en', state, code_challenge: crypto.createHash('sha256').update(verifier).digest('base64url'), code_challenge_method: 'S256' })) url.searchParams.set(k, v);
    const since = Date.now();
    await page.goto(url.toString(), { waitUntil: 'domcontentloaded' });
    let typedEmail = false, typedCode = false;
    for (let i = 0; i < 240 && !callback; i += 1) {
      const where = await page.evaluate(() => location.pathname).catch(() => '');
      if (!typedEmail && await page.$('input[name="identifier"]')) {
        await page.type('input[name="identifier"]', mailbox);
        await answerLogtoPrompt(page);
        await page.keyboard.press('Enter');
        typedEmail = true;
      } else if (!typedCode && where.endsWith('/verification-code')) {
        const code = execFileSync('python3', [path.join(vaultRepo, 'e2e/imap_code.py'), mailbox, String(since / 1000)], { encoding: 'utf8' }).trim();
        assert.match(code, /^\d{6}$/, 'IMAP helper returned no code');
        await page.keyboard.type(code);
        typedCode = true;
      } else if (where.endsWith('/consent')) {
        await page.evaluate(() => [...document.querySelectorAll('button')].find(b => /authorize|allow|continue|동의|허용/i.test(b.textContent))?.click());
      }
      const answered = await answerLogtoPrompt(page).catch(() => false);
      await new Promise(r => setTimeout(r, answered ? 1200 : 500));
    }
    assert(callback?.code && callback.state === state, `no authorization code (${JSON.stringify(callback)}, at ${page.url()})`);
    const res = await fetch(oidc.token_endpoint, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ grant_type: 'authorization_code', client_id: clientID, code: callback.code, redirect_uri: redirectURI, code_verifier: verifier, resource }) });
    assert.equal(res.status, 200, `token exchange ${res.status}`);
    return { token: (await res.json()).access_token, emailCodeUsed: typedCode };
  } finally {
    redirectServer.close();
    await context.close();
  }
}

async function deleteAccount(browser, label) {
  const { token, emailCodeUsed } = await signIn(browser, apiResource);
  const auth = { Authorization: `Bearer ${token}` };
  const me = await (await fetch(server + '/v1/me', { headers: auth })).json();
  // The agent's default vault is owned by this account and would block DELETE /v1/me with 409 owns_vaults.
  const removedVaults = [];
  const listed = await fetch(server + '/v1/vaults', { headers: auth });
  if (listed.status === 200) {
    for (const v of (await listed.json()).vaults || []) {
      if (v.name !== 'Thegram' || v.role !== 'owner') continue;
      const meta = await (await fetch(`${server}/v1/vaults/${v.id}`, { headers: auth })).json();
      const del = await fetch(`${server}/v1/vaults/${v.id}`, { method: 'DELETE', headers: { ...auth, 'If-Match': meta.policy_etag } });
      removedVaults.push({ id: v.id, status: del.status });
    }
  }
  const del = await fetch(server + '/v1/me', { method: 'DELETE', headers: auth });
  step(label, { principal: me.principal || me.id, consentRequiredBefore: me.consent_required, emailCodeUsed, removedVaults, deleteStatus: del.status, deleteBody: del.status === 204 ? '' : (await del.text()).slice(0, 200) });
  assert.equal(del.status, 204, `${label}: DELETE /v1/me ${del.status}`);
}

async function rpc(token, sessionID, id, method, params) {
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18' };
  if (sessionID) headers['Mcp-Session-Id'] = sessionID;
  const res = await fetch(server + '/mcp', { method: 'POST', headers, body: JSON.stringify({ jsonrpc: '2.0', ...(id === null ? {} : { id }), method, params }) });
  const text = await res.text();
  const data = text.startsWith('{') ? JSON.parse(text) : JSON.parse(/^data: (.*)$/m.exec(text)?.[1] || 'null');
  return { status: res.status, sessionID: res.headers.get('mcp-session-id') || sessionID, data };
}

let browser, profile;
try {
  profile = await fs.mkdtemp(path.join(os.tmpdir(), 'thegram-consent-e2e-'));
  browser = await puppeteer.launch({ executablePath: chrome, headless: true, userDataDir: profile, args: ['--no-first-run', '--no-default-browser-check'] });
  await deleteAccount(browser, 'resetAccount');
  const { token, emailCodeUsed } = await signIn(browser, mcpResource);
  const init = await rpc(token, null, 1, 'initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'thegram-consent-e2e', version: '1' } });
  assert.equal(init.status, 200, `initialize ${init.status}`);
  await rpc(token, init.sessionID, null, 'notifications/initialized', {});
  const list = await rpc(token, init.sessionID, 2, 'tools/list', {});
  const call = await rpc(token, init.sessionID, 3, 'tools/call', { name: 'gram_projects', arguments: {} });
  const error = call.data?.result?.structuredContent?.error;
  step('freshAccountOverMCP', { emailCodeUsed, initializeStatus: init.status, server: init.data?.result?.serverInfo, toolsListStatus: list.status, tools: list.data?.result?.tools?.length, callStatus: call.status, isError: call.data?.result?.isError, error });
  assert.equal(list.status, 200, 'tools/list');
  const hints = Object.fromEntries((list.data?.result?.tools || []).map(t => [t.name, t.annotations]));
  step('toolAnnotations', { hints });
  for (const [name, a] of Object.entries(hints)) {
    const writes = name === 'gram_create' || name === 'gram_patch';
    assert.equal(a.readOnlyHint, !writes, `${name} read-only safety hint`);
    assert.equal(a.destructiveHint, name === 'gram_patch', `${name} destructive safety hint`);
    assert.equal(a.openWorldHint, false, `${name} external-interaction safety hint`);
  }
  assert.equal(Object.keys(hints).length, 15, 'tool count');
  assert.equal(call.data?.result?.isError, true, 'tools/call should fail');
  assert.equal(error?.code, 'CONSENT_REQUIRED');
  assert(error.message.includes(server + '/'), 'message lacks the sign-up URL');

  // Finishing sign-up is all a new person does; the agent then finds a Thegram vault made for it and writes there.
  const api = await signIn(browser, apiResource);
  const consent = await fetch(server + '/v1/me/consent', { method: 'POST', headers: { Authorization: `Bearer ${api.token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ birthdate: '1990-05-17', terms: true, privacy: true, disclaimer: true }) });
  assert.equal(consent.status, 200, `consent ${consent.status}`);
  const projects = await rpc(token, init.sessionID, 4, 'tools/call', { name: 'gram_projects', arguments: {} });
  const vaults = (projects.data?.result?.structuredContent?.mounts || []).filter(m => m.kind === 'vault');
  const vault = vaults.find(m => m.name === 'Thegram' && m.access === 'write');
  const created = vault && await rpc(token, init.sessionID, 5, 'tools/call', { name: 'gram_create', arguments: { path: `${vault.key}/inbox.gram`, title: 'Inbox', base_revision: null, content: { text: '# Log\n' } } });
  const createdDoc = created?.data?.result?.structuredContent;
  step('afterSignUpDefaultVault', { consentStatus: consent.status, vaults, isError: projects.data?.result?.isError, inbox: createdDoc?.doc, sync: createdDoc?.sync, createError: createdDoc?.error });
  assert(vault, 'no writable Thegram vault after sign-up');
  assert.equal(vaults.length, 1, 'more than one vault was created');
  assert.equal(createdDoc?.sync?.state, 'synced', 'inbox.gram did not sync to the vault');
  report.result = 'passed';
} catch (e) {
  report.error = String(e?.message || e);
} finally {
  try {
    if (browser) await deleteAccount(browser, 'cleanupAccount');
  } catch (e) {
    report.cleanupError = String(e?.message || e);
    report.result = 'failed';
  }
  await browser?.close();
  if (profile) await fs.rm(profile, { recursive: true, force: true });
  report.completedAt = new Date().toISOString();
  await fs.mkdir(evidence, { recursive: true });
  await fs.writeFile(path.join(evidence, 'consent-e2e-report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log('result', report.result, report.error || '', report.cleanupError || '');
  process.exitCode = report.result === 'passed' ? 0 : 1;
}
