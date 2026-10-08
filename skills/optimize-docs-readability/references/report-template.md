# Readability report template

Use this template at the reporting step. Translate headings and labels into the report's
language; write each rewrite in its document's language. Replace placeholders with
evidence, retain every section, and write "None" with a reason for empty sections.
Repeat finding blocks per document without severity rankings. If the evidence does not
support a concrete rewrite, state what information the author must supply; do not invent it.

---

# Documentation readability review

- Date: <YYYY-MM-DD>
- Repository/workspace: <reviewed root>
- Requested documents: <full repository-relative selected file list>
- Diff base: <base and reviewed range, or not applicable>
- Actual coverage: <documents reviewed and any limits>

## Readers and purposes

| Document | Reader | Purpose | Evidence source |
| --- | --- | --- | --- |
| <path> | <situation and goal, or undetermined> | <purpose, or undetermined> | <location and supporting evidence> |

## Findings by document

### <document path>

#### <finding title>

- Location: <file:line or file § heading>
- Reader loss: <concrete work transferred to this Reader>
- Criterion: <number and name>
- Rewrite:

<paste-ready replacement text; for visual recommendations, include the representation
type, insertion/replacement location, and Mermaid diagram or Markdown table>

## Evidence verification

- Method: <self-verification by the reviewing agent; state any additional review actually performed>
- Evidence checked: <source locations, Reader evidence, rewrite comparisons, source support for proposed diagrams/tables, and criterion coverage>
- Corrections: <findings removed or corrected, or none>
- Unverified items: <claims/checks and reasons, or none; do not present these as confirmed findings>

Verification covers the evidence and scope listed here; it does not guarantee that no
issues were missed.

## Skipped documents and stopped checks

| Document or check | Reason | What remains unreviewed |
| --- | --- | --- |
| <path or criterion> | <exclusion, unavailable evidence, or stop condition> | <affected coverage> |

## Criteria without findings

| Document(s) | Criterion | Outcome | Reason |
| --- | --- | --- | --- |
| <paths> | <number and name> | <checked with no finding / intrinsic difficulty / not applicable> | <evidence or explanation> |

Include every criterion that produced no finding. Checks that could not run belong in
the preceding section, not among successful checks.

## Chinese style review

Findings from `tech-doc-style-chinese` in its review mode, ordered by its own rules.
For a document outside its scope, or when the skill is not installed, write "Not run"
with the reason.

- Scope: <documents checked, and the `tech-doc-style-chinese` references read>
- Project conventions: <target project's style rules that override the defaults, or none>

| Location | Original text | Issue | Suggested text |
| --- | --- | --- | --- |
| <file:line or file § heading> | <quoted original> | <rule violated and its effect> | <replacement text> |
