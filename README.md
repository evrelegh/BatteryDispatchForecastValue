# Battery Dispatch Forecast Value

## When Better Forecasts Make Better Decisions

**Status: Work in Progress — empirical Belgian market analysis not yet complete.**

This project studies the **economic value of load forecasting in constrained battery dispatch**.

The central question is:

> **Does improved statistical forecast accuracy translate into improved economic battery dispatch, and under what price and state-of-charge conditions does the ranking of forecasts change?**

A deliberately provocative version is:

> **Does a 13.6% MAE gap imply a 13.6% economic-value gap?**

The project follows the chain:

**forecast → uncertainty → dispatch decision → realized economic consequence**

## Research objective

The purpose is not to build yet another load-forecasting benchmark.

The objective is to determine when forecast quality actually changes an operational battery decision, and whether a statistically better forecast produces materially better realized economic performance.

The study therefore separates four questions:

1. How different are the forecasts statistically?
2. Do those forecast differences change the battery dispatch?
3. What is the realized economic consequence?
4. Which forecast errors and operational constraints explain the difference?

## Core methodological point

Under symmetric, unconstrained linear electricity settlement, the load forecast can become irrelevant to optimal battery dispatch.

If grid exchange is unrestricted and imports and exports are settled at the same linear price, forecast load contributes only an additive constant to the dispatch objective.

In that case:

> **forecast error exists, but forecast decision value is zero.**

Forecast value emerges only when additional economic or physical structure is introduced, such as:

- asymmetric import/export prices;
- grid import or export constraints;
- load-dependent constraints;
- nonlinear tariffs;
- demand charges.

This provides an explicit negative control for the empirical study.

## Battery dispatch model

The current model is a deterministic linear program with:

- charging and discharging power limits;
- battery energy-capacity limits;
- charging and discharging efficiency;
- fixed initial state of charge;
- fixed terminal state of charge;
- quarter-hour physical resolution;
- separate grid import and export variables;
- asymmetric import/export settlement.

The optimizer uses a three-stage lexicographic solution procedure:

1. minimize economic settlement cost;
2. among economically equivalent solutions, minimize battery throughput;
3. among remaining equivalent solutions, apply deterministic temporal tie-breaking.

This avoids allowing arbitrary solver degeneracy to masquerade as forecast dependence.

## Temporal integrity

The experiment uses a strict information boundary.

The dispatch decision origin is:

**18:00 Europe/Brussels on D-1**

Only information available at that origin may influence the battery schedule.

Day-ahead Belgian electricity prices are considered known at that point.

Realized future load is used only for ex-post economic evaluation.

The core rule is:

> **Forecast information determines dispatch. Realized outcomes determine ex-post economic value.**

## Belgian day-ahead prices

The physical model always operates on a quarter-hour grid.

For Belgian SDAC prices:

- before **1 October 2025**, hourly day-ahead prices are repeated over the four corresponding quarter-hours;
- from **1 October 2025**, native 15-minute SDAC prices are used.

Civil-day structure is preserved, including DST days with:

- 92 quarter-hours;
- 96 quarter-hours;
- 100 quarter-hours.

ENTSO-E Transparency Platform data will be the primary price source.

## Negative prices and LP cycling

The project explicitly tests a known continuous-LP pathology.

With sufficiently negative electricity prices, simultaneous charging and discharging can become economically attractive because battery losses increase grid consumption while preserving the terminal state of charge.

For the current battery:

- charge efficiency: 0.95;
- discharge efficiency: 0.95;
- round-trip efficiency: 0.9025;
- cycle loss fraction: 0.0975.

A constructed negative-price stress test reproduces this behaviour.

The empirical Belgian price data will determine whether this pathology is material enough to require a mutually exclusive charge/discharge formulation, most likely a MILP.

## Forecast inputs

The project is designed to reuse previously frozen Belgian day-ahead load forecasts without retuning them for battery outcomes.

This is important because the economic analysis must not contaminate the earlier forecast comparison.

The stylised site preserves the temporal structure and relative forecast errors of Belgian system load under linear scaling.

It is **not** intended to represent a statistically typical commercial or industrial site.

## Economic evaluation

The primary economic comparison will evaluate alternative forecast-driven dispatch schedules against realized load.

Planned measures include:

- realized energy cost;
- forecast-induced economic regret;
- perfect-foresight benchmark;
- dispatch differences;
- state-of-charge differences;
- constraint activation;
- attribution of economic loss to specific forecast errors.

A central attribution tool will be the LP dual variables.

Locally, the economic impact of forecast error can be related to a dual-weighted error:

\[
\Delta V \approx \sum_t \lambda_t e_t
\]

where:

- \(e_t = L_t - \hat L_t\) is the load forecast error;
- \(\lambda_t\) is the marginal value associated with the power-balance constraint.

This gives a route from:

**forecast error → economically weighted error → decision change → realized regret**

## Validation philosophy

The project is designed around falsification rather than around obtaining a positive result.

Current validation includes:

- power-balance reconstruction;
- state-of-charge recursion checks;
- terminal-state verification;
- objective reconstruction;
- charge/discharge power bounds;
- symmetric-price forecast-irrelevance negative control;
- asymmetric-price positive control;
- deterministic tie-breaking;
- explicit negative-price cycling stress test.

Current status:

**11 automated tests passing.**

## Project structure

```text
BatteryDispatchForecastValue/
├── README.md
├── pyproject.toml
├── src/
│   └── battery_dispatch_forecast_value/
│       ├── __init__.py
│       └── dispatch.py
├── tests/
│   └── test_dispatch.py
├── notebooks/
│   └── battery_dispatch.ipynb
└── docs/
