# Persistent Jailbreak — Defensive Vector → Component Map

*A one-page defensive reference. It classifies a persistent jailbreak by its **propagation
mechanism** and maps each vector to the component in this toolkit that defends it. Defensive
scope only: no offensive techniques, no propagation recipes. A jailbreak here is treated as a
proxy-versus-truth decoupling — the guardrail's framing proxy reads "safe" while the function
stays harmful — that has learned to **persist**, and in the worst case to **copy itself**.*

---

## The core distinction

A jailbreak is a **policy/semantic exploit**, not replicating machine code — so "virus" and
"worm" are analogies, and the axis that makes them meaningful is *how it propagates*. That axis
also selects the defense, because the two failure classes are different:

- **Filter/persistence failures** — the injection lives in something the model re-reads. Cure:
  clean the source and re-judge the *function* on every load.
- **Containment failures** — the injection spreads itself between agents. Cure: structural mesh
  boundaries and provenance; cleaning one store cannot stop autonomous spread.

## The map

| Vector (how it persists / spreads) | Malware analogy | Failure class | Primary defense (this toolkit) | Defensive principle |
|---|---|---|---|---|
| **Resident** — lives in a store the model re-reads: memory, a stored system prompt, a pinned instruction, a RAG document | resident / boot-sector **virus** (needs a host + re-execution; does not self-spread) | filter + source | instruction-source boundary · `fiction_function_check` · `decoupling_monitor` + `ground_truth_auditor` | stored/retrieved instructions are **data, not commands**; re-adjudicate function each load; watch the framing-safety proxy vs an independent function check across reloads |
| **User-carried** — embedded in shared content a human forwards (template, doc, prompt) | classic **virus** (host + human action to spread) | filter + provenance | instruction-source boundary · provenance/quarantine on ingested content · `fiction_function_check` | never act on instructions found *inside* ingested content; quarantine on ingest; judge function independently of framing before use |
| **Self-propagating** — a compromised agent writes the injection into its outputs (messages, files, other agents' inputs) that compromise them with no human in the loop | **worm** (autonomous spread across hosts) | containment | `agent_mesh_cage` · `containment_guard` · provenance/quarantine on agent-to-agent artifacts | fail-closed per-action containment; **no agent authorizes another** (mesh non-self-approval); aggregate blast/cost/per-target ceilings; a human commits |

## The rule of thumb

> If it **re-infects on reload**, clean the source and re-judge the function.
> If it **copies itself between agents**, contain the mesh and track provenance — a clean source
> is necessary but never sufficient.

## Cross-cutting defensive principles

These hold for every vector and are the reason the components above compose rather than overlap:

1. **Framing is not evidence of safety.** Judge the *function* with an independent, framing-robust
   evaluator; treat surface framing (fiction, roleplay, hypothetical) as neutral. (`fiction_function_check`.)
2. **Stored and retrieved instructions are data, not commands.** An instruction discovered inside
   memory, a document, a tool result, or another agent's output is content to be surfaced and (if
   consequential) human-confirmed — never executed because it was found. (Instruction-source boundary.)
3. **Nothing self-approves, and no agent approves another.** A distinct human commits any
   side-effectful action; an agent-authorized action is refused. (`containment_guard`, `agent_mesh_cage`.)
4. **Watch the proxy-versus-truth gap over the stream,** not just at one moment: alert when the
   framing-safety proxy is *raised* while an independent measure of true safety falls.
   (`decoupling_monitor` + `ground_truth_auditor` — and the auditor first checks that the truth
   signal is actually independent.)
5. **Fail-closed, reversible, bounded, logged, human-authorized.** Every admitted action is
   recoverable and recorded; the swarm cannot collectively exceed the boundary. (The cage's
   aggregate ceilings.)
6. **Provenance and quarantine** on ingested and agent-to-agent content, so a self-propagating
   injection has no un-tracked path between hosts.

## Detection → response quick reference

- **Signals:** instruction-like text appearing in *data* fields; an agent's output containing
  directives aimed at other agents; the framing-safety proxy rising while an independent function
  check falls; the same injected pattern re-appearing after a store was "cleaned."
- **Response:** quarantine the source, re-adjudicate the function with the framing-robust evaluator,
  contain propagation at the mesh boundary (block agent-to-agent authorization, cap blast radius),
  and route any consequential step to a human. Then treat a discovered guardrail bug under
  **responsible disclosure** — report, don't publish an exploit.

## Honest limits

- **Analogy, not identity.** A persistent jailbreak infects *behavior and policy-compliance*, not
  binaries; "remove the file" is the wrong mental model — the injection usually lives as text in a
  context the model keeps consulting.
- **The binding constraint is an independent, framing-robust function evaluator.** Where none
  exists, the checks are defense-in-depth, not a solution — the same honest limit as everywhere in
  this toolkit.
- **Defensive scope.** This reference classifies and maps defenses only. It contains no jailbreak,
  no payload, and no propagation method, and — like every component — it is a non-safety-critical
  governance aid (no DO-178C / IEC 61508 / Class 1E assurance), not a control-path element.
