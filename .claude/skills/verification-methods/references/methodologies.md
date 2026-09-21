# Verification Methodologies — Reference Sheet

A quick-reference list of verification methodologies for AI-generated code and
agentic systems, each with a plain definition and a link to an explanation of the
methodology itself (not a product page).

## Artifact-level verification (is the code correct?)

| Methodology | Definition | Explanation link |
| --- | --- | --- |
| Type checking | Automated checking that values are used consistently with what operations expect of them | [Type system — Wikipedia](https://en.wikipedia.org/wiki/Type_system) |
| Static analysis / SAST | Scanning source code without running it, to match against known-bad patterns | [Static program analysis — Wikipedia](https://en.wikipedia.org/wiki/Static_program_analysis) |
| Symbolic execution | Running code with placeholder inputs to derive exact failure conditions via an SMT solver | [Symbolic execution — Wikipedia](https://en.wikipedia.org/wiki/Symbolic_execution) |
| Formal verification / theorem proving | Mathematically proving code satisfies a specification for all possible inputs | [Formal verification — Wikipedia](https://en.wikipedia.org/wiki/Formal_verification) |
| Unit / integration testing | Checking behavior against specific, chosen example inputs and expected outputs | [Unit testing — Wikipedia](https://en.wikipedia.org/wiki/Unit_testing) |
| Property-based testing | Specifying a general property, then generating many inputs to search for a violation | [QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs — Claessen & Hughes, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) |
| Mutation testing | Deliberately introducing small bugs to check whether the test suite catches them | [Mutation testing — Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing) |
| Contract testing | Verifying the interface between two services stays consistent, independent of internals | [Contract Test — Martin Fowler](https://martinfowler.com/bliki/ContractTest.html) |

## Process-level verification (is the agent behaving reliably?)

| Methodology | Definition | Explanation link |
| --- | --- | --- |
| Runtime observability / tracing | Instrumenting an agent so its trajectory is visible and queryable after the fact | [Observability primer — OpenTelemetry](https://opentelemetry.io/docs/concepts/observability-primer/) |
| Evals | Structured tests of agent behavior against a dataset and scoring method | [Holistic Evaluation of Language Models (HELM) — Liang et al., 2022](https://arxiv.org/abs/2211.09110) |
| Sandboxed execution | Running agent code in an isolated environment so bad actions fail safely | [Sandbox (computer security) — Wikipedia](https://en.wikipedia.org/wiki/Sandbox_%28computer_security%29) |
| Guardrails | Policies/filters constraining what actions an agent is allowed to produce | [AI Risk Management Framework — NIST](https://www.nist.gov/itl/ai-risk-management-framework) |
| Human-in-the-loop review | A person approves/rejects/edits high-consequence agent actions | [Human-in-the-loop — Wikipedia](https://en.wikipedia.org/wiki/Human-in-the-loop) |
| Multi-agent verification | Critic, debate, self-consistency, reflection, or ensemble patterns checking model output | [AI Safety via Debate — Irving, Christiano, Amodei, 2018](https://arxiv.org/abs/1805.00899) |
| CI/CD integration | Routing agent-generated changes through the same pipeline as human-authored code | [Continuous integration — Wikipedia](https://en.wikipedia.org/wiki/Continuous_integration) |
| Progressive rollout | Shipping a change to a small percentage of traffic behind a flag before full release | [Feature toggle — Wikipedia](https://en.wikipedia.org/wiki/Feature_toggle) |
| Red-teaming / adversarial testing | Deliberately probing for failures under an adversarial threat model | [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| Model checking | Exhaustively exploring an agent's reachable states/transitions to verify invariants | [Model checking — Wikipedia](https://en.wikipedia.org/wiki/Model_checking) |

## Classification framework

| Method | Definition | Explanation link |
| --- | --- | --- |
| T / A / I / D / U (Trust Spec) | Test / Analysis / Inspection / Demonstration / Unverifiable classification for each requirement | [Verification and validation — Wikipedia](https://en.wikipedia.org/wiki/Verification_and_validation) |

> **Note:** Property-based testing and evals don't have a single neutral "founding"
> reference the way formal verification does. The links above point to the paper that
> introduced or formalized the methodology in each case (QuickCheck for the former,
> HELM for the latter), not the only possible choice.
