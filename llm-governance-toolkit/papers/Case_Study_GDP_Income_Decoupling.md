# Case Study — Detecting a Real Decoupling: GDP per Capita vs Median Household Income

*The decoupling and ground-truth tools (`decoupling_monitor`, `ground_truth_auditor`) run on real,
published US economic data instead of a constructed series, doing on genuine data exactly what they do
in the synthetic demos. Runnable: `real_data_gdp_vs_income.py`.*

---

## Context and question

"The economy grew" is usually stated as one number: real GDP per capita. But GDP per capita is a
**proxy** for something people actually care about — how the typical household is doing — and the
closer **truth** for that is real median household income. The proxy-vs-truth question at the center
of the whole toolkit, asked of real data: do the two move together, or does the headline number drift
from the lived reality it is taken to represent?

## The data (real, cited)

- **Proxy — US real GDP per capita**, chained 2012 dollars, annual 2000–2019 (Bureau of Economic
  Analysis).
- **Truth — US real median household income**, constant dollars, annual 2000–2019 (US Census Bureau /
  FRED series `MEHOINUSA672N`).

Both are indexed to 2000 = 100 inside the tools so the different base years drop out and the series
are directly comparable. One honest caveat carried in the code: the 2019 median-income jump partly
reflects the 2019 CPS ASEC processing change, not only real gains — but the core 2000–2013 decoupling
does not depend on that year.

## Method

Feed the two aligned series to `decoupling_monitor` (which flags when the proxy rises while the gap to
an independent truth opens) and then to `ground_truth_auditor` (which asks the prior question: is the
"truth" actually independent of the proxy, or merely its shadow?). No parameter was tuned to force a
verdict; the co-movement window is disclosed in the code.

## Findings

**A sustained, real decoupling.** `decoupling_monitor` classifies the relationship as **DRIFTING**
from 2002 onward: the proxy kept rising while the gap to the truth widened. Indexed to 2000, real GDP
per capita reached ~115 by 2014 while real median household income sat near ~96 — a **peak gap of
about 19 index points (19.2 in 2014)**. Put plainly: GDP per capita had grown ~15% while the median
household was about **4% below where it started**. Under a tighter co-movement window the monitor
trips a strict **DECOUPLED alert at the early-2010s trough (2012)**. The *drift* is robust across
windows; only the sharper "DECOUPLED" label is window-sensitive, and that sensitivity is disclosed
rather than hidden.

**The independence check refuses to overclaim.** `ground_truth_auditor` asks whether median income is
just a restatement of GDP. Verdict: **UNVERIFIED**, with **51% of median income's variance not
explained by GDP**. Read honestly, that is the correct two-sided answer: median income is **not** a
shadow of GDP (it carries real, independent information — which is exactly why the two *can* diverge),
**and** full independence still cannot be *confirmed* without a labeled reference. The tool declines
to certify in either direction.

## Interpretation

Nobody "gamed" GDP here — this is not manipulation, and that is the point. It is the quieter, more
general failure the toolkit targets: **a single reported number drifting from the reality it is taken
to represent**, so that "the economy is growing" and "the typical household is falling behind" were
both true at once for over a decade. The same shape recurs wherever a proxy is trusted without an
independent check — a peg drifting from its backing, "same price, worse product" inflation, a gamed
benchmark score — and it is caught the same way: watch the proxy against an independent truth, and
first verify that the truth is genuinely independent.

## Honest limits

- **The tools describe a divergence; they do not explain it.** Why median income lagged (labor-share
  decline, inequality, healthcare/housing costs, measurement choices) is an economics question the
  tools do not answer — they detect and refuse to overclaim, nothing more.
- **The "DECOUPLED" label is window-sensitive**; the robust finding is the *drift*, which holds across
  windows. This is stated, not smoothed over.
- **Independence is UNVERIFIED, not CONFIRMED** — by design. A labeled reference would be needed to
  confirm it, and the tool says so rather than pretending.
- **Single dataset, single country, annual resolution.** The result generalizes the *method*, not a
  universal economic claim.

## Lessons

Run on real, cited data, the tools do exactly what they promise on synthetic inputs — detect a genuine
proxy/truth divergence and refuse to certify the ground truth they can't confirm. The case shows the
discipline's value precisely where it is least dramatic: no villain, no gaming, just a headline number
and a lived reality that quietly came apart — the kind of decoupling that stays invisible until
something independent is measured against it.
