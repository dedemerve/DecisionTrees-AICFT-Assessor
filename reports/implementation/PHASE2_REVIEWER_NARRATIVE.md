# Phase 1–2 Implementation Retrospective

## Audience

This document explains **what was built, why it was built, and how it defends methodologically** for Q1 journal reviewers, dissertation examiners, and replication teams. It does not replace frozen framework theory (`framework/*`); it documents the **faithful operationalization** of that theory in software.

---

## 1. Research problem and design stance

### 1.1 Context

We assess **Decision Tree understanding** in a multimodal ProDaBi learning environment and interpret accumulated evidence through **UNESCO AI-CFT (2024)** — but only at the **final interpretive layer**, after domain-level understanding has been established.

The assessment is grounded in **Evidence-Centered Design (ECD)**:

| ECD construct | Our operationalization |
|---------------|------------------------|
| Student model | Observable Behaviours → ILOs → Domain Understanding |
| Task model | Worksheet bundles (evidence collection instruments) |
| Evidence model | Evidence Units → behaviour hypotheses → inferential chain |

### 1.2 Core methodological commitment

> **Observable behaviour precedes interpretation.**

Therefore the implementation enforces a **strict inferential order** with no shortcuts:

```
Raw Source
    → Evidence Unit          [descriptive — M2 FROZEN]
    → Observable Behaviour   [first inference — M3]
    → Instructional Learning Object (ILO)
    → Domain Understanding
    → Interpretive Recommendation (AI-CFT policy)
    → Researcher Decision
```

Evidence may **never** directly generate ILO, Domain, AI-CFT, or competency conclusions.

### 1.3 Two project phases

| Phase | Status | Role |
|-------|--------|------|
| **Phase 1 — Framework design** | FROZEN v1.0 | Scientific theory: ontologies, inference maps, review protocol |
| **Phase 2 — Implementation** | In progress | Faithful runtime; one milestone at a time with freeze gates |

Phase 1 artifacts (`Observable_Behaviours.json`, `Behaviour_to_ILO.json`, `Inference_Rules.md`, etc.) are **constraints**, not implementation targets. The implementation must not redesign them.

---

## 2. Why milestone-based implementation?

The repository is evolving into a **100+ file assessment platform**. Large undifferentiated changes destroy traceability and make Q1-level methodological defense impossible.

We adopted:

- **One milestone at a time**
- **Explicit acceptance criteria**
- **PASS / FAIL verification**
- **Freeze gates** before the next inferential layer
- **STOP** — no automatic continuation

This mirrors software engineering practice but serves **construct validity**: each layer is independently auditable.

---

## 3. Phase 2 Milestone 1 — Worksheet bundles (FROZEN)

### 3.1 What we did

Rebuilt worksheets **WS1–WS11** as pure **evidence collection instruments**. Each deployed worksheet folder contains exactly:

```
extraction_schema.json
rubric.json
behaviour_opportunities.json
validity_notes.json
answer_key.json
```

**WS2, WS8, WS9** are scaffolded as `not_deployed` (absent from ProDaBi unplugged corpus v1).

### 3.2 Why we did it

**Reviewer concern:** *"Worksheets that embed competency mappings conflate task evidence with interpretive claims."*

**Our response:**

- Worksheets collect **candidate evidence** and declare **which Observable Behaviours they may elicit** (`behaviour_opportunities.json` references `OB_*` only).
- They do **not** contain ILO, Domain, or AI-CFT mappings — those belong to higher inference layers defined in frozen framework artifacts.
- `extraction_schema.json` sets `interpretation_prohibited: true` — extraction is structurally incapable of interpretation by contract.

### 3.3 Methodological payoff

| Without M1 | With M1 |
|------------|---------|
| Rubric + legacy LO3 mapping mixed in one file | Clean separation: instrument vs inference |
| OCR/scoring drives competency labels | Scoring is local; portfolio inference is separate |
| Hard to audit "what did the worksheet claim?" | Validity notes + behaviour opportunities are explicit |

**ECD alignment:** Task model is isolated from student model.

---

## 4. Phase 2 Milestone 2 — Evidence Unit runtime (FROZEN v1.1)

### 4.1 What we did

Implemented the **canonical Layer 2 runtime**:

- Schema: `schema/evidence_units_v1.schema.json` (version **1.1**)
- Runtime: `evidence_unit_runtime.py`, `evidence_unit_metadata.py`
- Output: `students/<id>/evidence_units.json`
- Sample: `Sample_Student` — **147** evidence units from existing extractions

An Evidence Unit is defined as:

> **The smallest traceable assessment object representing an interpretable piece of learner evidence while preserving provenance, uncertainty, source quality, and review metadata.**

### 4.2 Why we did NOT start with OCR

**Reviewer concern:** *"Your pipeline seems tied to Claude Vision."*

**Our response:**

- OCR is an **adapter**, not part of the assessment framework.
- The stable interface is `evidence_units.json`.
- Adapters (Claude, GPT Vision, Azure DI) may change; **Evidence Units must not**.
- M2 was completed **before** OCR refactor deliberately — this supports the claim **"OCR-agnostic assessment architecture"** in publication.

```
[OCR adapter — replaceable]
        ↓
FieldExtractionInput
        ↓
evidence_unit_runtime  ← FROZEN
        ↓
evidence_units.json
        ↓
[Behaviour Engine — M3]
```

### 4.3 Why v1.1 is an "assessment object" not a transcription log

Early extraction-only JSON conflates **transcription** with **evidence**. Reviewers correctly ask whether a blank field, a partial threshold, or a high-OCR-confidence illegible response carry the same epistemic weight.

v1.1 adds **descriptive assessment metadata** (not inference):

| Field | Purpose for construct validity |
|-------|------------------------------|
| `evidence_unit_type` | Links evidence form to behaviour patterns (definition, threshold, rule, …) |
| `source_quality` | Separates OCR quality from answer quality |
| `evidence_completeness` | Distinguishes blank / partial / complete without scoring |
| `observability` | direct / indirect / derived — epistemic strength of source |
| `confidence.{ocr, extraction, evidence_quality}` | Triadic confidence; no ad-hoc competency scores |
| `review_level` | Human-in-the-loop gate before inference |
| `alternative_interpretations` | Preserves competing readings without collapsing uncertainty |
| `provenance` | Full traceability to source artifact |

**Critical boundary:** None of these fields assert Observable Behaviour, ILO, Domain, or AI-CFT. They prepare the Behaviour Engine; they do not replace it.

### 4.4 Freeze policy (M2)

> **No further Evidence Unit fields without construct-validity justification.**

Further metadata additions face diminishing returns and risk **ontology creep**. M2 is **FROZEN** at schema v1.1.

Freeze package: `reports/implementation/m2_freeze/`

---

## 5. What we deliberately did NOT implement (yet)

| Omitted | Reason |
|---------|--------|
| Behaviour Engine | First inferential leap — highest validity risk; M3 |
| ILO / Domain / AI-CFT in worksheets or EU | Would violate ECD ordering |
| Portfolio competency scores | Researcher decision only at chain end |
| OCR as core milestone | Technology, not theory |
| Legacy `*/evidence.json` removal | Coexists temporarily; deprecated path to LO3 mapping |

---

## 6. Verification and reproducibility

| Milestone | Tests | Validator |
|-----------|-------|-----------|
| M1 | `test_worksheet_bundles.py` (7) | `validate_worksheet_bundles.py` |
| M2 | `test_evidence_units.py` (7), `test_evidence_unit_metadata.py` (8) | `validate_evidence_units.py`, `schema_validate.py` |

Combined M1+M2: **22 tests PASS**.

Every generated artifact validates against its schema. Framework frozen files were not modified during Phase 2 implementation.

---

## 7. Anticipated reviewer questions (FAQ)

### Q1: Why not score AI-CFT directly from worksheets?

Because that collapses task performance into competency claims without observable-behaviour mediation. UNESCO AI-CFT is an **interpretive framework**, not the primary assessment model (stated in `ARCHITECTURE.md` and frozen policy artifacts).

### Q2: Is this just automated rubric scoring?

No. Rubric scoring (where present) is a **local quality signal**. The framework claim chain requires **behaviour-level evidence** aggregated across modalities before ILO and Domain inference. M1–M2 do not produce competency labels.

### Q3: How do you handle uncertainty?

At M2: `uncertainty`, `alternative_interpretations`, `review_level`, and triadic `confidence` on each Evidence Unit. At M3+: competing behaviour hypotheses with counter-evidence (planned). Contradictions are preserved, not averaged away.

### Q4: Human-in-the-loop?

LLM/OCR role: extract and organize. **Researcher** makes final competency judgement (`Researcher_Review_Protocol.md`). `requires_human_review` and `review_level` propagate upward.

### Q5: Replicability?

Frozen framework JSON + versioned worksheet bundles + deterministic EU IDs + freeze manifests. A replication team can swap OCR adapters without touching M2 runtime.

---

## 8. Next milestone — Behaviour Engine (M3)

### 8.1 Why M3 is the scientific pivot

Everything through M2 is **descriptive**. M3 is the **first interpretation**:

```
Evidence Unit → Observable Behaviour (hypothesis, not lookup)
```

This is the most validity-sensitive transition in the entire system.

### 8.2 Design principles (approved, not yet implemented)

Behaviour Engine will **not** be a deterministic classifier.

Pipeline:

```
Evidence Unit
    → Candidate Behaviour Generator
    → Evidence Matching
    → Behaviour Hypothesis
    → Competing Behaviours
    → Evidence Sufficiency Check
    → Behaviour Recommendation
    → Research Flag
```

Output artifact (planned): `behaviour_evidence.json`

Example structure:

```json
{
  "behaviour_id": "OB_CON_001",
  "status": "supported",
  "candidate_behaviours": ["..."],
  "selected_behaviour": "OB_CON_001",
  "selection_rationale": "...",
  "supporting_evidence": ["EU_..."],
  "counter_evidence": [],
  "alternative_behaviours": [],
  "confidence": "moderate",
  "review_required": false
}
```

**Constraints:**

- Reads **only** `evidence_units.json`
- References **only** `Observable_Behaviours.json`, `Inference_Rules.md`, `Inference_Patterns.md`
- Uses **may_support** logic — never deterministic `definition → OB_*`
- **No** ILO, Domain, or AI-CFT output

### 8.3 M3 acceptance criteria (preview)

- [ ] Multiple candidate behaviours per Evidence Unit possible
- [ ] Selection rationale recorded
- [ ] Supporting and counter evidence co-preserved
- [ ] Confidence does not exceed Evidence Unit epistemic ceiling
- [ ] No upward inference to ILO/Domain/AI-CFT
- [ ] Aligned with frozen inference rules and patterns

---

## 9. Suggested Methods-section narrative (for manuscript)

> We operationalized an Evidence-Centered Assessment Framework for multimodal Decision Tree learning in two phases. Phase 1 froze the theoretical ontology (28 Observable Behaviours, Instructional Learning Objects, Domain Understanding dimensions, and interpretive AI-CFT policies) with explicit inference maps and researcher review protocol. Phase 2 implemented a strictly ordered runtime pipeline in milestone-gated increments. Worksheet instruments (WS1–WS11) were rebuilt as pure evidence-collection bundles without competency mappings. A canonical Evidence Unit schema (v1.1) represents the smallest traceable assessment object, preserving provenance, source quality, completeness, observability, uncertainty, and review metadata while prohibiting behavioural or competency inference at extraction time. OCR technologies are treated as replaceable adapters upstream of this stable interface. The first inferential layer — mapping Evidence Units to Observable Behaviour hypotheses with competing alternatives and sufficiency checks — is implemented separately (Behaviour Engine) to protect construct validity. Final AI-CFT competency claims remain researcher-validated recommendations, not automated scores.

---

## 10. Artifact map (implementation status)

| Layer | Artifact | Status |
|-------|----------|--------|
| L0 Raw source | PDFs, CODAP, recordings | Existing data |
| L1 Instruments | `worksheets/WS*/` | **M1 FROZEN** |
| L2 Evidence Units | `evidence_units.json` | **M2 FROZEN v1.1** |
| L3 Behaviours | `behaviour_evidence.json` | M3 planned |
| L4 ILO | — | M4 planned |
| L5 Domain | — | M5 planned |
| L6 Interpretation | — | M6 planned |
| L7 Portfolio | `portfolio.json` | M7 (rebuild) |
| Dashboard | coverage / contradictions | M8 |

---

## 11. Sign-off

| Milestone | Verdict | Date |
|-----------|---------|------|
| Phase 2 M1 — Worksheet bundles | **PASS / FROZEN** | 2026-06-28 |
| Phase 2 M2 — Evidence Unit runtime v1.1 | **PASS / FROZEN** | 2026-06-28 |
| Phase 2 M3 — Behaviour Engine | **Not started** | — |

**Modification policy:** Framework theory frozen. M2 schema frozen. Proceed to M3 only with explicit researcher approval.
