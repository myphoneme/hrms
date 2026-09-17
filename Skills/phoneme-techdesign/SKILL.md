---
name: phoneme-techdesign
description: Generate a Phoneme-branded Technical Design Document (HLD/LLD) in Word, translating an approved BRD/PRD into module architecture, data models, APIs and sequence flows.
---

# Phoneme Technical Design Generator

Stage 2 of Phoneme's Concept-to-Launch SDLC framework. Takes an approved BRD/PRD (`phoneme-brd-prd`) and produces the engineering-facing High-Level Design + Low-Level Design that Stage 3 (`phoneme-uiux-brand-theme`) and eventual development/QA build against. For *which* technologies to use, this skill defers to `phoneme-technical-stack` rather than picking frameworks ad hoc per project.

## When to use
- A BRD/PRD already exists (or the user has clearly described the functional requirements) and the user asks for a "technical design", "HLD/LLD", "architecture doc", or says something like "now let's spec the build."
- Never invent functional scope here — pull requirements straight from the BRD/PRD's numbered sections; if no BRD/PRD exists yet, suggest running `phoneme-brd-prd` first (or confirm requirements directly with the user if they want to skip straight to design).

## Output format
Always a Word document (.docx) via docx.js, mirroring the BRD/PRD's Document Control conventions (Identification `PHN-<PRODUCT_CODE>-<YEAR>-TD`, same Version/Change Log/cover-page treatment, same brand palette per `phoneme-uiux-brand-theme`). Structure:

1. **Cover page & Document Control** — same pattern as the BRD/PRD, title "Technical Design Document (HLD/LLD)", subtitle naming the module(s)/phase covered.
2. **Change Log**.
3. **1. Overview** — one paragraph linking back to the BRD/PRD's vision, and which BRD/PRD sections/modules this design covers.
4. **2. High-Level Design** — 2.1 System architecture (components, hosting/infra — state the stack per `phoneme-technical-stack`'s current charter for this product, or flag if this project uses an approved exception); 2.2 Module breakdown (one subsection per BRD/PRD functional module, numbered to match it 1:1 for traceability); 2.3 Integration points (third-party APIs, job boards, email, auth providers, etc.).
5. **3. Low-Level Design** — per module: 3.x.1 Data model (entities/fields/relationships as tables), 3.x.2 API contracts (endpoint, method, request/response shape as tables), 3.x.3 Key sequence flows (numbered step lists — who calls whom, in what order), 3.x.4 Edge cases & error handling.
6. **4. Security & Compliance** — auth model, data-at-rest/in-transit, PII handling, any regulatory considerations relevant to the product's domain (e.g. DPDP Act 2023 where personal data of Indian users is involved).
7. **5. Non-Functional Design** — how each NFR from the BRD/PRD is actually achieved (caching, scaling strategy, rate limits, etc.) — table cross-referencing back to the BRD/PRD's NFR table.
8. **6. Open Questions / Risks** — bullets, owner, target resolution date.

## Traceability rule
Module numbering in this document must mirror the BRD/PRD's Functional Requirements numbering exactly (e.g. BRD/PRD "3.2 JD Management" → TDD "2.2 Module: JD Management" and "3.2 Low-Level Design: JD Management") so anyone can cross-walk between the two documents section by section.

## Workflow
1. Read the current BRD/PRD (or the user's latest functional description) before drafting anything — do not start from a blank template.
2. Read the product's Technical Stack Charter (`phoneme-technical-stack`) if one exists for this product; if not, run that skill first (or confirm stack choices inline with the user) before writing the architecture section.
3. Draft the docx.js script in a scratch file, module by module.
4. Build the .docx, deliver via SendUserFile, and write it into the connected repo's `Technical/` folder (or equivalent) if one exists.
5. If the BRD/PRD used different terminology than what's since been finalized (a renamed entity, a changed flow), flag the mismatch to the user rather than silently reconciling it — terminology changes should be an explicit, tracked decision.
