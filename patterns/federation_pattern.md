# The Federation Pattern (System-of-Systems for LLM Workflows)

*Composing multiple governed LLM subsystems without creating a single uncontrolled super-agent.*

## The problem

Once you have several specialist LLM systems — a strategist, a coder, a critic, a researcher — the tempting move is to wire them into one big autonomous loop that calls whichever it likes and merges the results. That maximizes capability and *minimizes* governability: authority becomes diffuse, failures cross boundaries invisibly, and no human can see why the system concluded what it did.

The federation pattern composes subsystems for capability **while preserving the boundaries that make each one governable.**

## The shape

```
                 ┌─────────────┐
                 │   ROUTER    │  identifies relevant domains; activates only those
                 └──────┬──────┘
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
     ┌─────────┐  ┌─────────┐   ┌─────────┐
     │ SPECIALIST│ │SPECIALIST│  │SPECIALIST│   each: bounded, single-responsibility
     │    A     │ │    B     │  │    C     │   emits ARTIFACTS only (no actions)
     └────┬─────┘ └────┬─────┘  └────┬─────┘
          └────────────┼─────────────┘
                       ▼
                 ┌─────────────┐
                 │ SYNTHESIS   │  compares/reconciles; NO silent merge; declares
                 │  KERNEL     │  precedence for conflicts; preserves dissent
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │ HUMAN SEAM  │  artifacts side-by-side; human decides
                 └─────────────┘
```

## Rules that keep it governable

1. **Artifact-only exchange.** Subsystems exchange **read-only artifacts**, never actions and never mutable shared state. A specialist cannot reach into another and change it.
2. **No shared memory.** Each subsystem runs in its own context; there is no global "everything the federation knows" that drifts and accumulates hidden authority. (This is also the antidote to the false "they're coordinating behind the scenes" impression — there is no back-channel; the only integration point is the synthesis kernel, in the open.)
3. **Router activates, it does not decide.** The router selects *which* specialists are relevant; it does not rank their conclusions or pick a winner.
4. **Synthesis reconciles without collapsing.** When specialists disagree, the synthesis kernel **preserves the disagreement** and resolves it only by *declared precedence* (e.g., "safety dominates performance"), stated explicitly. It never silently averages incompatible positions into a false consensus.
5. **Failure-first, per subsystem.** Each specialist surfaces how its own recommendation breaks before how it wins, so synthesis operates on honest inputs.
6. **The federation as a whole produces artifacts, not actions.** Any execution is gated exactly as in the Agent-Containment pattern — through a human and a Minimal Execution Unit. The federation is a reasoning organ, not an actuator.

## Why "no shared memory, artifact-only" is the load-bearing choice

The moment subsystems share mutable state or call each other directly, three things happen: authority becomes untraceable (who concluded this?), failures propagate silently across boundaries, and the system starts to *feel* like a single opaque intelligence. Keeping exchange to read-only artifacts through one visible synthesis point means every conclusion has a provenance, every boundary is inspectable, and the "one big mind" illusion never forms — because structurally there is no one big mind, only bounded parts and an open synthesis.

## Honest positioning and limits

A **practitioner's architecture pattern**, aligned with well-known ideas: modular design (single responsibility, minimal coupling), microservice-style boundaries applied to reasoning, mixture-of-experts routing at the workflow level, and human-in-the-loop synthesis. Not novel research.

Limits:

- **Latency and cost.** Running several specialists plus synthesis is slower and more expensive than one call. Justified for high-stakes, multi-domain decisions; overkill for simple ones.
- **Synthesis is the hard part.** A weak synthesis kernel can still collapse plurality or launder a specialist's error into a confident conclusion. The pattern moves the risk to one visible place; it does not remove it.
- **Router quality bounds the system.** If the router activates the wrong specialists, downstream quality suffers regardless of the pattern.
- **It composes governed parts.** Federation assumes each specialist is itself governed (framing gate, artifacts, containment). Wiring together ungoverned agents in this shape does not make them safe.

Within those bounds, the pattern lets you scale capability across domains while keeping the two properties that matter: **every conclusion is traceable, and a human holds the pen.**
