from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class DispatchInputs:
    forecast_load_kw: np.ndarray
    day_ahead_price_eur_per_mwh: np.ndarray
    energy_capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    charge_efficiency: float
    discharge_efficiency: float
    initial_soc_kwh: float
    terminal_soc_kwh: float
    interval_hours: float = 0.25
    import_adder_eur_per_mwh: float = 0.0
    export_deduction_eur_per_mwh: float = 0.0


@dataclass(frozen=True)
class DispatchResult:
    charge_kw: np.ndarray
    discharge_kw: np.ndarray
    import_kw: np.ndarray
    export_kw: np.ndarray
    soc_kwh: np.ndarray
    objective_eur: float
    primary_objective_eur: float
    secondary_throughput_kwh: float
    tertiary_timing_score: float
    solver_message: str


def _validate_inputs(inputs: DispatchInputs) -> None:
    load = np.asarray(inputs.forecast_load_kw, dtype=float)
    price = np.asarray(inputs.day_ahead_price_eur_per_mwh, dtype=float)

    if load.ndim != 1:
        raise ValueError("forecast_load_kw must be one-dimensional.")

    if price.ndim != 1:
        raise ValueError("day_ahead_price_eur_per_mwh must be one-dimensional.")

    if len(load) == 0:
        raise ValueError("At least one physical interval is required.")

    if len(load) != len(price):
        raise ValueError(
            "forecast_load_kw and day_ahead_price_eur_per_mwh "
            "must have identical lengths."
        )

    if not np.all(np.isfinite(load)):
        raise ValueError("forecast_load_kw contains non-finite values.")

    if not np.all(np.isfinite(price)):
        raise ValueError(
            "day_ahead_price_eur_per_mwh contains non-finite values."
        )

    if inputs.energy_capacity_kwh <= 0:
        raise ValueError("energy_capacity_kwh must be strictly positive.")

    if inputs.max_charge_kw <= 0:
        raise ValueError("max_charge_kw must be strictly positive.")

    if inputs.max_discharge_kw <= 0:
        raise ValueError("max_discharge_kw must be strictly positive.")

    if not 0 < inputs.charge_efficiency <= 1:
        raise ValueError("charge_efficiency must lie in (0, 1].")

    if not 0 < inputs.discharge_efficiency <= 1:
        raise ValueError("discharge_efficiency must lie in (0, 1].")

    if inputs.interval_hours <= 0:
        raise ValueError("interval_hours must be strictly positive.")

    if inputs.import_adder_eur_per_mwh < 0:
        raise ValueError(
            "import_adder_eur_per_mwh must be non-negative."
        )

    if inputs.export_deduction_eur_per_mwh < 0:
        raise ValueError(
            "export_deduction_eur_per_mwh must be non-negative."
        )

    if not 0 <= inputs.initial_soc_kwh <= inputs.energy_capacity_kwh:
        raise ValueError(
            "initial_soc_kwh must lie within battery energy bounds."
        )

    if not 0 <= inputs.terminal_soc_kwh <= inputs.energy_capacity_kwh:
        raise ValueError(
            "terminal_soc_kwh must lie within battery energy bounds."
        )


def _indices(T: int) -> dict[str, slice]:
    """
    Variable ordering:

    [charge | discharge | import | export | soc_1 ... soc_T]

    soc_0 is fixed externally at initial_soc_kwh.
    soc_t stored here is the end-of-interval state after interval t.
    """

    return {
        "charge": slice(0, T),
        "discharge": slice(T, 2 * T),
        "import": slice(2 * T, 3 * T),
        "export": slice(3 * T, 4 * T),
        "soc": slice(4 * T, 5 * T),
    }


def _build_primary_problem(
    inputs: DispatchInputs,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[tuple[float | None, float | None]],
]:
    """
    Construct the deterministic day-ahead LP.

    The optimization objective is forecast-based settlement cost.
    """

    load = np.asarray(inputs.forecast_load_kw, dtype=float)
    price = np.asarray(inputs.day_ahead_price_eur_per_mwh, dtype=float)

    T = len(load)
    idx = _indices(T)
    n_variables = 5 * T

    buy_price = price + inputs.import_adder_eur_per_mwh
    sell_price = price - inputs.export_deduction_eur_per_mwh

    objective = np.zeros(n_variables, dtype=float)

    euro_factor = inputs.interval_hours / 1000.0

    objective[idx["import"]] = buy_price * euro_factor
    objective[idx["export"]] = -sell_price * euro_factor

    # ---------------------------------------------------------------
    # Equality constraints
    # ---------------------------------------------------------------

    n_equalities = 2 * T + 1

    A_eq = np.zeros((n_equalities, n_variables), dtype=float)
    b_eq = np.zeros(n_equalities, dtype=float)

    # Power balance:
    # import - export + discharge - charge = forecast load
    for t in range(T):
        row = t

        A_eq[row, idx["charge"].start + t] = -1.0
        A_eq[row, idx["discharge"].start + t] = 1.0
        A_eq[row, idx["import"].start + t] = 1.0
        A_eq[row, idx["export"].start + t] = -1.0

        b_eq[row] = load[t]

    # State-of-charge recursion:
    #
    # soc_t
    #   = soc_{t-1}
    #     + eta_c * charge_t * dt
    #     - discharge_t * dt / eta_d

    for t in range(T):
        row = T + t

        A_eq[row, idx["soc"].start + t] = 1.0

        if t > 0:
            A_eq[row, idx["soc"].start + t - 1] = -1.0
            b_eq[row] = 0.0
        else:
            b_eq[row] = inputs.initial_soc_kwh

        A_eq[row, idx["charge"].start + t] = (
            -inputs.charge_efficiency * inputs.interval_hours
        )

        A_eq[row, idx["discharge"].start + t] = (
            inputs.interval_hours / inputs.discharge_efficiency
        )

    # Fixed terminal state of charge.
    terminal_row = 2 * T
    A_eq[terminal_row, idx["soc"].stop - 1] = 1.0
    b_eq[terminal_row] = inputs.terminal_soc_kwh

    # ---------------------------------------------------------------
    # Variable bounds
    # ---------------------------------------------------------------

    bounds: list[tuple[float | None, float | None]] = []

    bounds.extend(
        [(0.0, inputs.max_charge_kw)] * T
    )

    bounds.extend(
        [(0.0, inputs.max_discharge_kw)] * T
    )

    bounds.extend(
        [(0.0, None)] * T
    )

    bounds.extend(
        [(0.0, None)] * T
    )

    bounds.extend(
        [(0.0, inputs.energy_capacity_kwh)] * T
    )

    return objective, A_eq, b_eq, bounds


def solve_dispatch(
    inputs: DispatchInputs,
    *,
    economic_tolerance_eur: float = 1e-8,
    throughput_tolerance_kwh: float = 1e-8,
) -> DispatchResult:
    """
    Solve the deterministic battery-dispatch LP.

    Lexicographic hierarchy:

    1. minimize economic settlement cost;
    2. among economic optima, minimize total battery throughput;
    3. among those optima, prefer earlier battery activity.

    The tertiary criterion is used only as deterministic tie-breaking.
    It does not alter the primary economic objective.
    """

    _validate_inputs(inputs)

    if economic_tolerance_eur < 0:
        raise ValueError(
            "economic_tolerance_eur must be non-negative."
        )

    if throughput_tolerance_kwh < 0:
        raise ValueError(
            "throughput_tolerance_kwh must be non-negative."
        )

    objective, A_eq, b_eq, bounds = _build_primary_problem(inputs)

    T = len(inputs.forecast_load_kw)
    idx = _indices(T)

    # ---------------------------------------------------------------
    # Stage 1 — economic optimum
    # ---------------------------------------------------------------

    primary = linprog(
        c=objective,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not primary.success:
        raise RuntimeError(
            "Primary dispatch optimization failed: "
            f"{primary.message}"
        )

    primary_optimum = float(primary.fun)

    # ---------------------------------------------------------------
    # Stage 2 — minimum battery throughput
    # ---------------------------------------------------------------

    throughput_objective = np.zeros_like(objective)

    throughput_objective[idx["charge"]] = inputs.interval_hours
    throughput_objective[idx["discharge"]] = inputs.interval_hours

    A_ub_stage2 = objective.reshape(1, -1)

    b_ub_stage2 = np.array(
        [primary_optimum + economic_tolerance_eur],
        dtype=float,
    )

    secondary = linprog(
        c=throughput_objective,
        A_ub=A_ub_stage2,
        b_ub=b_ub_stage2,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not secondary.success:
        raise RuntimeError(
            "Secondary dispatch optimization failed: "
            f"{secondary.message}"
        )

    throughput_optimum = float(secondary.fun)

    # ---------------------------------------------------------------
    # Stage 3 — deterministic temporal tie-break
    # ---------------------------------------------------------------

    timing_objective = np.zeros_like(objective)

    time_weights = np.arange(1, T + 1, dtype=float)

    timing_objective[idx["charge"]] = (
        time_weights * inputs.interval_hours
    )

    timing_objective[idx["discharge"]] = (
        time_weights * inputs.interval_hours
    )

    # Preserve both preceding lexicographic optima.
    A_ub_stage3 = np.vstack(
        [
            objective,
            throughput_objective,
        ]
    )

    b_ub_stage3 = np.array(
        [
            primary_optimum + economic_tolerance_eur,
            throughput_optimum + throughput_tolerance_kwh,
        ],
        dtype=float,
    )

    tertiary = linprog(
        c=timing_objective,
        A_ub=A_ub_stage3,
        b_ub=b_ub_stage3,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not tertiary.success:
        raise RuntimeError(
            "Tertiary dispatch optimization failed: "
            f"{tertiary.message}"
        )

    x = tertiary.x

    charge = x[idx["charge"]].copy()
    discharge = x[idx["discharge"]].copy()
    grid_import = x[idx["import"]].copy()
    grid_export = x[idx["export"]].copy()
    soc_end = x[idx["soc"]].copy()

    soc = np.concatenate(
        (
            np.array([inputs.initial_soc_kwh], dtype=float),
            soc_end,
        )
    )

    reconstructed_primary_objective = float(objective @ x)

    reconstructed_throughput = float(
        throughput_objective @ x
    )

    timing_score = float(
        timing_objective @ x
    )

    return DispatchResult(
        charge_kw=charge,
        discharge_kw=discharge,
        import_kw=grid_import,
        export_kw=grid_export,
        soc_kwh=soc,
        objective_eur=reconstructed_primary_objective,
        primary_objective_eur=primary_optimum,
        secondary_throughput_kwh=reconstructed_throughput,
        tertiary_timing_score=timing_score,
        solver_message=tertiary.message,
    )
