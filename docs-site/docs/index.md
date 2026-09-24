# Teamora HRMS — Requirement Review Portal

This site is the published, read-and-comment view of Phoneme's BRD/PRD and other
requirement documents for the **Teamora HRMS** project. It exists so that
requirement review and sign-off happens on the web, on the actual document text,
with a permanent audit trail — instead of over email or a separate copy that can
drift from the source.

This is the as-built implementation of **Phoneme SDLC SOP, Section 8.7** —
which now also carries the review governance (roles, criteria, SLA, partial/
at-risk approval, change control, escalation) consolidated from
`PHN-SDLC-2026-02-DOCGOV`.

## Roles for this review

| Role | Who | Responsibility |
|---|---|---|
| Author / Preparer | Anuj (with drafting support) | Opens the review PR once content is complete enough for review |
| Technical Reviewer | **Arjun Kushwaha** | Validates technical feasibility/completeness; leaves inline PR comments |
| Approver | Product Owner (Anuj / designate) | Final Approved sign-off via PR approve + merge |

## How review & sign-off works here

1. **Prepare** — the BRD/PRD is written in Markdown under `docs-site/docs/` in the
   `myphoneme/hrms` repo and opened as a Pull Request against `main`.
2. **Publish for review** — every open PR auto-builds this site and deploys a
   preview copy; GitHub posts the preview link as a PR comment automatically.
3. **Review** — the assigned Reviewer(s) above read the rendered page for
   readability and add review feedback as **inline comments directly on the PR
   diff**, against the exact requirement in question, against the criteria in
   SOP Section 8.7.3 (content unambiguous + no unresolved open questions).
   Target turnaround: **3–5 business days** from the PR opening (SOP Section
   8.7.4). This is the permanent, timestamped review record.
4. **Fold back** — the author updates the document in the same PR/branch to
   address feedback; every change is a visible commit.
5. **Sign-off** — the Approver reviews the final diff and **approves + merges
   the PR**. The merge itself is the sign-off event: GitHub records who
   approved it and when, and merging auto-publishes the updated document to the
   `main` (production) copy of this site.

A module can be approved and merged ahead of the rest of the document
(SOP 8.7.5), and work may start at-risk ahead of a formal merge only via a
logged `at-risk-authorized` comment on the PR naming the accepted risk and
target merge date (SOP 8.7.6) — never silently.

No separate signature tool is needed for this internal review loop — the PR
approval **is** the audit trail (reviewer identity, timestamp, and exact diff
reviewed are all permanently recorded in GitHub).

## Technical Design review roles

For a Technical Design (SOP 8.7.2), the **Technical Reviewer is mandatory** and also checks that the
design traces 1:1 to the BRD/PRD requirement IDs; the **Approver** is the Release Owner or senior
technical authority. The review and sign-off steps are the same as above: inline PR comments,
fold-back commits, then approve + merge.

## Current documents

| Document | Version | Status | Requirement IDs |
|---|---|---|---|
| [Teamora BRD/PRD — Module 1 & 2](brd-prd/teamora-v2.4.md) | v2.4 (approval recorded in v2.5 .docx) | **Approved Baseline** — signed off 24-Sep-2026 (PR #1) | HR-M1-FR-001…008, HR-M2-FR-001…008 |
| [Teamora Technical Design — Module 1 & 2](tdd/teamora-tdd-m1m2-v4.2.md) | v4.2 | Draft — in review | Implements HR-M1-FR-001…008, HR-M2-FR-001…008 |

See the [Teamora HRMS - SDLC Tracker](https://github.com/users/myphoneme/projects/5)
project board for the live status of this review against the wider development
pipeline.
