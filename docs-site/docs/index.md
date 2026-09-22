# Teamora HRMS — Requirement Review Portal

This site is the published, read-and-comment view of Phoneme's BRD/PRD and other
requirement documents for the **Teamora HRMS** project. It exists so that
requirement review and sign-off happens on the web, on the actual document text,
with a permanent audit trail — instead of over email or a separate copy that can
drift from the source.

## How review & sign-off works here

1. **Prepare** — the BRD/PRD is written in Markdown under `docs-site/docs/` in the
   `myphoneme/hrms` repo and opened as a Pull Request against `main`.
2. **Publish for review** — every open PR auto-builds this site and deploys a
   preview copy; GitHub posts the preview link as a PR comment automatically.
3. **Review** — the Team Lead reads the rendered page (this site) for readability
   and adds review feedback as **inline comments directly on the PR diff**, against
   the exact line/requirement in question. This is the permanent, timestamped
   review record.
4. **Fold back** — the author updates the document in the same PR/branch to
   address feedback; every change is a visible commit.
5. **Sign-off** — the Product Owner reviews the final diff and **approves +
   merges the PR**. The merge itself is the sign-off event: GitHub records who
   approved it and when, and merging auto-publishes the updated document to the
   `main` (production) copy of this site.

No separate signature tool is needed for this internal review loop — the PR
approval **is** the audit trail (reviewer identity, timestamp, and exact diff
reviewed are all permanently recorded in GitHub).

## Current documents

| Document | Version | Status | Requirement IDs |
|---|---|---|---|
| [Teamora BRD/PRD — Module 1 & 2](brd-prd/teamora-v2.4.md) | v2.4 | Draft — pending Reviewed/Approved sign-off | HR-M1-FR-001…008, HR-M2-FR-001…008 |

See the [Teamora HRMS - SDLC Tracker](https://github.com/users/myphoneme/projects/5)
project board for the live status of this review against the wider development
pipeline.
