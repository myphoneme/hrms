---
name: phoneme-technical-stack
description: Define and record a Phoneme product's Technical Stack Charter — the confirmed languages, frameworks, database, hosting/infra, AI/ML components, and DevOps conventions — so architecture and code stay consistent across a project instead of being re-decided per document.
---

# Phoneme Technical Stack Charter

A standalone stage that sits alongside Stage 2 (`phoneme-techdesign`) rather than inside it: Phoneme works across genuinely different technical domains (SaaS web products, data-center/cloud infrastructure projects, Pine Script/broker trading systems, CrewAI-based agentic workflows, OOXML/document tooling), so there is no single fixed "Phoneme stack" to assume. This skill's job is to nail down, confirm, and durably record the right stack *for a specific product*, once, so every later document (Technical Design, code, deployment plan) references the same charter instead of drifting.

## When to use
- Starting a new product's Technical Design and no Technical Stack Charter exists yet for it.
- The user is deciding or changing core technology choices ("what should we build this in", "let's use X for the backend", "should this be on AWS or Azure").
- Before writing any actual application code for a new Phoneme product, to confirm the stack rather than assuming one.

## What the charter records
A short section (in the Technical Design doc, or its own one-pager if the user prefers) with these fields — leave a field explicitly "TBD — confirm with user" rather than guessing:

1. **Product type** — SaaS web app / internal tool / infra project / trading system / content & document tooling / agentic workflow — this determines which of the sub-patterns below even apply.
2. **Frontend** — framework, styling approach, hosting (e.g. static/CDN vs. server-rendered).
3. **Backend** — language/framework, API style (REST/GraphQL), auth approach.
4. **Data** — primary datastore, caching layer, file/blob storage.
5. **AI/ML components** — which parts use an LLM or model (e.g. JD generation, resume screening), which provider/API, and any human-in-the-loop override requirement.
6. **Hosting & infra** — cloud provider or on-prem/data-center (Phoneme has in-house data-center/private-cloud experience — HPE/Alletra-class infra — for projects that call for it), environments (dev/staging/prod), domain/subdomain pattern (e.g. `app.<product>.io`).
7. **Third-party integrations** — job boards, email/SMS providers, payment, OAuth providers — anything Stage 2's "Integration points" section will need.
8. **DevOps & CI/CD** — repo hosting (GitHub per existing Phoneme convention), branching model, CI pipeline, deployment method.
9. **Security & compliance baseline** — data residency, PII handling, DPDP Act 2023 or other applicable regulation, credential storage approach.
10. **Coding conventions** — repo folder structure, naming conventions, lint/format tooling — kept short; point to an existing style guide if one already exists rather than re-writing one per product.

## Rules
- Never assert a specific framework or provider as "the Phoneme standard" unless the user has actually said so for this product or a prior one on record — ask and confirm instead of defaulting silently. It is fine to *suggest* a sensible default and ask for a yes/no.
- Once confirmed, treat the charter as authoritative for that product: `phoneme-techdesign` should read it before writing the System Architecture section, and application code should follow it rather than introducing an unapproved technology mid-project. A deliberate stack change is a tracked decision (add a line to the charter's own changelog), not a silent swap.
- Different Phoneme products can have entirely different charters — do not carry one product's stack into another's without the user saying to.

## Workflow
1. Check whether a Technical Stack Charter already exists for this product (in the Technical Design doc's architecture section, or a dedicated note) before asking questions the user has already answered.
2. If none exists, ask through the fields above — batch related questions, don't interrogate one field at a time.
3. Record the confirmed charter in the product's Technical Design document (Section 2.1) or as its own short reference file in the repo's `Technical/` folder.
4. Point `phoneme-techdesign` and any development work back to this charter rather than re-deciding stack per module.
