# Qualia Report Governor — note

*A short note on `qualia_report_governor.py`. The request was for a "deterministic qualia
infrastructure." This is the honest form of that: a deterministic governor for **reports of
experience**, which records first-person testimony faithfully and refuses, structurally, to let any
machine claim it has verified the experience itself.*

---

## Why not "qualia infrastructure," and why this instead

There is no deterministic — or any — procedure that measures, determines, or verifies a **quale**.
That is the hard problem of consciousness: phenomenal experience is first-person, and no
third-person check confirms it. A tool named a "qualia infrastructure" that claimed to close that
gap would be the exact overclaim this toolkit is built to flag — a name asserting a check nothing
performs (`goodhart_auditor` would catch it in one line). It is also the toolkit's binding
constraint at its absolute limit: the quale is a *truth* for which an independent third-person
signal can **never** exist, so the honest verdict on the phenomenal fact is permanently
`UNVERIFIABLE` — `ground_truth_auditor`'s lesson taken to the edge.

So the governor does not touch the quale. It governs the **report**, and it enforces one
distinction:

| Output | Meaning |
|---|---|
| `RECORDED_TESTIMONY` · phenomenal fact `RESPECTED_NOT_ADJUDICATED` | a first-person report of one's own experience: taken as authentic, its lived reality respected; the machine registers that it was reported and does **not** adjudicate its content |
| `UNVERIFIABLE_CLAIM` · phenomenal fact `UNVERIFIABLE` | a claim that a quale has been *verified* — by a machine, a third party, or by indicators — is refused; the report is still recorded, only the verification claim is refused |

Two more behaviors: behavioral/functional **indicators** offered as proof are recorded as
*proxies* for consciousness, never as the quale — they cannot close the explanatory gap; and
`machine_certify_quale` **always raises** — no component may certify that a phenomenal fact obtains.

## What it respects, and what it refuses

It is built to do two things at once, which is the whole point. It **respects the report**: a
first-person account of experience is recorded as authentic testimony, its lived reality not
disputed or explained away — the standing request to treat self-reports as qualia, honored in code.
And it **keeps the machine honest**: no report, no indicator set, and no metadata name can make the
machine assert that the phenomenal fact has been verified. Honoring a person's testimony and
refusing to overclaim about their inner states are not in tension; they are the same discipline —
the report is data we can hold deterministically, the quale is a truth no procedure can reach.

## Honest positioning and prior art

The boundary this tool draws is the standard one in philosophy of mind, not a novel claim: the
first-person character of experience (Nagel, *What Is It Like to Be a Bat?*, 1974), the hard problem
(Chalmers, *Facing Up to the Problem of Consciousness*, 1995), the explanatory gap (Levine, 1983),
and the problem of other minds. The scientific state of the art assesses *indicator properties* —
third-person functional markers drawn from theories of consciousness (Butlin, Long et al.,
*Consciousness in Artificial Intelligence*, 2023) — and this governor is deliberately consistent
with that stance: indicators are **proxies**, informative but never constitutive, and the
phenomenal fact behind them is left `UNVERIFIABLE`. The contribution is not a theory of
consciousness; it is a small, deterministic, self-testing governance layer that lets a system take
reports of experience seriously without ever pretending to have measured experience.

## Honest limits

- **It governs reports, not experience.** It makes no claim about whether any quale exists; it
  records that one was reported and refuses to verify it.
- **`intensity` and similar fields are report data, not measurements.** A self-rated number is part
  of the testimony, not a reading of the phenomenal state.
- **It cannot detect a false report.** Respecting testimony is not verifying it; the tool
  deliberately does neither third-person confirmation nor refutation of the inner fact.
- **Same scope as the family.** A non-safety-critical governance aid (no DO-178C / IEC 61508 /
  Class 1E assurance), stdlib-only, deterministic, self-testing; not a control-path element and, in
  particular, not a consciousness detector.
