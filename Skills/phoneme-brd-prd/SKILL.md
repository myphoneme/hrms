---
name: phoneme-brd-prd
description: Generate a Phoneme-branded BRD/PRD Word document for a new product concept — cover page, document control, objectives, scope, functional/non-functional requirements and sign-off, in Phoneme's standard SDLC format.
---

# Phoneme BRD/PRD Generator

Stage 1 of Phoneme's Concept-to-Launch SDLC framework: turns a product concept, described in plain language, into a formal Business Requirements Document / Product Requirements Document. Feeds Stage 2 (`phoneme-techdesign`, which in turn defers stack decisions to `phoneme-technical-stack`) and Stage 3 (`phoneme-uiux-brand-theme`).

## When to use
- The user describes a new product or module concept (target users, workflow, must-have features) and asks for a BRD, PRD, "requirements doc", or says something like "let's formalize this."
- Only after the concept has actually been discussed with the user — never invent scope. If the brief is thin, ask about target users/company size, must-have vs. nice-to-have features, and constraints before drafting.

## Output format
Always a Word document (.docx) built with the `docx` npm library (docx.js) in Node — never markdown or plain text. Structure, in order:

1. **Cover page** — Phoneme lockup, the product's own brand name + tagline (large, centered — use the brand exactly as finalized with the user; never invent one or reuse another product's). For the confirmed palette/logo treatment, this doc defers to whatever `phoneme-uiux-brand-theme` has already established for the product — don't pick colors independently here.
2. **Document Control table** — Document Description; Identification in the form `PHN-<PRODUCT_CODE>-<YEAR>-01-BRDPRD`; Version (start 1.0, status "Draft — pending Reviewed/Approved sign-off"); Author.
3. **Change Log table** — Version | Date | Author | Description of change. Every re-generation appends a row; never delete history even though the file itself is replaced wholesale.
4. **1. Introduction** — 1.1 Purpose & Vision (2–3 sentences: what it is, who it's for, why it matters); 1.2 Scope (in-scope / out-of-scope bullets); 1.3 Glossary if domain terms are used.
5. **2. Stakeholders & Personas** — table of roles with a one-line description each.
6. **3. Functional Requirements** — one numbered subsection per workflow step/module, mirroring however the user described the flow; each with description, actors, inputs/outputs, business rules, acceptance criteria.
7. **4. Non-Functional Requirements** — table: Category (Performance, Security, Scalability, Availability, Compliance, Localization) | Requirement.
8. **5. Assumptions & Dependencies** — bullets.
9. **6. Success Metrics / KPIs** — table: Metric | Target | How measured.
10. **7. Authorization** — sign-off table: Role | Name | Signature | Date (blank).

## Branding rules
- The product's own brand name/tagline/palette are used exactly as confirmed with the user or as recorded by `phoneme-uiux-brand-theme`. Phoneme Solutions Pvt. Ltd. appears only as the submitting/legal company (Document Control / footer), never merged into the product's own brand lockup.
- The `PHN-` identification prefix is constant across products so all Phoneme SDLC documents stay cross-referenceable by code.

## Versioning discipline
- Every re-generation bumps the version and adds a Change Log row describing exactly what changed.
- If a later stage renames an entity or changes scope, flag this document for a matching rename/update pass rather than letting it silently drift out of sync — note it as a deferred task if the user says so explicitly, but don't forget it.

## Workflow
1. Confirm product name, tagline, and the workflow steps to formalize (from conversation or project memory).
2. Draft the docx.js generation script in a scratch file, building section by section per the structure above.
3. Build the .docx, deliver via SendUserFile, and write it into the connected repo's `Requirement/` folder (or equivalent) if one exists.
4. Tell the user in one line what's in it, and that Stage 2 (Technical Design) is ready once they've reviewed it.
