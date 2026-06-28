# Versioning Policy

## Purpose

This policy governs version control for framework artifacts so that interpretations remain reproducible across time.

## Scope

The policy applies to:

- ontologies
- mappings
- rubrics
- schemas
- aggregation rules
- confidence rules
- validation rules
- researcher review guidance

## Versioning Principle

Any change that can affect interpretation must be versioned and documented.

## Version Categories

### Major version

Use a major version change when:

- the inferential chain changes
- an ontology is restructured
- a mapping logic changes conceptually
- a policy changes the meaning of prior interpretations

### Minor version

Use a minor version change when:

- new behaviours, Learning Objects, or misconceptions are added without changing prior semantics
- additional source types are supported
- clarifying fields are added

### Patch version

Use a patch version change when:

- typos are fixed
- non-semantic clarifications are made
- examples are refined without changing interpretation rules

## Required Documentation Per Change

Every versioned change must record:

- artifact name
- previous version
- new version
- date
- author
- reason for change
- affected downstream artifacts
- whether prior results remain comparable

## Compatibility Rule

If a change alters interpretation semantics, prior outputs must not be treated as directly comparable without an explicit migration note.

## Review Rule

All major and minor changes should trigger review of dependent artifacts before the framework proceeds to production use.

