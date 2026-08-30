\# Battery Dispatch Forecast Value



\## When Better Forecasts Make Better Decisions



This project studies the economic value of load forecasting in constrained

battery dispatch.



The central question is:



> Does improved statistical forecast accuracy translate into improved

> economic battery dispatch, and under what price and state-of-charge

> conditions does the ranking of forecasts change?



The research chain is:



\*\*forecast → uncertainty → dispatch decision → realized economic consequence\*\*



The project combines:



\- a tested battery-dispatch optimization model;

\- explicit temporal and information-integrity constraints;

\- negative and positive controls for forecast decision value;

\- independent validation of optimization results;

\- empirical Belgian day-ahead electricity prices;

\- frozen out-of-sample load forecasts;

\- realized economic evaluation and regret attribution.



A key methodological point is established analytically and numerically:

under unconstrained symmetric linear settlement, load forecasts do not affect

optimal battery dispatch. Forecast decision value arises only when features

such as import/export price asymmetry, grid constraints, or nonlinear tariffs

make the dispatch problem load-dependent.



The current implementation also explicitly tests the behaviour of the

continuous LP under negative electricity prices, where simultaneous charging

and discharging can become economically optimal through deliberate

round-trip energy losses.



\## Status



Core deterministic battery LP implemented and validated.



Current automated test suite: \*\*11 tests passing\*\*.



Belgian day-ahead price acquisition and the empirical forecast-value

experiment are the next stage.

