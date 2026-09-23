---
name: verification-methods
description: Reference sheet of verification methodologies for AI-generated code and agentic systems (type checking, SAST, symbolic execution, formal verification, property-based testing, mutation testing, evals, guardrails, red-teaming, model checking, T/A/I/D/U) plus a catalogue of formal specification languages with a verdict for this repository (TLA+, Quint, Alloy, Dafny, Lean 4, Rocq/Coq, Isabelle/HOL, SPARK, Event-B, P, F*, Agda, Idris, Verus, Kani, Z, VDM, PVS). Use when writing or reviewing a verification plan, a verification.md / trust spec, a testing strategy for agent output, when proposing or evaluating a formal method or specification language, or when the user asks how to verify, validate, or gain confidence in code an agent produced.
---

# Verification methodologies

A vocabulary for answering two different questions. Keep them separate — conflating
them is the usual failure mode of a verification plan.

1. **Artifact-level** — is the code correct?
2. **Process-level** — is the agent behaving reliably?

A methodology that answers one does not answer the other. A green test suite says
nothing about whether the agent will take a destructive action tomorrow; a sandbox
says nothing about whether today's diff is right.

## The catalogue

Full table — definition plus a link to an explanation of the methodology itself
(not a vendor page) — lives in [references/methodologies.md](references/methodologies.md).
Read it before writing anything that names these methods, so the definitions stay
exact and the links stay neutral.

Index:

- **Artifact-level:** type checking · static analysis / SAST · symbolic execution ·
  formal verification / theorem proving · unit & integration testing ·
  property-based testing · mutation testing · contract testing
- **Process-level:** runtime observability / tracing · evals · sandboxed execution ·
  guardrails · human-in-the-loop review · multi-agent verification · CI/CD
  integration · progressive rollout · red-teaming / adversarial testing · model checking
- **Classification:** T / A / I / D / U (Trust Spec) — Test / Analysis / Inspection /
  Demonstration / Unverifiable, assigned per requirement

## Formal specification languages

Before proposing TLA+, Lean 4, Alloy, Dafny, Rocq, Isabelle, SPARK, Event-B, P, F*,
Agda, Idris, Verus, Kani, Z, VDM, PVS or Quint for this repository, read
[references/lenguajes-formales.md](references/lenguajes-formales.md). Fifteen languages,
each with its official link, and a **verdict for this codebase** — three techniques
adopted (written in Python with `hypothesis`, no new dependency), twelve discarded with
the reason grouped, and three named conditions that reopen the question.

The rule that file enforces: **none of the fifteen is installed.** What crosses over is
the technique — small-scope counterexamples (Alloy), the safety/liveness split (TLA+ and
Quint), and declared preconditions with fail-closed behavior (Dafny and SPARK). A formal
model nothing runs in CI asserts a guarantee nobody is checking.

## Producing a verification document

When asked for a `verification.md`, a verification plan, or a trust spec:

1. Open the reference table and use its definitions verbatim in spirit — one plain
   sentence per method, no marketing adjectives.
2. Keep the artifact/process split as the top-level structure.
3. Include the explanation link for every method you name. Link to the methodology,
   never to a tool that implements it.
4. If the document is for a specific codebase, add a column or section saying which
   methods are **in use**, **planned**, or **not applicable here**, with a reason for
   each "not applicable". A catalogue with no verdicts is not a plan.
5. Close with the T/A/I/D/U classification applied to the project's own requirements,
   and name explicitly what falls under **U (unverifiable)**. Naming what you cannot
   verify is the point of the exercise.

## Honest caveats to carry over

- Property-based testing and evals have no single neutral founding reference the way
  formal verification does. The links given are the paper that introduced or
  formalized the method (QuickCheck; HELM) — a defensible choice, not the only one.
- Coverage of a method in the table is not a recommendation to adopt it. Symbolic
  execution and model checking cost more than most projects can justify; say so
  rather than listing them as aspirations.

## Idioma

Los documentos de este proyecto se escriben en español. La hoja de referencia
conserva los términos en inglés donde son el nombre establecido del método.
