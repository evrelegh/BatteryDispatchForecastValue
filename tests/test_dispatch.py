# tests/test_dispatch.py

import numpy as np
import pytest

from battery_dispatch_forecast_value.dispatch import (
    DispatchInputs,
    solve_dispatch,
)


def make_inputs(
    load,
    price,
    *,
    import_adder=0.0,
    export_deduction=0.0,
):
    """
    Small standard battery used throughout the unit tests.
    """

    return DispatchInputs(
        forecast_load_kw=np.asarray(load, dtype=float),
        day_ahead_price_eur_per_mwh=np.asarray(price, dtype=float),
        energy_capacity_kwh=100.0,
        max_charge_kw=50.0,
        max_discharge_kw=50.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        initial_soc_kwh=50.0,
        terminal_soc_kwh=50.0,
        interval_hours=0.25,
        import_adder_eur_per_mwh=import_adder,
        export_deduction_eur_per_mwh=export_deduction,
    )


def test_flat_price_prefers_no_battery_throughput():
    """
    With a positive flat symmetric price and fixed terminal SoC,
    cycling only creates losses.

    The lexicographic solution should therefore leave the battery idle.
    """

    T = 8

    inputs = make_inputs(
        load=np.full(T, 40.0),
        price=np.full(T, 100.0),
    )

    result = solve_dispatch(inputs)

    assert np.allclose(result.charge_kw, 0.0, atol=1e-7)
    assert np.allclose(result.discharge_kw, 0.0, atol=1e-7)
    assert np.allclose(result.soc_kwh, 50.0, atol=1e-7)
    assert result.secondary_throughput_kwh == pytest.approx(
        0.0,
        abs=1e-7,
    )


def test_price_arbitrage_moves_energy():
    """
    A sufficiently large price difference should cause charging in
    the cheap interval and discharging in the expensive interval.
    """

    inputs = make_inputs(
        load=[40.0, 40.0],
        price=[20.0, 200.0],
    )

    result = solve_dispatch(inputs)

    assert result.charge_kw[0] > 1e-6
    assert result.discharge_kw[1] > 1e-6

    assert result.soc_kwh[-1] == pytest.approx(
        50.0,
        abs=1e-7,
    )


def test_power_balance_is_satisfied():
    """
    Reconstruct the forecast power balance independently from
    returned decision variables.
    """

    load = np.array([20.0, 35.0, 50.0, 25.0])
    price = np.array([50.0, 30.0, 120.0, 80.0])

    inputs = make_inputs(load, price)
    result = solve_dispatch(inputs)

    reconstructed_load = (
        result.import_kw
        - result.export_kw
        + result.discharge_kw
        - result.charge_kw
    )

    assert np.allclose(
        reconstructed_load,
        load,
        atol=1e-7,
    )


def test_soc_recursion_is_satisfied():
    """
    Reconstruct every SoC transition independently.
    """

    inputs = make_inputs(
        load=[30.0, 30.0, 30.0, 30.0],
        price=[20.0, 40.0, 150.0, 100.0],
    )

    result = solve_dispatch(inputs)

    for t in range(len(inputs.forecast_load_kw)):
        expected_next_soc = (
            result.soc_kwh[t]
            + inputs.charge_efficiency
            * result.charge_kw[t]
            * inputs.interval_hours
            - result.discharge_kw[t]
            * inputs.interval_hours
            / inputs.discharge_efficiency
        )

        assert result.soc_kwh[t + 1] == pytest.approx(
            expected_next_soc,
            abs=1e-7,
        )


def test_terminal_soc_is_satisfied():
    inputs = make_inputs(
        load=[25.0, 30.0, 45.0, 35.0],
        price=[10.0, 40.0, 200.0, 70.0],
    )

    result = solve_dispatch(inputs)

    assert result.soc_kwh[0] == pytest.approx(
        inputs.initial_soc_kwh,
        abs=1e-7,
    )

    assert result.soc_kwh[-1] == pytest.approx(
        inputs.terminal_soc_kwh,
        abs=1e-7,
    )


def test_objective_reconstructs_from_grid_flows():
    """
    Independently reconstruct the economic objective from returned
    import/export flows.
    """

    load = np.array([30.0, 45.0, 20.0, 50.0])
    price = np.array([25.0, 80.0, 15.0, 160.0])

    inputs = make_inputs(
        load,
        price,
        import_adder=20.0,
        export_deduction=10.0,
    )

    result = solve_dispatch(inputs)

    buy_price = (
        price + inputs.import_adder_eur_per_mwh
    )

    sell_price = (
        price - inputs.export_deduction_eur_per_mwh
    )

    reconstructed_cost = np.sum(
        (
            buy_price * result.import_kw
            - sell_price * result.export_kw
        )
        * inputs.interval_hours
        / 1000.0
    )

    assert result.objective_eur == pytest.approx(
        reconstructed_cost,
        abs=1e-8,
    )


def test_symmetric_price_forecast_irrelevance_negative_control():
    """
    NC-1.

    Under symmetric linear pricing and unconstrained signed grid
    exchange, materially different load forecasts must produce the
    same lexicographically selected battery dispatch.
    """

    price = np.array(
        [20.0, 20.0, 40.0, 80.0, 160.0, 80.0, 40.0, 20.0]
    )

    forecast_a = np.array(
        [20.0, 30.0, 40.0, 50.0, 60.0, 50.0, 30.0, 20.0]
    )

    forecast_b = np.array(
        [150.0, 5.0, 100.0, 10.0, 200.0, 5.0, 120.0, 1.0]
    )

    result_a = solve_dispatch(
        make_inputs(forecast_a, price)
    )

    result_b = solve_dispatch(
        make_inputs(forecast_b, price)
    )

    assert np.allclose(
        result_a.charge_kw,
        result_b.charge_kw,
        atol=1e-6,
    )

    assert np.allclose(
        result_a.discharge_kw,
        result_b.discharge_kw,
        atol=1e-6,
    )

    assert np.allclose(
        result_a.soc_kwh,
        result_b.soc_kwh,
        atol=1e-6,
    )


def test_asymmetric_price_can_make_forecast_change_dispatch():
    """
    PC-1.

    With a non-zero import/export spread, construct two forecasts
    that place the system on different sides of the import/export
    kink. The optimal battery dispatch should then differ.
    """

    price = np.array([20.0, 100.0])

    low_load_forecast = np.array([0.0, 0.0])
    high_load_forecast = np.array([100.0, 100.0])

    low_result = solve_dispatch(
        make_inputs(
            low_load_forecast,
            price,
            import_adder=50.0,
            export_deduction=50.0,
        )
    )

    high_result = solve_dispatch(
        make_inputs(
            high_load_forecast,
            price,
            import_adder=50.0,
            export_deduction=50.0,
        )
    )

    dispatch_difference = max(
        np.max(
            np.abs(
                low_result.charge_kw
                - high_result.charge_kw
            )
        ),
        np.max(
            np.abs(
                low_result.discharge_kw
                - high_result.discharge_kw
            )
        ),
    )

    assert dispatch_difference > 1e-6


def test_invalid_length_mismatch_fails():
    inputs = make_inputs(
        load=[20.0, 30.0],
        price=[50.0, 60.0, 70.0],
    )

    with pytest.raises(ValueError):
        solve_dispatch(inputs)


def test_invalid_efficiency_fails():
    inputs = DispatchInputs(
        forecast_load_kw=np.array([20.0, 20.0]),
        day_ahead_price_eur_per_mwh=np.array([50.0, 50.0]),
        energy_capacity_kwh=100.0,
        max_charge_kw=50.0,
        max_discharge_kw=50.0,
        charge_efficiency=1.20,
        discharge_efficiency=0.95,
        initial_soc_kwh=50.0,
        terminal_soc_kwh=50.0,
    )

    with pytest.raises(ValueError):
        solve_dispatch(inputs)
def test_negative_price_can_induce_simultaneous_battery_cycling():
    """
    Known LP pathology / formulation diagnostic.

    With sufficiently negative settlement prices, simultaneous charging
    and discharging can be economically optimal because battery losses
    permit additional negatively priced grid consumption while preserving
    the terminal state-of-charge constraint.

    This test deliberately documents that behaviour. If the production
    formulation is later strengthened to prohibit simultaneous cycling,
    this test must be replaced rather than silently deleted.
    """

    n = 4

    inputs = DispatchInputs(
        forecast_load_kw=np.full(n, 200.0),
        day_ahead_price_eur_per_mwh=np.full(n, -200.0),
        energy_capacity_kwh=100.0,
        max_charge_kw=50.0,
        max_discharge_kw=50.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        initial_soc_kwh=50.0,
        terminal_soc_kwh=50.0,
        interval_hours=0.25,
        import_adder_eur_per_mwh=0.0,
        export_deduction_eur_per_mwh=0.0,
    )

    result = solve_dispatch(inputs)

    simultaneous_cycle_kw = np.minimum(
        result.charge_kw,
        result.discharge_kw,
    )

    assert np.max(simultaneous_cycle_kw) > 1e-6

    # The constructed case remains entirely on the import side.
    assert np.all(result.import_kw > 0.0)

    assert np.allclose(
        result.export_kw,
        0.0,
        atol=1e-7,
    )

    # Terminal SoC remains satisfied despite deliberate cycling.
    assert np.isclose(
        result.soc_kwh[-1],
        result.soc_kwh[0],
        atol=1e-7,
    )