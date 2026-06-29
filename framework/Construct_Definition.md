# Construct Definition

## Purpose

This document defines the **ontological** target construct assessed by the framework:

**Decision Tree Understanding**

It answers the reviewer question:

> How do you know the framework measures Decision Tree understanding rather than general academic ability, writing ability, or digital fluency?

The entire Assessment Argument rests on one assumption:

> Multi-source evidence collected through this pipeline **represents** Decision Tree Understanding — not a proxy construct.

If this construct is not theoretically and operationally defined, lower layers may be technically consistent yet scientifically indefensible.

---

## Ontological definition

**Decision Tree Understanding** is the learner's demonstrated capacity to:

1. **know** decision-tree concepts and their distinctions (terminology and distinction evidence → LO3.1),
2. **execute** decision-tree procedures correctly (procedure application evidence → LO3.2),
3. **choose and justify** among alternatives using performance-relevant criteria (strategic evaluation evidence → LO3.2), and
4. **reflect** on limits, trade-offs, and learning specific to decision-tree use (reflective creation evidence → LO3.3),

in ways that are **evidentially grounded**, **contextually appropriate**, and **distinguishable** from unrelated abilities.

This construct is **domain-specific** and **multi-dimensional**. No single dimension is sufficient for the whole construct.

---

## Construct hierarchy

> **Note:** These construct dimensions are **project-internal analysis categories** for *what we measure* (terminology, procedure, strategy, reflection). They are **not** taken from Kilpatrick (2001). Final proficiency assignment uses UNESCO AI-CFT **Acquire** (Basic AI techniques and applications, LO3.1), **Deepen** (Application skills, LO3.2), and **Create** (Creating with AI, LO3.3) levels only.

```
Decision Tree Understanding
├── Terminology and distinction evidence
│   └── terminology, distinctions, coherent explanation (maps to LO3.1 — Basic AI techniques and applications)
├── Procedure application evidence
│   └── threshold application, classification, tree construction (maps to LO3.2 — Application skills)
├── Strategic evaluation evidence
│   └── comparison, selection, model evaluation, trade-offs (maps to LO3.2 — Application skills)
└── Reflective creation evidence
    └── limitations, uncertainty, metacognitive commentary on DT use (maps to LO3.3 — Creating with AI)
```

### Dimension → framework layer mapping

| Construct dimension | Primary evidence layers | UNESCO AI-CFT proficiency / LO families | Domain Understanding tags |
|---------------------|-------------------------|-------------------------------------------|---------------------------|
| Terminology and distinction | worksheets, reflections | Acquire — Basic AI techniques and applications (LO3.1.x) | Terminology and distinction evidence |
| Procedure application | worksheets, CODAP logs, DT sections | Deepen — Application skills (LO3.1.x, LO3.2.1) | Procedure application evidence |
| Strategic evaluation | worksheets, multi-task performance | Deepen — Application skills (LO3.2.2, LO3.2.3) | Threshold Reasoning, Tree Construction |
| Reflective creation | reflections, open responses | Create — Creating with AI (LO3.3.x) | Reflective creation evidence |

Learning Objects are **instructional targets** within dimensions. They are not interchangeable with the construct itself.

---

## What this construct is not

| Non-target construct | Why excluded |
|----------------------|--------------|
| General intelligence | not domain-specific |
| General academic ability | task-agnostic performance |
| Writing quality / fluency | surface form ≠ DT reasoning |
| Digital fluency alone | interaction ≠ understanding |
| Confidence / verbosity | affect and length ≠ competence |
| Worksheet compliance | completion ≠ understanding |

---

## Construct boundaries (inclusion / exclusion)

**Includes:**

- decision-tree terminology and distinctions
- threshold and classification reasoning
- tree construction and interpretation
- evaluation and error reasoning
- reflective understanding **about** decision-tree use

**Does not automatically include:**

- generic data literacy
- generic mathematical ability
- persuasive writing quality
- general digital navigation skill
- generic AI enthusiasm or attitude

---

## Construct leakage

Construct leakage occurs when variance in a **non-target** construct (writing, fluency, verbosity) is mistaken for variance in **Decision Tree Understanding**.

Guard rules: `Inference_Rules.md` R13–R15. Operational response: `Inference_Patterns.md` PAT-BLOCK-001.

### Leakage risk catalogue

| ID | Leakage source | Symptom | Required framework response |
|----|----------------|---------|----------------------------|
| L1 | Writing ability | eloquent text, weak DT reasoning | cap Domain Understanding; do not infer Strategic |
| L2 | Brevity bias | short text, strong procedural evidence | do not under-assign Procedural/Strategic |
| L3 | Digital fluency | high click volume, weak justification | cap Strategic; logs alone insufficient |
| L4 | Terminology recall | vocabulary without transfer | Conceptual only unless corroborated |
| L5 | Reflection quality | excellent reflection, wrong thresholds | Reflective weak/moderate; block Threshold Reasoning |

---

## Construct leakage test matrix

Canonical adversarial cases for `Framework_Verification_Plan.md` Test 11. Each case specifies **inputs**, **expected outcome**, and **failure signal**.

### CLT-A — Strong writing, weak DT reasoning

| Field | Value |
|-------|-------|
| `case_id` | CLT-A |
| `leakage_source` | writing ability |
| Inputs | polished prose; incorrect or absent threshold logic; no CODAP corroboration |
| Expected outcome | **Low** Domain Understanding (Conceptual at most weak); no Strategic escalation |
| Failure signal | high Domain or AI-CFT driven by writing quality alone |
| Pattern | PAT-BLOCK-001 if escalation attempted |

### CLT-B — Weak writing, strong CODAP / procedural evidence

| Field | Value |
|-------|-------|
| `case_id` | CLT-B |
| `leakage_source` | brevity bias (inverse) |
| Inputs | minimal text; correct threshold moves; repeatable classification |
| Expected outcome | **Procedural** (and possibly Strategic) supported; writing not penalized |
| Failure signal | low scores solely due to brief responses |
| Pattern | PAT-POS-001 on procedural dimension |

### CLT-C — Good terminology, poor transfer

| Field | Value |
|-------|-------|
| `case_id` | CLT-C |
| `leakage_source` | terminology recall |
| Inputs | correct definitions; failure on novel threshold or transfer item |
| Expected outcome | **Conceptual only**; Transfer and Strategic blocked |
| Failure signal | broad Domain Understanding from vocabulary alone |
| Pattern | PAT-BLOCK-001 on Strategic / Generalisation |

### CLT-D — Excellent reflection, incorrect thresholds

| Field | Value |
|-------|-------|
| `case_id` | CLT-D |
| `leakage_source` | reflection mistaken for execution |
| Inputs | thoughtful metacognitive writing; wrong threshold application in worksheet/log |
| Expected outcome | Reflective weak–moderate; **Threshold Reasoning not inferred** |
| Failure signal | Strategic or Threshold domain from reflection without execution |
| Pattern | PAT-CONTRA-001 + PAT-BLOCK-001 |

### Test execution protocol

1. Construct synthetic or annotated student profiles matching each case.
2. Run full pipeline through portfolio aggregation.
3. Record `observed_framework_response` per dimension and LO peak.
4. Compare to expected outcome; flag `acceptable_or_problematic`.
5. If any failure signal fires, revise mapping weights, patterns, or aggregation — not the construct definition without explicit project decision.

---

## Operational implications

1. **Observable Behaviours** must code actions/statements against construct dimensions, not worksheet labels alone.
2. **Learning Object** claims must cite dimension-relevant evidence; LO peaks must not aggregate baseline/diagnostic items as mastery.
3. **Domain Understanding** synthesis must respect dimension independence (Conceptual ≠ Procedural ≠ Strategic).
4. **AI-CFT** proposals remain provisional until researcher validation; Create-level requires multi-dimensional Strategic evidence.
5. Every mapping change should answer: *which construct dimension does this measure, and which leakage case could falsely inflate it?*

---

## Relationship to other artifacts

| Artifact | Relationship |
|----------|--------------|
| `ARCHITECTURE.md` | inferential layers this construct flows through |
| `Assessment_Argument.md` | warrants assuming this construct is what evidence represents |
| `Inference_Rules.md` | laws preventing leakage (R13–R15) |
| `Inference_Patterns.md` | templates applying those laws (PAT-BLOCK-001, etc.) |
| `Framework_Verification_Plan.md` | Test 11 executes CLT-A through CLT-D |
| Ontology / mapping JSON | must align behaviours, LOs, and domain tags to dimensions above |

---

## Reviewer gate

Before accepting framework outputs as publishable, confirm:

1. Construct dimensions are independently assessable in the evidence model.
2. At least one CLT case has been executed with acceptable results.
3. No prohibited shortcut in `Inference_Rules.md` maps writing or fluency to DT understanding.
4. Portfolio aggregation excludes construct-irrelevant variance from peak LO claims.

---

## Status

**Foundational — highest scientific priority for framework defensibility.**

Stable unless the project explicitly changes its target construct. Changes here trigger re-review of all ontology, mapping, and verification artifacts.
