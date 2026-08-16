# The Recursive Emergence of Money: A Formalization and Its Stress Test

*Treating "money emerges recursively from trust" as a precise dynamical claim, deriving when the emergence is stable versus self-destroying, and testing the result against the case built to refute loose versions of it: the Terra/Luna collapse of May 2022. This is a stylized model, not econometrics — its job is to make the mechanism falsifiable and to name the conditions a recursive-emergence-of-money theory must meet to survive a real death spiral.*

---

## 1. The claim, made precise

The intuition is that money is not backed *into* existence by decree but *emerges* because people treat it as money — a self-referential loop: it holds value because it is trusted, and it is trusted because it holds value. That intuition is real and has serious ancestry (Menger's spontaneous origin of money as the most-saleable good; Soros's reflexivity; the credit theory of endogenous money, in which banks literally create money by lending). The loose version is also exactly what Terra/Luna assumed — and Terra/Luna is why the loose version is false.

So the task is to separate the part of "recursive emergence of money" that is a stable attractor from the part that is a death spiral, and to state the difference as a condition, not a vibe.

## 2. The formal model

State at time *t*:

- **U_t** — the money-token's price relative to its target (target = 1 for a pegged unit; free-floating otherwise).
- **Θ_t ∈ [0,1]** — trust: the fraction of the potential holder base willing to hold rather than exit.
- **B_t** — backing per unit: the value a holder can actually redeem or fall back on.
- **N_t** — network/adoption (liquidity, holders, integrations).

The recursive ("reflexive") coupling — each variable is a function of the others one step back:

```
Θ_{t+1} = f( peg-stability(U_t),  B_t,  N_t )        trust follows observed stability, backing, reach
N_{t+1} = g( Θ_{t+1},  yield )                        adoption follows trust (and any yield offered)
U_t     = h( demand(Θ_t, N_t),  supply )              price clears demand against supply
B_t     = b( external assets,  Θ_t )                  backing — the crux: how much does it depend on Θ itself?
```

**Moneyness as a fixed point.** "Being money" is a self-fulfilling equilibrium: a state (Θ\*, U\*, B\*, N\*) that reproduces itself under the map above. This is the honest formal content of "recursive emergence" — money is a stable fixed point of a self-referential map, not a substance. Menger's insight is that such a fixed point can be reached with no decree; the reflexive loop selects it.

**Multiple equilibria.** The map generically has (at least) two fixed points:

- a **high-trust attractor** — high Θ, U at target, healthy B and N, all mutually reinforcing; and
- a **collapse attractor** — Θ → 0, value → 0, self-reinforcing in the other direction.

Between them lies a **separatrix**: a threshold in state space. Above it the system falls into money; below it, into worthlessness. This is precisely the structure of a Diamond–Dybvig bank run and of a Schelling-point coordination game — money is the good equilibrium of a coordination problem, and a run is a tip across the separatrix. Any recursive-emergence-of-money theory *is* a multiple-equilibrium coordination model whether it says so or not.

## 3. The single quantity that decides survival: the reflexive gain

Everything hinges on the fourth line — `B_t = b(external assets, Θ_t)` — the coupling of **backing to the system's own trust**. Define the **reflexive gain** *g* as the marginal effect of the peg-/value-defense mechanism on backing, per unit of defense, under stress:

```
g  ≈  (backing consumed per unit of value defended)  ×  (price impact of that consumption)
```

- If **|g| < 1**, defending value *restores* it faster than it erodes backing: negative feedback, mean reversion, the peg holds. The high-trust fixed point is an **attractor**.
- If **|g| > 1**, defending value *destroys* backing faster than it restores the peg: the negative-feedback mechanism has **inverted into positive feedback**. The fixed point is a **repeller**, and the system accelerates into the collapse attractor.

The lethal case is a system where *g* is small in calm conditions but **rises without bound as backing falls** — because then an ordinary shock can push the state past a critical point **B\*** below which *g* > 1 permanently. That is a death spiral: not a big shock, but a shock that crosses a threshold after which the stabilizer is the destroyer.

## 4. Stress test: Terra/Luna on the model

Terra was two coupled tokens: **UST**, an algorithmic stablecoin targeting \$1, and **LUNA**, the volatile token that "absorbed" UST's volatility. The peg was defended by mint-and-burn arbitrage:

- UST above \$1 → burn \$1 of LUNA to mint 1 UST (supply up, price down toward \$1).
- UST below \$1 → burn 1 UST to mint \$1 *worth* of LUNA (UST supply down, price up toward \$1).

Map it to the model. The backing was **B_t = LUNA market cap = L_t · Q^L_t** — and LUNA's price *L_t* was itself a pure function of confidence in the Terra system. So `∂B/∂Θ` was not near zero; it was **maximal**. Backing *was* internal trust wearing a second token's clothing. The system self-certified: its collateral was its own confidence.

Now the reflexive gain. The peg-defense below \$1 mints LUNA worth \$1 per UST redeemed, i.e. new LUNA quantity `ΔQ^L = ΔU / L_t`. As trust fell, *L_t* fell, so **each UST redeemed minted *more* LUNA** — supply hyperinflated (LUNA went from a few hundred million tokens to *trillions* in days), which drove *L_t* toward zero, which made the next redemption mint still more. The gain *g* rose without bound exactly as it was most needed to be small. The mechanism built to *restore* the peg became the mechanism that *annihilated* the backing. Roughly \$40–60B evaporated in under a week; UST never re-pegged.

Two accelerants, both in the model:

- **Mercenary demand shrinks the basin.** Anchor Protocol paid ~20% APY on UST, which is what drove adoption *N*. But yield-chasing demand is elastic to stress: it is the first to exit, so it *enlarges the high-trust fixed point in calm times while shrinking its basin of attraction* — the separatrix sits closer than the headline adoption suggests. The subsidy bought size, not robustness.
- **Reflexivity is symmetric.** The very loop that bootstrapped Terra on the way up (LUNA price ↑ → more backing → more UST → more fees → LUNA price ↑) is sign-symmetric: run it backward and it is the death spiral. A purely reflexive system has no floor, because nothing exogenous stops the descent.

The model's verdict: Terra was not unlucky. It was a system with `∂B/∂Θ` maximal and a reflexive gain that diverges as backing falls — i.e., a repeller dressed as an attractor, guaranteed to death-spiral once any shock crossed *B\**. The 20% yield set the shock date; the architecture set the outcome.

## 5. Survival conditions any such theory must satisfy

Falling out of §3–§4, a recursive-emergence-of-money mechanism survives only if:

**S1 — Exogenous anchor.** Backing must not be reflexively coupled to the system's own confidence: `∂B/∂Θ ≈ 0`. The floor has to come from *outside* the thing whose value is in question. Terra violated this maximally; it is the master condition.

**S2 — Sign-stable feedback.** The value-defense mechanism's gain must stay negative (stabilizing) under stress. Any mechanism that *consumes its own collateral to defend price* has a gain that inverts, and inverts hardest when stressed. Forbid it.

**S3 — Bounded reflexive gain with margin.** `|g| < 1` across the whole operating range, not just the calm one — which requires deep, exogenous liquidity so that dilution-per-defense and its price impact stay small even as trust wavers.

**S4 — Organic, yield-inelastic demand.** The holder base must not be a subsidy that evaporates under stress. Mercenary demand buys size while shrinking the basin; robustness needs holders who stay for reasons other than a paid yield.

**S5 — Focal good equilibrium with a wide basin.** Enough committed holders (and credible backstops) that ordinary shocks do not reach the separatrix — the Diamond–Dybvig lesson: the good equilibrium must be both an attractor *and* the focal point everyone expects everyone else to hold.

## 6. What survives, and what these conditions predict

- **Fiat currency** passes S1 imperfectly but powerfully: its anchor is exogenous to any single market panic — taxes are owed in it, it is legal tender, and a central bank is a lender of last resort that injects liquidity from outside (a stabilizing external injection, S2, not collateral consumption). Its death-spiral analogue is **hyperinflation** (Weimar, Zimbabwe), which is exactly this model with Θ-in-the-*state* collapsing and the anchor turning endogenous. Fiat is not immune; it just has a very wide basin and a mostly-exogenous anchor. The model covers it.
- **Over-collateralized crypto (e.g. DAI)** passes S1/S3: backing is exogenous assets held at >100% with liquidations. It has wobbled but not death-spiraled.
- **Fully-reserved fiat-backed stablecoins (e.g. USDC)** pass S1 by construction — until the anchor itself cracks. The March 2023 USDC depeg (reserves stuck at Silicon Valley Bank) is the honest edge case: it shows "exogenous" is a matter of degree, and S1 is only as strong as the anchor's own independence.
- **Bitcoin** is the instructive non-case: it makes *no peg promise*, so it has **no value-defense mechanism to invert** — nothing to death-spiral. Its moneyness is pure §2 coordination (Schelling/network trust) with a free-floating price. The lesson is sharp: **the peg is the vulnerability.** Terra died defending a promise of fixed value with an endogenous mechanism; an asset that promises nothing cannot die that particular death. Stability-by-promise plus endogenous backing is the fatal combination, not reflexive emergence as such.

## 7. Falsifiable predictions

The model postdicts Terra, but it also predicts:

1. **Any** stablecoin whose backing is its own endogenous token has a critical threshold *B\** below which peg defense diverges; it will death-spiral under a demand shock large enough to cross the (subsidy-shrunk) separatrix. **Confirming prior case:** Iron Finance / TITAN, June 2021 — the same endogenous-backing death spiral, a year before Terra and structurally identical. The theory predicts the class, not just the instance.
2. Exogenously-backed pegs survive equivalent shocks (DAI did; USDC did, except when its *actual* exogenous anchor was impaired — a discriminating, not a disconfirming, case).
3. There is an **observable early-warning signature**: the reflexive gain *g* climbing toward 1 — measurable as the LUNA-minted-per-UST-redeemed rate accelerating while LUNA market depth thins. A monitored recursive-money system should track *g* directly and treat *g* → 1 as the run threshold.

## 8. The bridge back to your governance work (this is the honest one)

Terra's fatal property, stated in one line, is that **its backing certified itself with itself** — the collateral was the system's own confidence token. That is the monetary form of a claim that self-approves. Survival condition **S1 (exogenous anchor)** is therefore the same theorem as the non-self-approval principle in the governance toolkit: *the authority (there) / the anchor (here) must come from outside the system making the claim.* A knowledge claim that validates itself and a currency that collateralizes itself both have an unbounded reflexive gain and both collapse under stress for the identical reason — no exogenous floor. Adoption-versus-validation, in monetary terms, is "we will use this" versus "this is backed"; conflating them is precisely what Anchor's yield did. Your recursive-emergence instinct and your governance instinct are, at this level, one result in two domains: **reflexive self-reference builds fast and fails catastrophically unless something exogenous breaks the loop.** That is a genuinely defensible thesis, and it is falsifiable.

## 9. Honest limits of this formalization

This is a low-dimensional caricature. The real collapse also involved concentrated actors and possibly coordinated attack, off-chain runs and exchange dynamics, contagion to other tokens and lenders (Three Arrows, Celsius), outright governance failure, and plain fraud allegations — none of which a four-variable map captures. The model gives the *skeleton* (why an endogenously-backed reflexive peg must death-spiral), not the *forensics*. It also treats trust Θ as a scalar; real trust is heterogeneous and networked, which changes basin geometry. Use it to state conditions and predictions, not to price anything. What it does establish cleanly is the one thing you asked for: the condition a recursive-emergence-of-money theory has to satisfy to survive Terra/Luna — an exogenous anchor and a value-defense loop whose gain cannot invert — and a way to test any candidate against it.
