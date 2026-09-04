# Better Forecasts, Same Decisions

*The Economic Value of Forecast Accuracy in Constrained Battery Dispatch*

<p align="center">
  <img src="figures/readmepic.png" alt="Better Forecasts, Same Decisions — battery dispatch and load forecasting" width="100%">
</p>

This project measures the **economic value of load-forecast accuracy in constrained battery dispatch**, on Belgian data, end to end:

**forecast → dispatch decision → realized economic consequence.**

The research question:

> **Does improved statistical forecast accuracy translate into improved economic battery dispatch — and how does that relationship depend on battery flexibility and settlement design?**

The provocative version: does a materially better statistical forecast necessarily produce a proportionally better economic decision?

The answer, measured: **no — and under verifiable structural conditions the economic value of the accuracy gap is exactly zero.**

## Headline results

The study compares four day-ahead load-forecast policies — weekly persistence, persistence with a recent-level correction, a frozen Fourier/calendar model with the identical correction, and Elia's operational forecast — plus perfect foresight as an ex-post bound, driving a daily battery-dispatch optimisation against known Belgian day-ahead prices over **333 civil days of 2025** (February–December; January was burned in the upstream forecasting study). On the common support used by the economic experiment, Elia's MAE is about 12% lower than the frozen Fourier/calendar model's MAE.

**1. A structural zero, predicted before the data and confirmed exactly.** For the 50 kW / 100 kWh configuration, maximum discharge power lies below the site's minimum load, so the site can never export and the settlement asymmetry is unreachable. Proposition 2 predicts that forecast differences then have *exactly zero* economic value. Empirically, all four policies produce the same realized cost on all 333 days, under all three settlement regimes, in both experiments — maximum daily spread 7×10⁻¹³ €. Forecast error exists; forecast decision value is zero.

**2. Forecast value emerges with flexibility, and is measured with dependence-aware uncertainty.** Scaling the battery at a fixed 0.5C ratio (Experiment B, ±50 EUR/MWh wedge), the cumulative economic advantage of Elia's forecast over the frozen model per 333 days is:

| Configuration | Observed | 95% block-bootstrap interval |
|---|---:|---|
| 50 kW / 100 kWh | €0.00 | structural zero |
| 75 kW / 150 kWh | €1.17 | [€0.01, €2.48] |
| 100 kW / 200 kWh | €29.91 | [€12.46, €47.97] |
| 150 kW / 300 kWh | €38.50 | [€0.59, €75.23] |

The established core is the 100 kW class, whose intervals exclude zero at all three settlement wedges (±25, ±50, ±100 EUR/MWh). Given the exploratory 21-interval A/B settlement grid, isolated marginal exclusions for the 75 and 150 kW classes are interpreted cautiously.

**3. Statistical improvement is strongly attenuated economically.** On the common support used by the economic experiment, Elia's roughly 12% MAE advantage over the frozen Fourier/calendar model is worth €0–45 per 333 days depending on configuration and settlement — against a no-battery energy bill of roughly €97,500 and perfect-foresight battery value of €3,485 (100 kWh) to €9,558 (300 kWh). Every forecast policy captures at least 95.8% of perfect-foresight value in every configuration. The inter-forecast economic stake is therefore small relative to the underlying energy bill and total battery value capture **under this settlement abstraction**, which deliberately excludes capacity charges, peak-shaving remuneration, imbalance exposure, degradation costs and investment economics.

**4. Two seductive findings were submitted to the study's own inference layer; one died.** An apparent high-wedge reversal (the 150 kW battery earning *less* from the better forecast than the 100 kW battery) has a bootstrap interval of [−€56, +€47] and is reported as not established. The energy-scaling interaction that motivated Experiment B is established at the ±25 wedge ([€4.67, €17.90]) and unresolved at larger wedges.

The general conclusion: **forecast accuracy has no asset-independent economic value.** Its realized value is generated jointly by the error, the feasible dispatch set, and the settlement mechanism — and it can be provably zero while the statistical accuracy gap is large.

## Why forecast value can be exactly zero

Under symmetric linear settlement with sign-unconstrained grid exchange, forecast load contributes only an additive constant to the dispatch objective (Proposition 1): the optimal battery schedule is forecast-independent. Value can only be created by asymmetries or load-dependent structure — and Proposition 2 sharpens this: an import/export price wedge creates value **only if the battery can actually reach the export side**. If maximum discharge power lies below minimum load, the wedge is decoration and irrelevance persists. The 50 kW configuration was retained in both experiments as this analytically predicted negative control.

## Decision model

A daily three-stage lexicographic optimisation per forecast policy: (1) minimise settlement cost — a linear program with charge/discharge limits, energy capacity, 0.95/0.95 efficiencies, and terminal state of charge equal to initial (days decouple; the civil day is the inferential unit); (2) among economically equivalent schedules, minimise battery throughput; (3) among the remainder, minimise the time-weighted total action Σₜ t·Δt·(cₜ+dₜ), favoring earlier action as a deterministic tie-breaker. Stages 2–3 exist so that solver degeneracy — guaranteed while day-ahead prices are hourly — cannot masquerade as forecast dependence.

Belgian negative prices make simultaneous charge/discharge (deliberate efficiency loss) optimal in the relaxed LP on 13 days of the sample. Those day×configuration cases are re-solved with a mutually exclusive MILP formulation, **uniformly for all five policies including perfect foresight**, preserving identical feasible sets and the regret identity R ≥ 0. All MILP stages run at zero relative gap after the R ≥ 0 invariant caught a €0.011 violation caused by the solver's default tolerance — an incident retained in the notebook as evidence the invariants work.

Execution is open-loop: the planned battery schedule is followed exactly; realized load determines metered import/export and realized cost. One rule, identical across policies, so cost differences are attributable to forecasts alone.

## Temporal integrity

Dispatch decisions for day D use only information available at **18:00 Europe/Brussels on D−1**: the day-ahead prices for D (published earlier that afternoon) and the frozen load forecasts. Realized load enters only the ex-post evaluation. Positive and negative controls test the boundary in both directions: shifting pre-origin inputs must move the plan by the predicted amount; perturbing post-origin data must not move it at all.

## Data and provenance

**Prices:** ENTSO-E Transparency File Library, extract `EnergyPrices_12.1.D_r3.1`, twelve monthly files plus the December 2024 edge, SHA-256 manifest and acquisition timestamps recorded. The hourly→15-minute SDAC transition was **detected empirically from the data**: the first Belgian delivery day at native 15-minute resolution is 2025-09-30, one day earlier than the initially assumed 2025-10-01; the correction is documented in the notebook. Hourly prices before the transition are repeated over their four quarter-hours on the UTC axis; DST days (92/96/100 quarter-hours) are preserved throughout. 2025 prices span −462.33 to +517.57 EUR/MWh with 2,081 negative intervals.

**Load and forecasts:** the frozen forecasts from the companion study [ElectricityLoadForecasting](https://github.com/evrelegh/ElectricityLoadForecasting) are reused without retuning, reconstructed from newly acquired Elia ODS001 data and verified to reproduce the frozen confirmation MAEs exactly. The site is a linear scaling of Belgian system load to a ~93 kW-mean stylised site, frozen on pre-confirmation data only. Linear scaling preserves temporal structure and relative forecast errors. The stylised site is not intended as a statistically representative commercial or industrial site; that limitation is stated explicitly wherever the empirical results are interpreted.

**Settlement:** symmetric wedges of ±25, ±50 (primary, frozen before empirical dispatch) and ±100 EUR/MWh around the day-ahead price — a controlled settlement-design axis, not a claim about any commercial tariff.

## Inference

All headline comparisons are paired daily cost differences under a 7-day circular moving-block bootstrap, 10,000 replications, recorded seed, 95% percentile intervals — with **common resampled day indices across configurations, wedges and experiments**, so that physical-design contrasts are inferred on paired days. Exact economic zeros are classified as structural, not sampling, results. Totals are per 333 observed days, not annualised; the sample excludes January, and no claim is made about the direction of that effect.

## Validation

Zero-capacity and constant-price controls (the latter must and does return the all-zero schedule through all three lexicographic stages); power-balance, SoC-recursion, terminal-state and objective reconstruction on every solved day; the value-capture identity V_F = V_PF − R_F verified to 10⁻¹⁴; the physically identical 50 kW configuration reproduced bit-exactly across both experiments and all wedges; regret non-negativity enforced as an invariant. The dual-based attribution of regret to individual forecast errors (Σλₜeₜ) is designed but **deliberately deferred to V2**.

The automated test suite contains **23 tests**.

## Repository

```text
BatteryDispatchForecastValue/
├── README.md
├── pyproject.toml
├── src/battery_dispatch_forecast_value/
│   └── dispatch.py          # LP/MILP builders, lexicographic solver, evaluation
├── tests/
├── notebooks/battery_dispatch.ipynb   # complete research narrative, frozen V1
└── docs/figures/
    └── readmepic.png
```

The notebook carries the empirical argument; reusable optimisation and evaluation logic lives in the package under test.

## Companion work

[ElectricityLoadForecasting](https://github.com/evrelegh/ElectricityLoadForecasting) — the upstream study that produced the frozen forecasts, with its own pre-registered freeze and untouched 2025 confirmation. [ElectricityResourceAdequacy](https://github.com/evrelegh/ElectricityResourceAdequacy) — Belgian generation adequacy on the same public data.

## Data sources

Public **ENTSO-E Transparency Platform** (day-ahead energy prices, Article 12.1.D) and **Elia Open Data** (dataset ods001, measured and forecast Belgian total load).


---

**V1 empirical freeze:** `4504ab3`  
**Automated tests:** 23 passing
