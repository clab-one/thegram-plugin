# Memory authoring patterns

These patterns describe useful structure, not a sample record count or permission to import someone else's data.

- Engineering: explain purpose, current components, meaningful changes and unresolved work. Count commits only with a named command and scope; classify each supported fact by meaning; commits are provenance, with no automatic event or task.
- Operations: keep current risks, incident boundaries, decisions and verifying evidence distinct. A changed threshold should link to the choice it replaces and scoped implementation/verification evidence when available.
- Research: preserve source attribution, disagreement and dates. Link evidence to the claim it supports or contradicts; a chronological sequence alone does not prove causation.
- Shared plans: explain accepted choices, replaced choices and remaining steps. A decision is not implemented merely because it is accepted; require implementation evidence; add an event only for a meaningful sourced occurrence.
- Metrics: define the measured quantity, denominator, unit, observation window and source. Reuse one metric ID for repeated observations and disclose incomparable units or windows.

Use standalone record placements, inline mentions, explicit links and filtered collections only according to the current `gram_profile`. A collection is a document projection, not a dashboard widget. The current rich collection views are list and table. Document, dashboard and graph rendering is a host capability, not a promise of the storage transport or plugin.

Revision recording time reflects when information was actually recorded; sourced event time and effective time are separate. Do not fabricate recording history, backdate an import or rebuild a document to imitate a sample.

Do not imitate record counts, revision counts, repeated inspection events or link density as quality targets. Explain what changed and why, retain uncertainty, and put evidence near the supported claims so readers can understand purpose, state, reasons and remaining work.

Write records that survive retrieval outside their document: a concise `t` identifies the subject and claim, and a short `d` retains scope, essential conditions, exceptions and uncertainty from the source. For illustration only, if a source explicitly chooses monthly subscriptions for Cedar's paid team plan while leaving its personal plan free, "Pricing decision / Bill monthly" loses the subject and boundary; "Cedar paid team plan uses monthly subscriptions / Monthly billing applies to Cedar's paid team plan; the personal plan remains free" preserves them. Never introduce these details unless the source establishes them, and never add search terms as a list.

After important material is saved and read back, ask a representative natural question and open the retrieved record or section to check the answer (SKILL.md section 9). A miss calls for a source-backed clarity check or an honest retrieval limitation, not duplicate records or repeated rank tuning.
