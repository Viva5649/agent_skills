---
name: audit-docs-landscape
description: Audit repository-wide documentation gaps, navigation, discoverability, and newcomer reading paths. For wording or readability of individual documents, use optimize-docs-readability.
---

# Audit Docs Landscape

Inventory one repository's Doc landscape: the documentation that exists, the
documentation its code implies should exist, and whether a newcomer can navigate between
them. Report gaps and assign each one an owner. Never write documentation.

## What this skill owns

For content problems, the dividing line against `optimize-docs-readability` is whether
the information exists at all:

- The information is written down, but the document makes the Reader recover it →
  `optimize-docs-readability`.
- The information was never written anywhere → **this skill**, as a Documentation gap.

Cross-document navigation also belongs to this skill, including information already
written down in documents that cannot be reached from the entry point.

Wording is only a first approximation of the trigger. "Review this README" is the other
skill; "what are we missing" is this one. When the user's phrasing is ambiguous, decide
by the rule above.

## Never write

Report gaps and navigation problems. Apart from the review report and its output directory,
do not create, edit, move, or delete any file.
Every gap you report names the skill that should close it, so the report is a dispatch
list rather than a complaint list.

By default, save the full report to `.scratch/docs-review/<date>-landscape-<repository>.md`, relative
to the reviewed repository's root (or the workspace root when there is no Git repository).
Resolve that root from the review target, never from the skill installation directory or
a machine-specific path. Create the output directory if it does not exist.
Use `YYYY-MM-DD` for the date. For `<repository>`, use the reviewed repository root directory's name.
Replace whitespace and filename-invalid characters (`/ \ : * ? " < > |`) in the name
with hyphens. If the path already exists, append `-2`, `-3`, etc. before `.md` rather
than overwrite it.
Return a brief summary and a link to the saved report in the conversation. Honor an
explicit output path or a request not to save. If saving fails, deliver the full report
in the conversation and state that it was not saved, with the reason.

## The rule that makes this useful

**Every gap must be derived from named code evidence.** A gap you cannot trace to a
concrete path, dependency, route, or script does not get reported. Without this rule the
output degrades into a generic checklist — "you have no CONTRIBUTING.md" — which is
noise the user could have generated without reading their repository.

## Process

### 1. Map what exists

List the repository's documentation: `README` at every level, Markdown under `docs/`,
repository-root design documents, ADRs, runbooks. Record where each one sits.

By default, exclude Agent-directed files (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`,
`.cursorrules`) from the inventory of human documentation, but do read them — they often state conventions
that tell you what documentation the project expects to exist. **Classify by reader,
not filename:** follow references that these files incorporate as their own rules and
exclude those documents too. This repository's `docs/agents/*` is one such example.
Include them only when explicitly requested; then identify their Reader as the human
maintainer of the instructions.

Before judging content, record each document's **Reader** (the human's situation and
goal) and **Purpose**: `TUTORIAL` (walk through it), `HOW-TO` (complete a task),
`REFERENCE` (look up a fact), or `EXPLANATION` (understand why). Infer them from, in order:
the document's own statement, its filename and location, the wording of inbound links,
and the code's actual shape. Record the evidence source, not just the conclusion.

### 2. Derive what should exist, from the code

Run all five probes. Before treating a candidate as a gap, establish its intended
Reader and Purpose from named code evidence and project conventions. **If the evidence
does not support a Reader, report that it cannot be determined and stop judgments that
depend on that inference.** Do not invent a Reader to complete a finding. Continue
probes with independent evidence and link-existence checks; apply the same rule to
existing documents whose Reader could not be determined in step 1.

Each probe starts from something concrete in the repository:

| Probe | Derived from | Documentation it implies |
| --- | --- | --- |
| Module boundaries | The top-level module, service, or package split | Where each one's responsibility boundary is written down |
| Non-obvious technology choices | The parts of the dependency list, config, or build scripts that are not the default choice | A record of why that choice was made |
| Manual operational actions | Migration scripts, key rotation, release procedures | A runbook |
| Multiple run modes | dev/prod branching, feature flags, the environment-variable matrix | An explanation of how the modes differ |
| External contracts | HTTP routes, CLI commands, publicly exported symbols | Reference documentation |

**Prefer gaps that will not go stale.** A decision and its reasoning stays true; a
restatement of structure ("these are the modules, this one calls that one") drifts as the
code changes, and reading the code gives it to you anyway. When a gap points at structure
restatement, say so and lower the strength of the recommendation rather than reporting it
at the same weight as a missing decision record.

### 3. Check navigation

Collect links across all tracked Markdown files, then walk outward from the selected
README or entry document. Within that tracked Markdown scope, compare the inventory
with the documents reached from the entry point. Report four things:

- **Orphan documents** — documents with no inbound link from any tracked Markdown file.
- **Documents unreachable from the entry point** — include groups that link to each
  other but have no path from the entry point. Keep this distinct from the Orphan
  definition; combine both observations in one finding when they affect the same document.
- **Entry-point conflict** — more than one document presenting itself as the starting
  point.
- **Broken links** — links pointing at a file or anchor that does not exist.

The selected entry point's own lack of inbound links is not a navigation defect. For
example, with `README → guide` and `a ↔ b`, report `a` and `b` as unreachable; do not
report README itself as a defect merely because nothing links to it.

**State this limitation in the output**: you only count links between tracked Markdown
files, so a document reached from a code comment, an external site, or a chat message
will be misreported as an Orphan. Declaring the limitation is more useful than an orphan
list that pretends to be complete.

### 4. Draft the report, ordered by the cost of being stuck

At this step, load [the report template](references/report-template.md) relative to
this skill directory and use it for the full report. Do not load it during evidence
collection. Keep the required sections even when there are no findings.

Open with the Reader/Purpose judgments and their evidence, covering existing documents
and proposed gaps. Mark unsupported judgments as undetermined rather than filling them
with guesses.

Every finding has four fields:

| Field | Content |
| --- | --- |
| Gap | The missing documentation, or the specific navigation problem |
| Code evidence | The concrete path or artifact that creates the need. **No evidence, no finding** |
| Who gets stuck, and when | A named Reader and a triggering moment — a newcomer's first day, release night, the middle of an incident |
| Owner | `codebase-documenter` to write it, `domain-modeling` to record it as an ADR, or `spec-miner` to reverse-engineer it from code |

**Order findings** by who gets stuck and how soon. Unlike a readability review, the fix
here is expensive — writing a document costs real time — so the user needs to know what
to write first. This asymmetry is deliberate.

**Also report every probe that ran and found no gap.** This is not optional. Findings
alone cannot tell the reader whether a probe was applied and came back clean or was
silently skipped. Keep it distinct from the stop condition below: that one covers a probe
that *could not run* because its code evidence was unreadable; this one covers a probe
that *ran and found nothing*. Both belong in the output.

### 5. Verify evidence and deliver

Before saving or delivering the report, the auditing agent performs one evidence
verification pass. Check repository evidence, not just the draft's wording:

- For each proposed gap, search for the content in other repository documents, including
  alternate names and locations. Confirm that the named code evidence creates the stated
  Reader's need; absence of a conventional filename alone does not establish a gap.
- Reproduce each navigation finding against the collected tracked-Markdown links and
  selected entry point: check inbound links, reachability, competing entry claims, or the
  actual missing file/anchor as applicable. Preserve the entry-point exemption and combine
  Orphan and unreachable observations for the same document.
- Account for all five probes and four navigation checks, distinguishing no findings
  from checks that could not run. Keep conclusions within the actual inspected coverage.

Remove false positives and correct unsupported conclusions. If evidence cannot be checked,
move the affected claim to unverified coverage rather than present it as a confirmed finding.
Verify any corrected finding against its evidence before retaining it. Record the verification
method, evidence checked, corrections made (or none), and remaining unverified items in the
template. Then save and deliver under the output rules above.
This is self-verification, not independent review or a guarantee that nothing was missed.
Do not add a second reviewer by default.

## Boundaries

Do not do these; they belong to skills the user already has:

| Not this skill | Owner |
| --- | --- |
| Checking whether existing documentation still matches what the code does | `neat-freak` |
| Reverse-engineering specs, dependency maps, or API documentation from code | `spec-miner` |
| Writing any documentation, including the gaps this skill reports | `codebase-documenter` |
| Establishing the domain glossary or writing an ADR | `domain-modeling` |
| Reviewing whether one existing document is readable | `optimize-docs-readability` |

## Stop conditions

- **The repository is too large** to build a trustworthy module inventory in one pass —
  report the scope you actually covered and do not present it as complete.
- **No README or entry document exists** — that is the top finding. Navigation checking
  collapses to "there is no entry point"; do not walk links.
- **A probe's code evidence is unreadable** — for example the build configuration is
  missing. Report that the probe did not run and why. Never fill the hole with a generic
  checklist item.
- **A gap has no code evidence** — drop it rather than reporting it as a possibility.
