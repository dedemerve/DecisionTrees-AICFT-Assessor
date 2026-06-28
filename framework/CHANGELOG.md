# Architecture Change Log

## 2026-06-28

### Decision

Established the core inferential chain:

`Raw Evidence -> Evidence Units -> Observable Behaviours -> Learning Objects -> Domain Understanding -> AI-CFT Competency Claims -> Researcher Validation`

### Rationale

This replaces weaker direct worksheet-to-competency logic with an ECD-aligned interpretive chain.

### Decision

Separated `Learning Objects` from `Domain Understanding`.

### Rationale

Learning Objects are instructional targets, while Domain Understanding is a broader disciplinary synthesis. Collapsing them would weaken construct clarity.

### Decision

Positioned AI-CFT as the final interpretive layer rather than the primary assessment model.

### Rationale

UNESCO AI-CFT is broader than local Decision Tree task performance and should therefore rest on accumulated domain evidence.

### Decision

Added a formal `Assessment_Argument.md`.

### Rationale

A publishable framework requires explicit claims, warrants, threats, and mitigation logic, not only file structure.

### Decision

Added governance artifacts for researcher review, versioning, dependency tracking, and change logging.

### Rationale

Reproducibility, auditability, and framework maintenance are part of scientific defensibility, not optional implementation details.

### Decision

Added `Inference_Rules.md` as a distinct framework artifact.

### Rationale

The architecture and assessment argument define layers and warrants, but they do not by themselves specify the admissible inferential moves between layers. A dedicated inference-rules artifact is needed to prevent undocumented jumps, preserve ECD integrity, and make future mappings scientifically reviewable.

### Decision

Extended `Inference_Rules.md` with rule types, sufficiency grammar, negative inference, null evidence, and competing hypothesis logic.

### Rationale

Different layers use different kinds of inference, and Q1-level defensibility requires more than generic “support” language. These additions make the inferential system more explicit, more auditable, and less vulnerable to over-interpretation.

### Decision

Added `Inference_Patterns.md` as a separate framework artifact.

### Rationale

The framework needs standardized inferential templates before ontology and mapping artifacts are instantiated. This prevents later artifacts from encoding support, contradiction, null evidence, or escalation inconsistently.

### Decision

Added `Construct_Definition.md` as a core framework artifact.

### Rationale

The framework required an explicit definition of the target construct so that later ontologies, mappings, and verification tests can distinguish Decision Tree Understanding from non-target constructs such as writing ability, digital fluency, or general academic performance.

### Decision

Strengthened the distinction between `Inference_Rules.md` and `Inference_Patterns.md`.

### Rationale

`Inference_Rules.md` now functions as the normative law book of the inference system, while `Inference_Patterns.md` serves as the operational template library. This separation makes their scientific responsibilities more defensible.

### Decision

Strengthened `Framework_Verification_Plan.md` with gate logic, internal/external verification, construct leakage testing, and freeze criteria.

### Rationale

At this maturity level the framework must be verified, not merely expanded. These additions make verification a condition for freeze rather than an optional recommendation.

### Decision

Rewrote `Inference_Rules.md`, `Inference_Patterns.md`, and `Construct_Definition.md` per adversarial review.

### Rationale

- **Rules** reduced to normative core (R1–R20, prohibited shortcuts, confidence laws); operational transition detail removed.
- **Patterns** expanded to full standard template with nine core patterns, four transition bundles, and DT examples; each pattern cites governing rules.
- **Construct Definition** strengthened with ontological hierarchy, dimension→layer mapping, leakage catalogue, and executable CLT-A–D test matrix wired to Verification Plan Test 11.
- No new framework artifacts added; highest ROI is construct clarity, not layer expansion.

### Decision

Implemented **Instructional Learning Object (ILO) ontology v1.0** in `Learning_Objects.json` (Milestone 2).

### Rationale

ILOs represent curriculum instructional targets (feature, threshold, MCR, etc.) and bridge frozen Observable Behaviours to Domain Understanding. Terminology explicitly disambiguates ILO from SCORM Learning Objects and UNESCO AI-CFT competency codes (LO3.x).

### Decision

Froze **Instructional Learning Object (ILO) ontology v1.0** after Milestone 2 freeze package.

### Rationale

Freeze package includes behaviour→ILO coverage matrix, ILO dependency graph, instructional sequence, standardized concept families, and freeze report. Milestone 3 mapping artifact renamed to `Behaviour_to_ILO.json`. No `generalisation` family ILO in v1.0 — accepted limitation.

### Decision

Revised **Behaviour_to_ILO.json** to v1.1 as the first inference layer: qualitative confidence with explicit basis, mapping roles (primary/secondary/contextual/diagnostic), rejected alternatives with reasons, structured counter-evidence, and automated analytics reports.

### Rationale

Numeric mapping confidence removed (deferred to Confidence_Model.json). Validator now emits coverage, construct, cross-construct matrices and mapping statistics for construct-validity auditing.

### Decision

Froze **Observable Behaviour Ontology v1.0** after Milestone 1 freeze package verification.

### Rationale

Downstream layers (ILO mapping, domain ontology, worksheet bundles) require a stable behaviour vocabulary. Freeze package includes coverage matrix, semantic duplicate review, dependency graph, construct coverage report, and freeze report. Human expert review remains pending; semantic ontology changes require major version bump.
