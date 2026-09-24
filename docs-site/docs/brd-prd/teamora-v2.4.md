![Teamora](../assets/img/teamora-logo.png){ width="220" }

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p><strong>Teamora</strong></p>
<p><em>People. Potential. Progress.</em></p>
<p>Candidate Search to Onboarding Module</p></td>
</tr>
<tr class="even">
<td></td>
</tr>
</tbody>
</table>

**BRD / PRD**

**PROJECT CODE: PHN-HR-2026-01**

September 2026

Submitted by: Phoneme Solutions Pvt. Ltd.

*Security Classification: Confidential — Internal*

**Document Control**

| **Field**               | **Value**                                                                                                                 |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------|
| Document Description    | Business Requirements Document / Product Requirements Document (BRD/PRD) — Teamora: Candidate Search to Onboarding Module |
| Identification          | PHN-HR-2026-01-BRDPRD, Version 2.4 (Draft — pending Reviewed/Approved sign-off, see Authorization below)                  |
| Security Classification | Confidential — Internal                                                                                                   |
| Location                | HR Management project workspace                                                                                           |

**Authorization**

|             | **Name of the Person**       | **Date**    |
|-------------|------------------------------|-------------|
| Prepared by | Anuj (with drafting support) | 10-Sep-2026 |
| Reviewed by | Pending                      | Pending     |
| Approved by | Pending                      | Pending     |

**Change Log**

| **Version** | **Date**    | **Section**            | **A/M/D** | **Description**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | **Reviewed By** |
|-------------|-------------|------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| 0.1–0.2     | 03-Sep-2026 | All                    | A         | Initial BRD/PRD draft; Module 1 & 2 requirements locked                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Pending         |
| 1.0         | 10-Sep-2026 | All                    | M         | Rebuilt on the standard Phoneme corporate template; renamed to BRD/PRD; trimmed to requirements-only scope — pricing, commercial terms, project management, and infrastructure sizing moved out to the Technical Design and consolidated Proposal documents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Pending         |
| 2.0         | 15-Sep-2026 | 1, 3, 4, 5, 6          | A/M       | Resolved critical/high review findings: replaced "locked" language with a formal Draft/Reviewed/Approved Baseline/Superseded status lifecycle (Section 1.2); stated the Release 1 boundary as Modules 1-2 only, with Modules 3-10 marked as roadmap (Section 1.3, 3, 4.3); added the staffing-agency/multi-client tenant model as an in-scope Release 1 requirement and resolved the corresponding open dependency; excluded soft-skill/behavioral signals entirely from the screening-stage scoring matrix per business decision, removing the prior contradiction with the locked no-numeric-soft-skill-scoring rule (Section 4.1); reworked the JD-freeze process flow to reflect a draft-then-freeze scoring matrix rather than a matrix generated only at the freeze moment; added requirement IDs (HR-M1-FR-xxx / HR-M2-FR-xxx) and an Acceptance Scenarios table to both Module 1 and Module 2 (Section 4.1, 4.2); corrected the resume-format claim to PDF/DOCX only, matching the Technical Design (Section 4.2); added measurable, testable acceptance thresholds and a traceability-register requirement (Section 5); updated Naukri RMS/LinkedIn Talent Solutions references to reflect their proposed-adapter-contract status pending vendor confirmation | Pending         |
| 2.1         | 15-Sep-2026 | 1.2, 3, 4.1, 4.2, 5, 6 | A/M       | Resolved second-pass review findings: relabeled module and document status from "Approved Baseline" to "Draft, pending Reviewed/Approved sign-off" throughout, since no actual approver/date was recorded — status now requires an actual Authorization-table entry, not just build-ready content (Section 1.2, 3, 4.1, 4.2, 5); fixed the HR-M1-FR-007 inconsistency with the Technical Design by stating a direct-employer requisition with a client selected is rejected (422), not silently ignored, and added the corresponding scenario; extended Acceptance Scenarios coverage from 8 to all 16 requirement IDs across both modules; added concrete (provisional, pending Product/Engineering sign-off) measurable targets for duplicate-detection precision, resume-parsing accuracy/time, search latency/volume, upload limits, and availability/RPO/RTO (Section 5); added dependencies for sign-off on those provisional targets and for scheduling the formal document review/approval itself (Section 6); aligned the Client Stakeholder dependency wording with the Technical Design's explicit Release 1 deferral rather than leaving it open-ended                                                                                                     | Pending         |
| 2.2         | 15-Sep-2026 | 1.2, 8, 9              | A         | Added new Section 8, Competitive Landscape & USP Analysis: a feature cross-matrix benchmarking Module 1/2 capabilities against six Indian (Darwinbox, Keka, greytHR, Zoho Recruit, PeopleStrong, Turbohire) and five global (Workday Recruiting, BambooHR, Greenhouse, Lever, SmartRecruiters) ATS/HRMS providers, drawn from each provider's public product/help/pricing pages (Sep 2026), plus the resulting six USPs; renumbered the former Section 8 (Road Ahead) to Section 9 and updated its cross-references                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Pending         |
| 2.3         | 17-Sep-2026 | 1.1, 2, 6, 8           | A/M       | Product/brand name confirmed and applied throughout: renamed from the working name "Phoneme HR Suite" to "Teamora" (by Phoneme, tagline "One place for your people.") on the cover page, running footer, Document Control, and every in-body reference (Section 1.1, 2.2, 8); removed the now-resolved brand-name-confirmation item from Section 6 Dependencies. Phoneme Solutions Pvt. Ltd. remains the submitting company; "Teamora" is the product/customer-facing name only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Pending         |
| 2.4         | 18-Sep-2026 | 1.1, Document Control  | M         | Brand finalization: dropped the "by Phoneme" line from the product lockup (cover, running footer, Document Description) — Phoneme remains the submitting company via the Authorization/cover fields only, not as part of the product name; replaced the working tagline "One place for your people." with the finalized tagline "People. Potential. Progress." everywhere it appears. No requirement content changed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Pending         |

**Client Sign Off**

| **Stakeholder Name** | **Role** | **Sign Off Date** | **Communication** |
|----------------------|----------|-------------------|-------------------|
|                      |          |                   |                   |
|                      |          |                   |                   |

**Confidentiality Agreement**

This document is copyrighted, and all rights are reserved. This document may not, in whole or in part, be copied, photocopied, reproduced, translated, or reduced to any electronic medium or machine-readable form without prior consent, in writing. This document is for internal use only and may, in whole or in part, be provided to anyone outside of the Company, including customers, clients, or prospects after taking an approval from an authorized representative.

**Table of Contents**

**1. Introduction**

> 1.1 Overview
>
> 1.2 Purpose
>
> 1.3 Scope
>
> 1.4 References
>
> 1.5 Abbreviations

**2. Overall Description / Background**

> 2.1 Background & Problem Statement
>
> 2.2 Business Objectives
>
> 2.3 Target Market & Personas

**3. Proposed Solution — Overview**

**4. Specific Requirements**

> 4.1 Module 1 — Job Description (JD) Intake & Freezing — Status: Draft v2.1, pending Reviewed/Approved sign-off (supersedes v1.0)
>
> 4.2 Module 2 — Candidate Sourcing & Resume Aggregation — Status: Draft v2.1, pending Reviewed/Approved sign-off (supersedes v1.0)
>
> 4.3 Modules 3–10 — Requirement-Level Scope (Draft, roadmap — not part of Release 1)

**5. Acceptance Criteria**

**6. Dependencies from Stakeholder Side**

**7. Key Risks**

**8. Competitive Landscape & USP Analysis**

> 8.1 Indian HRMS/ATS Providers
>
> 8.2 Global ATS/HRMS Providers
>
> 8.3 Resulting USPs for Teamora

**9. Road Ahead — SDLC Sequence**

**1. Introduction**

**1.1 Overview**

Teamora — "People. Potential. Progress." — is a B2B, multi-tenant SaaS HR module being scoped to automate the full talent lifecycle — from candidate search through onboarding completion — for companies with 50–2,000 employees and recruitment/staffing agencies, in India first. Today, HR and talent teams run this process across a disconnected set of spreadsheets, inboxes, and 2–3 unconnected point tools; Teamora replaces that patchwork with a single system of record covering ten connected process modules under one candidate record, one audit trail, and one set of role-based permissions per tenant company.

**1.2 Purpose**

This is a living Business Requirements Document (BRD) and Product Requirements Document (PRD) — requirements only. It carries no pricing, commercial terms, or delivery-plan detail; those belong to the Technical Design documents and the consolidated Proposal that follow once every module's requirements are frozen (see Section 9). Each module's requirement set moves through a formal status lifecycle — Draft → Reviewed → Approved Baseline → (on later revision) Superseded — rather than a single informal "locked" label; a status of Approved Baseline is recorded only once an actual Reviewed-by/Approved-by name and date appear in this document's own Authorization table, never inferred from requirement detail alone. Two of the ten process modules — JD Intake & Freezing, and Candidate Sourcing & Resume Aggregation — carry Draft v2.1 requirement detail in Section 4, build-ready in content but pending that formal review/approval step; the remaining eight are scoped at requirement level (Draft) and will follow the same path in sequence.

**1.3 Scope**

Release 1 boundary: the build-ready scope of this document, and of the companion Technical Design Document, is Module 1 (JD Intake & Freezing) and Module 2 (Sourcing & Resume Aggregation) only. Modules 3–10 remain requirement-level roadmap content (Section 4.3) and are explicitly out of scope for Release 1 build work — they are not implied to ship alongside Modules 1–2. Release 1 also includes, as an in-scope (not deferred) requirement, the staffing-agency / multi-client tenant model: a tenant may operate as a direct employer or as a staffing agency managing requisitions and candidates on behalf of multiple end-client companies, and this distinction is reflected throughout the Module 1 and Module 2 requirements below.

In scope for requirements across the full ten-module roadmap: JD intake and freezing (AI-generated variants, auto-generated weighted scoring matrix), multi-channel candidate sourcing, automated screening and scoring, candidate pre-interview data capture, multi-round interview management, selection and background verification, offer management with KRA/KPI generation and e-signature, onboarding, and the downstream payroll and appraisal modules the hiring record feeds into. Explicitly out of scope for this document: architecture/API design (Technical Design stage), pricing and commercial terms (Proposal stage), and project timeline/resourcing (Project Management stage).

**1.4 References**

- Digital Personal Data Protection Act, 2023 (India) — governs candidate and employee personal data handling throughout this product.

- Naukri RMS, LinkedIn Talent Solutions, and equivalent official job-board employer integrations — the sourcing-channel standard adopted in Section 4.2, pending vendor/product-tier confirmation (Section 6).

- India's RBI Account Aggregator framework and licensed income-verification providers (e.g. Perfios, HyperVerge) — the compliant alternative adopted for candidate income verification in the future Background Verification module.

- Industry benchmarking of current ATS/HRMS platforms (Darwinbox, Keka, Zoho Recruit, Zimyo, NeoRecruit, greytHR) — informing the differentiators noted throughout Section 4.

**1.5 Abbreviations**

| **Term**  | **Meaning**                                                    |
|-----------|----------------------------------------------------------------|
| ATS       | Applicant Tracking System                                      |
| BGV       | Background Verification                                        |
| JD        | Job Description                                                |
| KRA / KPI | Key Result Area / Key Performance Indicator                    |
| DPDP Act  | Digital Personal Data Protection Act, 2023 (India)             |
| SLA       | Service Level Agreement                                        |
| MVP       | Minimum Viable Product                                         |
| RMS       | Recruiter Management System (job-board employer integration)   |
| BRD / PRD | Business Requirements Document / Product Requirements Document |

**2. Overall Description / Background**

**2.1 Background & Problem Statement**

HR and talent teams at small-to-mid-size companies currently run recruitment and onboarding across a disconnected set of tools: spreadsheets or free ATS tiers for pipeline tracking, WhatsApp/email for interview coordination, a separate e-sign tool for offer letters, and manual checklists for onboarding. This produces four recurring problems: no single source of truth on candidate status; slow, manually-chased handoffs between offer acceptance and day-one readiness; compliance exposure from candidate PII scattered across personal inboxes with no consistent retention trail; and no structured hiring analytics for leadership to act on.

**2.2 Business Objectives**

| **Objective**                   | **How Teamora addresses it**                                                                                                           |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Reduce time-to-hire             | Single pipeline with automated stage transitions, scheduling, and reminders removes manual chase-up delay                              |
| Reduce time-to-productive       | Automated onboarding checklists and cross-team task assignment starting the moment an offer is accepted                                |
| Reduce compliance risk          | Centralised, access-controlled candidate records with consent capture, retention policy, and audit trail, aligned to the DPDP Act 2023 |
| Create a defensible data moat   | Every pipeline event captured as structured data from day one, supporting future AI-matching features                                  |
| Land-and-expand within accounts | Positioned as the first module of a broader Phoneme HR suite (payroll, performance) sharing one tenant and employee record             |

**2.3 Target Market & Personas**

Primary segment: companies with 50–2,000 employees in India, plus recruitment/staffing agencies managing multiple client pipelines. Primary buyer and daily user: the HR Manager / Talent Acquisition Lead. Day-to-day users span Recruiters, Hiring Managers, Interview Panelists, HR Ops/Onboarding Coordinators, and — on the candidate-facing side — the applicant and new hire themselves, interacting through a token-based portal with no account creation required.

**3. Proposed Solution — Overview**

The solution is structured as ten sequential, connected process modules, each owning a distinct stage of the talent lifecycle and handing structured data — not free text — to the next. Full architecture and technology decisions for each module are captured in that module's Technical Design document, not here. Modules 1 and 2 are the Release 1 build scope (Section 1.3); Modules 3–10 are roadmap content, not part of Release 1.

1.  Job Description (JD) Intake & Freezing — Draft v2.1, pending approval, Release 1 (Section 4.1)

2.  Candidate Sourcing & Resume Aggregation — Draft v2.1, pending approval, Release 1 (Section 4.2)

3.  Screening & Shortlisting — roadmap; scored against the Module 1 matrix, threshold-gated auto-advancement

4.  Candidate Pre-Interview Data Capture — roadmap; token-based portal, expected CTC, project write-ups

5.  Interview Management — roadmap; multi-round, structured interviewer scorecards, panel decision rollup

6.  Selection & Background Verification — roadmap; consent-gated identity/employment/income verification via licensed vendors

7.  Offer Management, KRA/KPI & E-Sign — roadmap; auto-generated offer letter and compensation breakup, e-signature, hire-to-payroll handoff

8.  Onboarding — roadmap; cross-team asset/IT/documentation checklist, day-one readiness dashboard

9.  Payroll & Compensation — roadmap; salary slips, full-and-final settlement, loans, employee expenses

10. Appraisal — roadmap; continuous KRA/KPI tracking feeding the annual review cycle

**4. Specific Requirements**

This section carries full requirement detail for the two modules built out to build-ready depth to date, followed by the current requirement-level (Draft) scope for the remaining eight modules.

**4.1 Module 1 — Job Description (JD) Intake & Freezing — Status: Draft v2.1, pending Reviewed/Approved sign-off (supersedes v1.0)**

A hiring manager sends a rough, free-text brief (by email or portal); the system converts it into structured JD data, generates multiple polished JD variants alongside an editable draft weighted scoring matrix, routes them for manager review and sign-off, and — at freeze — approves the JD version and its then-current matrix together, becoming the baseline every downstream module scores against. Release 1 includes the staffing-agency / multi-client tenant model: for an agency tenant, every requisition is raised against one of its end-client companies (Section 1.3); for a direct-employer tenant, no client selection applies.

**Process Flow**

1.  Manager submits a rough brief — by email to a dedicated intake address, or directly in the portal.

2.  System runs NLP extraction on the brief into the structured JD Intake Schema; low-confidence fields are flagged for manager confirmation rather than silently guessed.

3.  System generates 2–3 JD variants — a formal/corporate version, a candidate-friendly version, and a condensed job-board version.

4.  All variants are emailed to the manager (with a portal link) and appear in the portal's Pending JD Approval queue.

5.  Manager reviews by replying on the email in plain text (NLP-parsed back into structured diffs) or editing directly in the portal — both are first-class review paths.

6.  A configurable SLA (e.g. 3 business days) triggers a reminder, then an HR escalation, if the manager does not respond.

7.  Manager reviews and, once satisfied, adjusts the auto-generated draft scoring matrix (weights per category) directly in the portal — the draft matrix is generated alongside the JD variants in step 3 and remains editable through every review round, not only at the final moment.

8.  Manager freezes: the currently Pending-Approval JD version and its bound draft matrix are approved together in one action. The newly Approved version becomes JobRequisition's current version; if an earlier version was previously Approved, it is marked Superseded (its content retained, never deleted or overwritten) rather than replaced in place.

9.  A JD may be revised after an initial freeze (e.g. a role's requirements change): the same review/adjustment/freeze loop (steps 5–8) runs again and produces a new Approved version, superseding the one before it — this is a normal, supported path, not an exception.

**Scoring Matrix — Default Weight Bands**

Business decision (Release 1): soft-skill / behavioral signals are excluded entirely from the scoring matrix at JD-freeze and screening stage — no numeric weight, band, or proxy score is generated for them at this stage. They are captured as free text on the JD brief where relevant, and are assessed only qualitatively, by a human interviewer, at the structured interview stage (Module 5). The weight bands below cover only the categories that are numerically scored at screening; a matrix's weights must sum to exactly 100% before it can be approved.

| **Category**                 | **Default weight band** |
|------------------------------|-------------------------|
| Core tool/technical skills   | 35–55%                  |
| Experience & seniority       | 25–40%                  |
| Domain/analytical competency | 15–30%                  |
| Education fit                | 0–10%                   |

**Feature List**

| **Req ID**   | **Feature**                                 | **Description**                                                                                                                                                                                                                                    | **Priority** |
|--------------|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| HR-M1-FR-001 | Free-text brief ingestion (email + portal)  | NLP extraction into the structured JD Intake Schema, with low-confidence fields flagged for manager confirmation                                                                                                                                   | Must-have    |
| HR-M1-FR-002 | Multi-variant JD generation                 | Auto-generate 2–3 JD versions (formal, candidate-friendly, condensed) from structured data                                                                                                                                                         | Must-have    |
| HR-M1-FR-003 | Email + portal review loop                  | Manager approves/edits via direct email reply (NLP-parsed) or in-portal editor — both converge on the same draft                                                                                                                                   | Must-have    |
| HR-M1-FR-004 | JD versioning & audit trail                 | Every edit stored as a version with author and timestamp; an Approved version is immutable and only ever superseded, never overwritten                                                                                                             | Must-have    |
| HR-M1-FR-005 | Approval SLA & escalation                   | Configurable reminder/escalation timer if a manager doesn't respond to a pending JD                                                                                                                                                                | Must-have    |
| HR-M1-FR-006 | Draft-then-freeze weighted scoring matrix   | Matrix generated as an editable draft alongside the JD variants (not only at freeze), weights adjustable by the manager through every review round, approved atomically with the JD version at freeze; weights must sum to exactly 100% to approve | Must-have    |
| HR-M1-FR-007 | Staffing-agency / multi-client requisitions | An agency-tenant requisition is raised against a specific end-client company; a direct-employer tenant has no client selection                                                                                                                     | Must-have    |
| HR-M1-FR-008 | JD templates                                | Save an Approved JD + matrix as a reusable template for recurring roles                                                                                                                                                                            | Should-have  |

**Approved Decisions**

- An Approved JD version and its matrix are immutable; any further change creates a new version through the same review/approval loop and, on its own approval, supersedes the prior Approved version rather than overwriting it.

- Manager can approve/edit by direct email reply (parsed by NLP) or in-portal — both are first-class; a low-confidence email parse always routes to a portal confirmation step rather than auto-applying.

- The scoring matrix is generated as an editable draft alongside the JD variants and remains editable by the manager through every review round; freezing approves the JD version and its then-current draft matrix together in one action — no matrix goes live without a human setting eyes on the weights, and the weights must sum to exactly 100%.

- Soft skills are captured as text at JD/resume stage only and are excluded entirely from the numeric screening-stage scoring matrix; they are assessed solely through qualitative human judgment at the structured interview stage (Module 5).

- Release 1 includes the staffing-agency / multi-client tenant model: an agency tenant's requisition must specify an end-client company; a direct-employer tenant's does not.

**Acceptance Scenarios**

| **Req ID**   | **Scenario**                                                                                  | **Expected outcome**                                                                                                                                                                                                                                                    |
|--------------|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| HR-M1-FR-006 | Manager submits matrix weights that sum to 100%                                               | Freeze succeeds; new JD version and matrix set to Approved; prior Approved version (if any) set to Superseded                                                                                                                                                           |
| HR-M1-FR-006 | Manager submits matrix weights that do not sum to 100%                                        | Freeze request rejected with the offending total returned; no state change to the requisition                                                                                                                                                                           |
| HR-M1-FR-006 | Two managers attempt to freeze the same requisition simultaneously                            | Exactly one freeze succeeds atomically; the second is rejected against the now-current state, not silently overwritten                                                                                                                                                  |
| HR-M1-FR-004 | Manager edits a JD after it has already been Approved (frozen)                                | Direct edit to the Approved version is rejected; the edit instead opens a new Draft/Revising version through the standard review loop                                                                                                                                   |
| HR-M1-FR-004 | Manager repeats an identical freeze request already applied                                   | Second request is a no-op against the same Approved version — no duplicate version or duplicate matrix is created                                                                                                                                                       |
| HR-M1-FR-007 | An agency-tenant manager submits a brief without selecting a client                           | Rejected at intake with an explicit validation error (422); a client selection is required before the brief is accepted                                                                                                                                                 |
| HR-M1-FR-007 | A direct-employer-tenant manager submits a brief with a client selected                       | Rejected at intake with an explicit validation error (422) — a direct-employer tenant has no client to select, and the field must be left unset rather than populated; consistent with agency-without-client-selected being rejected the same way, not silently ignored |
| HR-M1-FR-001 | Manager submits a brief with a field the NLP extraction cannot confidently identify           | Field is flagged low-confidence and manager_confirmed is forced false; the field cannot feed an Approved JD until the manager explicitly confirms or corrects it                                                                                                        |
| HR-M1-FR-002 | Structured brief data is complete enough to generate variants                                 | System produces all three JD variants (formal, candidate-friendly, condensed); none is silently skipped                                                                                                                                                                 |
| HR-M1-FR-003 | Manager replies to the review email with a low-confidence or ambiguous instruction            | Reply is not auto-applied; routed to a portal confirmation step for the manager to confirm the intended change before it is applied                                                                                                                                     |
| HR-M1-FR-005 | Manager does not respond within the configured SLA window                                     | A reminder fires at the configured threshold, followed by an HR escalation if still unresolved; both fire on a scheduled check, not only when the manager next opens a request                                                                                          |
| HR-M1-FR-008 | Manager saves an Approved JD + matrix as a template and later reuses it for a new requisition | New requisition pre-populates from the template; the template itself is unaffected by later edits to the requisition created from it                                                                                                                                    |

**4.2 Module 2 — Candidate Sourcing & Resume Aggregation — Status: Draft v2.1, pending Reviewed/Approved sign-off (supersedes v1.0)**

Once a JD is frozen (Approved), it is published to sourcing channels and resumes begin flowing into the system — via job-board integration, direct email, or manual upload — into one unified, deduplicated candidate pool scoped to the owning tenant and, for an agency tenant, its specific end-client.

**Approved decision:** resumes are ingested only through official, contracted integrations — job-board recruiter APIs / RMS partnerships (Naukri RMS, LinkedIn Talent Solutions, and equivalent) — plus direct email intake and manual upload. Unauthorized scraping of job-board pages is explicitly out of scope, since it violates most job boards' terms of service and creates an ongoing legal and account-suspension risk. Where a target board has no official API, the fallback is manual upload — never scraping. Naukri RMS and LinkedIn Talent Solutions are, as of this baseline, proposed adapter contracts pending vendor/product-tier confirmation (Section 6) — not yet confirmed vendor capabilities.

**Sourcing Channels**

| **Channel**                     | **Ingestion method (Approved)**                                                                   |
|---------------------------------|---------------------------------------------------------------------------------------------------|
| Naukri                          | Naukri RMS (Recruiter Management System) API integration — pending vendor confirmation, Section 6 |
| LinkedIn                        | LinkedIn Talent Solutions API integration — exact product pending confirmation, Section 6         |
| Niche job boards (e.g. iimjobs) | Official employer API where available; manual upload otherwise                                    |
| Direct email intake             | Automated inbox parsing — attachment extraction + resume parsing                                  |
| Manual upload                   | Recruiter-driven single/bulk upload — universal fallback                                          |
| Employee referral               | Referral link/form tied to the referring employee, attributed at intake                           |

**Feature List**

| **Req ID**   | **Feature**                                | **Description**                                                                                                                                                                                                                                             | **Priority** |
|--------------|--------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| HR-M2-FR-001 | Multi-channel job posting                  | Publish an Approved requisition to the careers page and contracted job-board integrations from one action                                                                                                                                                   | Must-have    |
| HR-M2-FR-002 | Job-board API integration (not scraping)   | Naukri RMS / LinkedIn Talent Solutions / equivalent official integrations only                                                                                                                                                                              | Must-have    |
| HR-M2-FR-003 | Email intake parsing                       | Dedicated per-(tenant, client) inbox auto-parses incoming resumes/attachments                                                                                                                                                                               | Must-have    |
| HR-M2-FR-004 | Resume parsing                             | Extract structured fields (contact, experience, skills, education) from PDF and DOCX resumes, Release 1's supported formats                                                                                                                                 | Must-have    |
| HR-M2-FR-005 | Unified resume inbox                       | One consolidated view across all channels, scoped to (tenant, client), instead of separate per-source screens                                                                                                                                               | Must-have    |
| HR-M2-FR-006 | Duplicate detection with conflict handling | Flag likely-duplicate candidates on intake and link rather than duplicate; conflicting evidence routes to a recruiter for manual review rather than an automatic decision, and every resolution (linked, rejected, or later reversed) is retained for audit | Must-have    |
| HR-M2-FR-007 | Candidate database search                  | Full-text and filtered search across the caller's (tenant, client)-scoped candidate pool                                                                                                                                                                    | Must-have    |
| HR-M2-FR-008 | Referral capture & attribution             | Referral link/form tied to the referring employee, captured at intake                                                                                                                                                                                       | Should-have  |

**Approved Decisions**

- No unauthorized scraping of any job-board site, under any circumstance — sourcing channels ship only via official, contracted API/RMS integrations, direct email intake, or manual upload.

- A job board with no official API integration path falls back to manual upload/email intake rather than being scraped.

- Every incoming resume, regardless of channel, lands in one unified resume inbox scoped to its owning (tenant, client) and tagged by source.

- Duplicate detection runs at intake, before a candidate reaches the screening queue, scoped within (tenant, client) — the same person applying through two different agency clients is not treated as a duplicate, by design.

- Release 1 supports PDF and DOCX resumes only; other formats (.doc, .rtf, .pages, scanned images) are rejected at intake with an explicit unsupported-format error and routed to a manual structured-entry fallback rather than silently dropped or misparsed — this corrects an earlier, broader "any resume format" claim.

**Acceptance Scenarios**

| **Req ID**   | **Scenario**                                                                               | **Expected outcome**                                                                                                                                                  |
|--------------|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| HR-M2-FR-002 | A vendor confirms the exact contracted integration product                                 | Section 6 open dependency closes; Naukri RMS / LinkedIn Talent Solutions status in this document is updated from proposed to confirmed                                |
| HR-M2-FR-004 | Candidate uploads a scanned (image-only) or password-protected PDF                         | File is detected as unparseable rather than silently producing an empty or garbled parse; routed to the manual structured-entry fallback                              |
| HR-M2-FR-006 | Two resumes match on email but disagree on candidate name                                  | Routed to a recruiter review queue as a conflict, not auto-linked and not auto-rejected                                                                               |
| HR-M2-FR-006 | Recruiter finds an auto-link was incorrect                                                 | Recruiter can reverse the link; the original decision is retained for audit and the two candidate records are split back apart                                        |
| HR-M2-FR-005 | An agency recruiter searches the unified inbox                                             | Results are limited to the recruiter's authorized (tenant, client) scope; client is resolved from the recruiter's session, never accepted as a caller-supplied filter |
| HR-M2-FR-001 | A requisition is published for an agency's end-client                                      | The requisition's channel adapters use that end-client's own configured vendor credentials, not the agency's default or another client's                              |
| HR-M2-FR-003 | An email arrives at the intake address with no attachment                                  | Body is retained for audit but not treated as a resume; no Candidate/Application record is created from a bodiless or attachment-less email                           |
| HR-M2-FR-007 | A recruiter filters candidate search by a requisition the caller is not authorized to view | Filter is rejected or returns no results rather than exposing candidates for a requisition outside the caller's authorized scope                                      |
| HR-M2-FR-008 | A referred candidate applies via the referral link                                         | Application is tagged with the referring employee's attribution at intake, retained through the full candidate record, not only shown at the point of submission      |

**4.3 Modules 3–10 — Requirement-Level Scope (Draft, roadmap — not part of Release 1)**

The remaining modules are scoped to product-requirement level below and will each be elaborated to Approved Baseline detail, following the same process demonstrated for Modules 1–2, as they are brought into a future release.

**Module 3 — Screening & Shortlisting**

- Candidates are scored against the Module 1 weighted matrix as they enter the pipeline; knockout criteria reject automatically, others are ranked with visible score reasoning.

- Configurable per-requisition threshold moves a candidate to Screened status and triggers an automatic notification email.

**Module 4 — Candidate Pre-Interview Data Capture**

- Token/magic-link portal login (no account creation); role-configurable form (expected CTC, reason for change, project write-ups).

- Submission triggers interview scheduling and candidate notification of interview details.

**Module 5 — Interview Management**

- Multi-round (typically 2–3) structured interviews with scorecards tied to JD competencies; panel decision rollup before advancing to the next round.

- Candidate portal status updates in step with internal round outcomes.

**Module 6 — Selection & Background Verification**

- Triggered at SELECTED status. Consent capture is a hard gate before any check begins.

- Identity, address, education, and employment checks via a licensed BGV vendor integration.

- Income verification via India's Account Aggregator framework or a consented provider (e.g. Perfios, HyperVerge) — candidate-authorized data pull, not inbox scanning.

**Module 7 — Offer Management, KRA/KPI & E-Sign**

- Offer letter and compensation breakup auto-populated from candidate, role, and approved comp data; role-based KRA/KPI template attached automatically.

- E-signature integration with tracked status; accepted offer auto-closes the requisition and copies the comp structure into the Payroll module.

**Module 8 — Onboarding**

- Cross-team checklist (IT provisioning, ID card, facilities, HR paperwork) auto-assigned on offer signature, with a day-one readiness dashboard.

- Onboarding completion converts the candidate record into an employee record — the seam into Modules 9 and 10.

**Module 9 — Payroll & Compensation**

- Monthly salary slip generation, full-and-final settlement, loan/advance tracking, and employee expense reimbursement, with India statutory compliance (PF, ESI, professional tax, TDS).

**Module 10 — Appraisal**

- Continuous tracking against the KRA/KPIs set at offer stage, feeding an annual appraisal cycle rather than a once-a-year reconstruction exercise.

**5. Acceptance Criteria**

Measurable, testable targets — a qualitative statement such as "search should be fast" is not acceptance-testable on its own and is avoided below in favor of a stated threshold.

| **Criterion**                  | **Threshold**                                                                                                                                                                                                                                                                                                                                                                                                    |
|--------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Data isolation (tenant)        | No cross-tenant data access under automated isolation testing, across the database, message-queue, search-index, object-storage, and webhook layers (TDD Section 5.3)                                                                                                                                                                                                                                            |
| Data isolation (agency client) | For an agency tenant, no cross-client data access within the same tenant under the same automated isolation testing — a Client Stakeholder or agency recruiter scoped to one client never sees another client's requisitions or candidates                                                                                                                                                                       |
| Security                       | Role-based access control, encryption at rest and in transit, full audit log of candidate-PII access                                                                                                                                                                                                                                                                                                             |
| Compliance                     | DPDP Act 2023 alignment verified at each module baseline — consent gates, retention policy, data-principal rights workflow                                                                                                                                                                                                                                                                                       |
| Scoring-matrix integrity       | A matrix cannot reach Approved status with weights that do not sum to exactly 100%; 100% of freeze attempts with an invalid total are rejected, not silently normalized (HR-M1-FR-006)                                                                                                                                                                                                                           |
| Duplicate-detection precision  | Target: false-positive auto-link rate ≤ 1% on exact-key (email/phone) matches, measured against a labeled sample of resolved DuplicateMatch decisions each quarter — provisional target pending Product/Engineering sign-off (Section 6); any conflicting-evidence case routes to manual review rather than auto-linking regardless (HR-M2-FR-006)                                                               |
| Resume parsing                 | 100% of PDF/DOCX uploads either parse successfully or are routed to the manual fallback — none silently dropped or left in an unknown state. Target: ≥ 90% of successfully-routed PDF/DOCX uploads parse with all required fields (name, contact, one work-history entry) at ≥ 0.75 confidence, within 30 seconds of upload — provisional target pending Product/Engineering sign-off (Section 6) (HR-M2-FR-004) |
| Candidate search performance   | Target: p95 query latency ≤ 2 seconds at a reference load of 100,000 candidates and 50,000 applications per tenant, 20 concurrent searching users per tenant — provisional target pending Product/Engineering sign-off (Section 6) (HR-M2-FR-007)                                                                                                                                                                |
| Resume upload limits           | Target: single-file upload accepted up to 10 MB; bulk upload up to 200 files or 200 MB per batch, whichever is reached first — provisional target pending Product/Engineering sign-off (Section 6)                                                                                                                                                                                                               |
| Availability & recovery        | Target: 99.5% monthly availability for Module 1 and Module 2 read/write paths; Recovery Point Objective (RPO) ≤ 15 minutes and Recovery Time Objective (RTO) ≤ 4 hours for the primary datastore — provisional targets pending Product/Engineering sign-off (Section 6); full operational/DR detail is a Section 9 roadmap deliverable, not restated here                                                        |
| Module acceptance              | A module's requirements reach Approved Baseline only once (a) its Feature List, Approved Decisions, and Acceptance Scenarios (Section 4.1/4.2) are unambiguous enough for the Technical Design stage to begin without open questions, AND (b) an actual Reviewed-by/Approved-by name and date are recorded in this document's Authorization table — content readiness alone does not constitute approval         |
| Traceability                   | Every requirement ID in Section 4.1/4.2 has a corresponding row in the Requirement Traceability Register (a companion living document), linking it to its Technical Design reference(s) and test coverage before the module is considered build-ready                                                                                                                                                            |

**6. Dependencies from Stakeholder Side**

The following decisions are needed from Phoneme leadership/stakeholders before remaining modules can reach Approved Baseline. The staffing-agency multi-client priority question from the prior baseline is resolved — it is in scope for Release 1 (Section 1.3) — and is removed from this list.

1.  Target launch timeline and team size for the Release 1 build.

2.  Pricing/packaging model (per-seat, per-employee, or per-tenant flat fee) — to be resolved before the consolidated Proposal document (Section 9) is generated.

3.  First 2–3 design-partner customers to validate the workflow before general availability.

4.  Naukri RMS contracted-plan confirmation (push vs. poll availability) and LinkedIn Talent Solutions product-tier confirmation (Recruiter System Connect, Apply Connect, or another) — both integrations are proposed adapter contracts pending this vendor-feasibility gate (Section 4.2).

5.  Client Stakeholder read-only portal role for agency end-clients is explicitly deferred out of Release 1 (Section 4.2) — what such a role would see is a fast-follow decision, not a Release 1 blocker.

6.  Preferred e-signature and background-verification vendors — informs the Module 6 and Module 7 Technical Design.

7.  Confirmation of the Module 6 income-verification approach (Account Aggregator framework vs. a specific licensed vendor).

8.  Sign-off on the provisional measurable acceptance targets in Section 5 (duplicate-detection precision, resume-parsing accuracy/time, search latency/volume, upload limits, availability/RPO/RTO) with the actual Product and Engineering owners — these are placeholder-but-explicit values pending that review, not yet committed targets.

9.  Formal Reviewed-by/Approved-by sign-off on this BRD/PRD and the companion Technical Design Document — both currently carry Draft v2.1 status with build-ready content but no recorded approver; scheduling this review is itself a stakeholder-side dependency before Module 1/2 development can proceed on an Approved Baseline.

**7. Key Risks**

| **Risk**                                                            | **Impact**                                                  | **Mitigation**                                                                                                               |
|---------------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| Scope creep across ten modules                                      | Delays first shippable release                              | Module-by-module requirement locking and a firm MVP scope boundary                                                           |
| Third-party integration availability/cost (BGV, e-sign, job boards) | Blocks specific module features if a vendor contract stalls | Common adapter layer (defined at Technical Design stage) so a vendor swap is cheap; shortlist two vendors per category early |
| DPDP Act compliance gaps found late                                 | Legal/reputational risk with enterprise customers           | Compliance checklist reviewed at every module lock, not deferred to a pre-launch audit                                       |
| Multi-tenant data leakage                                           | Catastrophic trust failure for a B2B SaaS product           | Tenant-scoping enforced at the data-access layer plus a standing automated cross-tenant isolation test suite                 |

**8. Competitive Landscape & USP Analysis**

This section benchmarks Teamora's Module 1 (JD Intake & Freezing) and Module 2 (Sourcing & Resume Aggregation) feature set against eleven Indian and global ATS/HRMS providers, and draws out the resulting Unique Selling Propositions (USPs). Methodology: findings are drawn from each provider's own public product pages, help-center documentation, and pricing pages as of September 2026 — not from live demos or trials. "Yes"/"Partial"/"No" reflect what is publicly confirmed; "Unconfirmed" means the capability could not be verified either way from public sources and should not be read as "absent" — a materially different competitive position could emerge from a live demo. This matrix should be re-validated before use in external sales collateral.

**8.1 Indian HRMS/ATS Providers**

| **Capability**                                                                           | **Teamora**                                               | **Darwinbox**                            | **Keka**                                                  | **greytHR**                                    | **Zoho Recruit**                                       | **PeopleStrong**                                                   | **Turbohire**                       |
|------------------------------------------------------------------------------------------|-----------------------------------------------------------|------------------------------------------|-----------------------------------------------------------|------------------------------------------------|--------------------------------------------------------|--------------------------------------------------------------------|-------------------------------------|
| AI-generated JD variants (multiple drafts, not just a template)                          | Yes — 2–3 AI variants per brief (HR-M1-FR-002)            | Unconfirmed                              | No — JD is an uploaded attachment or external link only   | Unconfirmed                                    | Partial — skillset fields only, not full JD text       | Partial — skill recommendations only                               | Unconfirmed                         |
| Structured JD schema (queryable fields, not a file attachment)                           | Yes                                                       | Unconfirmed                              | No                                                        | Unconfirmed                                    | Partial                                                | Partial                                                            | Unconfirmed                         |
| Formal role-based JD/requisition approval workflow                                       | Yes — manager review with SLA/escalation                  | Unconfirmed                              | Yes — configurable universal or rule-based approval chain | Unconfirmed                                    | Partial — general workflow/blueprint automation        | Yes — configurable approval hierarchies                            | Partial — Approver role in workflow |
| Hard, immutable JD-freeze state (version-locked)                                         | Yes — DB-trigger-enforced immutability on freeze (unique) | Not found                                | Not found                                                 | Not found                                      | Not found                                              | Not found                                                          | Not found                           |
| Manager approval via native email-reply NLP parsing                                      | Yes — no portal login required (unique)                   | Not found                                | Not found                                                 | Not found                                      | Not found                                              | Not found                                                          | Not found                           |
| Unified, deduplicated multi-channel resume inbox                                         | Yes (HR-M2-FR-003)                                        | Unconfirmed                              | Unconfirmed                                               | Partial — undetailed "centralized inbox" claim | Yes — Resume Inbox                                     | Partial                                                            | Unconfirmed                         |
| Native resume parsing (no third-party add-on)                                            | Yes                                                       | No — marketplace add-on only             | Unconfirmed                                               | Unconfirmed                                    | Yes — Resume Extractor/Formatted Resume                | Yes                                                                | Unconfirmed                         |
| Cross-channel duplicate-candidate detection with audit trail                             | Yes — append-only reversal model (HR-M2-FR-006, unique)   | Not confirmed by any provider researched | —                                                         | —                                              | —                                                      | —                                                                  | —                                   |
| Multi-tenant + multi-client (agency) isolation architecture                              | Yes — 5-layer enforcement (TDD Section 5.3)               | No                                       | No                                                        | No                                             | Yes — Client Portal + Vendor Portal (Staffing Edition) | Partial — multi-stakeholder interfaces, no explicit agency edition | No                                  |
| Sourcing restricted to official APIs/RMS + email + manual upload (no job-board scraping) | Yes — explicit locked decision (legal/ToS risk avoidance) | Not stated publicly                      | Not stated publicly                                       | Not stated publicly                            | Not stated publicly                                    | Not stated publicly                                                | Not stated publicly                 |

**8.2 Global ATS/HRMS Providers**

| **Capability**                                                  | **Teamora**                                               | **Workday Recruiting**                       | **BambooHR**                            | **Greenhouse**                                               | **Lever**                                                                                | **SmartRecruiters**                                      |
|-----------------------------------------------------------------|-----------------------------------------------------------|----------------------------------------------|-----------------------------------------|--------------------------------------------------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------|
| AI-generated JD variants (multiple drafts, not just a template) | Yes — 2–3 AI variants per brief                           | Yes — generative AI to jumpstart JD creation | No — template library only              | Yes — "Job Post Description Suggestions"                     | Unconfirmed                                                                              | Unconfirmed                                              |
| Structured JD schema (queryable fields, not a file attachment)  | Yes                                                       | Partial                                      | Partial — template library              | Partial                                                      | Unconfirmed                                                                              | Unconfirmed                                              |
| Formal role-based JD/requisition approval workflow              | Yes — manager review with SLA/escalation                  | Unconfirmed                                  | Unconfirmed                             | Partial — Slack-integration recipe, native depth unconfirmed | Yes — dedicated job-posting, requisition, and proxy approval workflows (best documented) | Unconfirmed                                              |
| Hard, immutable JD-freeze state (version-locked)                | Yes — DB-trigger-enforced immutability on freeze (unique) | Not found                                    | Not found                               | Not found                                                    | Not found                                                                                | Not found                                                |
| Manager approval via native email-reply NLP parsing             | Yes — no portal login required (unique)                   | Not found                                    | Not found                               | Not found                                                    | Not found                                                                                | Not found                                                |
| Unified, deduplicated multi-channel resume inbox                | Yes                                                       | Unconfirmed                                  | Unconfirmed                             | Partial — LinkedIn RSC+ gives a unified applicant view       | Unconfirmed                                                                              | Partial — matches across internal and external databases |
| Native resume parsing (no third-party add-on)                   | Yes                                                       | Yes — AI reads resumes for latent skills     | Unconfirmed                             | Yes — Talent Matching                                        | Unconfirmed                                                                              | Yes — SmartAssistant matching                            |
| Cross-channel duplicate-candidate detection with audit trail    | Yes — append-only reversal model (unique)                 | Not confirmed by any provider researched     | —                                       | —                                                            | —                                                                                        | —                                                        |
| Multi-tenant + multi-client (agency) isolation architecture     | Yes — 5-layer enforcement (TDD Section 5.3)               | No                                           | No                                      | No — multi-brand job boards only, single company             | No                                                                                       | No                                                       |
| Public, transparent per-seat pricing                            | To be finalized (Section 6 dependency)                    | No — custom enterprise quotes                | Yes — \$10/\$17/\$25 per employee/month | No — custom quotes                                           | No — custom quotes                                                                       | No — custom quotes                                       |

**8.3 Resulting USPs for Teamora**

Six differentiators recur across both benchmarks — each a Module 1/2 decision already locked in this document (Section 4.1/4.2), not an aspirational claim:

1.  Hard, immutable JD-freeze state: the JDVersion state machine locks content at the database-trigger level the instant a version is Approved. No provider researched, Indian or global, publicly documents an equivalent formal version-lock — most treat the JD as a mutable field or a plain file attachment (Keka confirmed attachment-only).

2.  Manager approval by native email-reply NLP parsing, with no portal login required — not found in any of the eleven providers' public documentation, all of which assume in-portal approval.

3.  An explicit, ToS-safe sourcing architecture — official job-board APIs/RMS integrations plus email intake and manual upload only, with no scraping — combined with a single deduplicated resume inbox. No competitor publicly states an equivalent no-scraping guarantee; the closest partial matches (Zoho Recruit's Resume Inbox, greytHR's undetailed "centralized inbox") do not document the dedup layer.

4.  Cross-channel duplicate-candidate detection with an append-only reversal audit trail (HR-M2-FR-006). Zero of the eleven providers researched had this publicly confirmed — the single cleanest gap found across the entire competitive set.

5.  True multi-tenant plus multi-client (agency) isolation enforced independently at five layers — database, message queue, search index, object storage, and webhooks (TDD Section 5.3). Only Zoho Recruit's Staffing Edition (Client Portal + Vendor Portal) offers a comparable agency-facing model among the eleven, and its isolation depth is not publicly documented to this level.

6.  A weighted scoring matrix auto-generated from the frozen JD, with a hard validation rule that weights must sum to exactly 100% before freeze (HR-M1-FR-006) — not found in any provider researched.

**9. Road Ahead — SDLC Sequence**

This BRD/PRD is the first of a set of documents produced per module as the SDLC proceeds. The sequence for each module is: (1) BRD/PRD — this document, requirements only; (2) Technical Design — data schema, API contracts, and integration specs, produced once a module's requirements reach Approved Baseline; (3) UX/screen specification, where a module has a significant user-facing surface; (4) Test/acceptance plan, developed alongside the Technical Design rather than only after it. Once every module has cleared all applicable stages, a single consolidated Proposal document — carrying pricing, commercial terms, and delivery plan — is generated from this material for presentation to B2B customers. A Requirement Traceability Register (Section 5) is maintained as a living companion document from this baseline onward, linking each requirement ID through design, build, and test evidence.

- Modules 1 & 2: Draft v2.1, build-ready in content and pending formal Reviewed/Approved sign-off (this document) — Technical Design v2.1, same status, in progress alongside (see the companion Technical Design Document); Release 1 build scope.

- Module 3 onward: requirements to reach Approved Baseline in sequence, following the same process demonstrated for Modules 1 & 2, as they are brought into a future release.

- Final Proposal document: generated only once all module-level documents across all applicable stages are frozen, incorporating the pricing and commercial-terms decisions from Section 6.
