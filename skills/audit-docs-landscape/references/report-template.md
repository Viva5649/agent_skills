# Landscape report template

Use this template at the reporting step. Translate headings and labels into the report's
language. Replace placeholders with evidence, retain every section, and write "None"
with a reason for empty sections. Repeat finding blocks in order of who gets stuck and
how soon. Mark unsupported Reader/Purpose judgments as undetermined.

---

# Documentation landscape audit

- Date: <YYYY-MM-DD>
- Repository/workspace: <reviewed root>
- Requested coverage: <repository and any explicit exclusions>
- Actual coverage: <directories, documents, and code evidence inspected; limits>
- Selected entry point: <path, or absent>

## Documentation inventory, readers, and purposes

| Document or proposed gap | Existing / proposed | Reader | Purpose | Evidence source |
| --- | --- | --- | --- | --- |
| <path or missing documentation> | <status> | <situation and goal> | <purpose> | <location and supporting evidence> |

## Findings in priority order

### <finding title>

- Gap: <missing documentation or specific navigation problem>
- Code evidence: <concrete path or artifact creating the need>
- Who gets stuck, and when: <Reader and triggering moment>
- Owner: <codebase-documenter / domain-modeling / spec-miner>

## Probe coverage

| Probe | Outcome | Evidence and result, or reason it could not run |
| --- | --- | --- |
| Module boundaries | <finding / no gap / not run> | <details> |
| Non-obvious technology choices | <finding / no gap / not run> | <details> |
| Manual operational actions | <finding / no gap / not run> | <details> |
| Multiple run modes | <finding / no gap / not run> | <details> |
| External contracts | <finding / no gap / not run> | <details> |

## Navigation coverage

| Check | Outcome | Evidence and result, or reason it could not run |
| --- | --- | --- |
| Orphan documents | <finding / no finding / not run> | <details> |
| Documents unreachable from the entry point | <finding / no finding / not run> | <details> |
| Entry-point conflict | <finding / no finding / not run> | <details> |
| Broken links | <finding / no finding / not run> | <details> |

## Evidence verification

- Method: <self-verification by the auditing agent; state any additional review actually performed>
- Evidence checked: <searches for allegedly missing content, code evidence, reproduced navigation findings, and probe/check coverage>
- Corrections: <findings removed or corrected, or none>
- Unverified items: <claims/checks and reasons, or none; do not present these as confirmed findings>

Verification covers the evidence and scope listed here; it does not guarantee that no
issues were missed.

## Limitations and unverified coverage

Only links between tracked Markdown files were counted. Documents reached through code
comments, external sites, or chat messages may therefore be reported as Orphans.

<Additional exclusions, unavailable evidence, unsupported Reader/Purpose judgments,
and any coverage limits. If there is no entry point, state that link traversal did not run.>
