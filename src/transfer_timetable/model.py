"""MILP model for allocating connection buffers under delay uncertainty.

The data are intentionally small and synthetic. The purpose of the project is
to make the optimisation model transparent enough to inspect, test, and extend.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo


@dataclass(frozen=True)
class Policy:
    """Weights and limits defining one timetable-planning policy."""

    name: str
    buffer_budget: int
    buffer_cost: float
    missed_passenger_cost: float
    fairness_weight: float


@dataclass(frozen=True)
class Instance:
    """Validated input tables used by the optimisation model."""

    connections: pd.DataFrame
    scenarios: pd.DataFrame


def load_instance(data_dir: str | Path) -> Instance:
    """Load and validate the synthetic connection and delay data."""

    data_dir = Path(data_dir)
    connections = pd.read_csv(data_dir / "connections.csv")
    scenarios = pd.read_csv(data_dir / "delay_scenarios.csv")

    required_connections = {
        "connection_id",
        "station_group",
        "passengers",
        "base_slack",
        "max_extra_buffer",
    }
    missing = required_connections.difference(connections.columns)
    if missing:
        raise ValueError(f"connections.csv is missing columns: {sorted(missing)}")

    connection_ids = connections["connection_id"].tolist()
    missing_delays = set(connection_ids).difference(scenarios.columns)
    if missing_delays:
        raise ValueError(
            f"delay_scenarios.csv is missing connections: {sorted(missing_delays)}"
        )

    probability_sum = float(scenarios["probability"].sum())
    if abs(probability_sum - 1.0) > 1e-9:
        raise ValueError(
            f"Scenario probabilities must sum to 1; received {probability_sum:.6f}."
        )

    groups = set(connections["station_group"])
    if groups != {"hub", "regional"}:
        raise ValueError("station_group must contain both 'hub' and 'regional'.")

    return Instance(connections=connections, scenarios=scenarios)


def build_model(instance: Instance, policy: Policy) -> pyo.ConcreteModel:
    """Build the mixed-integer linear programme.

    Decision variables
    ------------------
    buffer[c]
        Extra scheduled connection buffer allocated to connection c (minutes).
    made[c, s]
        One if connection c is protected in delay scenario s, zero otherwise.
    fairness_gap
        Absolute difference between hub and regional missed-connection rates.
    """

    connections = instance.connections.set_index("connection_id")
    scenarios = instance.scenarios.set_index("scenario")
    connection_ids = connections.index.tolist()
    scenario_ids = scenarios.index.tolist()

    passengers = connections["passengers"].to_dict()
    base_slack = connections["base_slack"].to_dict()
    max_extra_buffer = connections["max_extra_buffer"].to_dict()
    station_group = connections["station_group"].to_dict()
    probability = scenarios["probability"].to_dict()
    delay = {
        (connection, scenario): float(scenarios.loc[scenario, connection])
        for connection in connection_ids
        for scenario in scenario_ids
    }

    big_m = max(delay.values()) + max(max_extra_buffer.values()) + 1

    model = pyo.ConcreteModel(name=f"transfer_buffer_{policy.name}")
    model.C = pyo.Set(initialize=connection_ids, ordered=True)
    model.S = pyo.Set(initialize=scenario_ids, ordered=True)

    def buffer_bounds(_model: pyo.ConcreteModel, connection: str) -> tuple[int, int]:
        return 0, int(max_extra_buffer[connection])

    model.buffer = pyo.Var(
        model.C,
        domain=pyo.NonNegativeIntegers,
        bounds=buffer_bounds,
    )
    model.made = pyo.Var(model.C, model.S, domain=pyo.Binary)
    model.fairness_gap = pyo.Var(domain=pyo.NonNegativeReals, bounds=(0, 1))

    model.buffer_budget = pyo.Constraint(
        expr=sum(model.buffer[c] for c in model.C) <= policy.buffer_budget
    )

    def connection_rule(
        _model: pyo.ConcreteModel, connection: str, scenario: str
    ) -> pyo.Constraint:
        # If made[c, s] = 1, the available slack must absorb the scenario delay.
        # If made[c, s] = 0, big-M relaxes the inequality.
        return (
            delay[connection, scenario]
            <= base_slack[connection]
            + _model.buffer[connection]
            + big_m * (1 - _model.made[connection, scenario])
        )

    model.connection_protection = pyo.Constraint(
        model.C, model.S, rule=connection_rule
    )

    def missed_rate_expression(group: str) -> pyo.Expression:
        group_connections = [
            c for c in connection_ids if station_group[c] == group
        ]
        group_passengers = sum(passengers[c] for c in group_connections)
        return sum(
            probability[s] * passengers[c] * (1 - model.made[c, s])
            for c in group_connections
            for s in scenario_ids
        ) / group_passengers

    model.hub_missed_rate = pyo.Expression(expr=missed_rate_expression("hub"))
    model.regional_missed_rate = pyo.Expression(
        expr=missed_rate_expression("regional")
    )
    model.fairness_positive = pyo.Constraint(
        expr=model.fairness_gap
        >= model.regional_missed_rate - model.hub_missed_rate
    )
    model.fairness_negative = pyo.Constraint(
        expr=model.fairness_gap
        >= model.hub_missed_rate - model.regional_missed_rate
    )

    model.expected_missed_passengers = pyo.Expression(
        expr=sum(
            probability[s] * passengers[c] * (1 - model.made[c, s])
            for c in connection_ids
            for s in scenario_ids
        )
    )
    model.total_buffer = pyo.Expression(
        expr=sum(model.buffer[c] for c in connection_ids)
    )
    model.objective = pyo.Objective(
        expr=policy.buffer_cost * model.total_buffer
        + policy.missed_passenger_cost * model.expected_missed_passengers
        + policy.fairness_weight * model.fairness_gap,
        sense=pyo.minimize,
    )

    model._project_data = {
        "connections": connections,
        "scenarios": scenarios,
        "probability": probability,
        "passengers": passengers,
        "station_group": station_group,
        "base_slack": base_slack,
    }
    return model


def solve_model(model: pyo.ConcreteModel, tee: bool = False) -> None:
    """Solve a model with the open-source HiGHS MILP solver."""

    solver = pyo.SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        raise RuntimeError(
            "HiGHS is not available. Install dependencies with "
            "`pip install -r requirements.txt`."
        )
    result = solver.solve(model, tee=tee)
    if result.solver.termination_condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(
            "The solver did not return an optimal solution: "
            f"{result.solver.termination_condition}"
        )


def extract_results(
    model: pyo.ConcreteModel, policy: Policy
) -> tuple[dict[str, float | str], pd.DataFrame]:
    """Convert the optimal Pyomo variable values into tidy tables."""

    data = model._project_data
    connections = data["connections"]
    scenario_ids = data["scenarios"].index.tolist()
    probability = data["probability"]
    passengers = data["passengers"]

    rows: list[dict[str, float | int | str]] = []
    for connection in model.C:
        missed_probability = sum(
            probability[s] * (1 - round(pyo.value(model.made[connection, s])))
            for s in scenario_ids
        )
        rows.append(
            {
                "policy": policy.name,
                "connection_id": connection,
                "origin": connections.loc[connection, "origin"],
                "transfer_station": connections.loc[connection, "transfer_station"],
                "station_group": connections.loc[connection, "station_group"],
                "passengers": int(passengers[connection]),
                "base_slack": int(connections.loc[connection, "base_slack"]),
                "extra_buffer": int(round(pyo.value(model.buffer[connection]))),
                "success_probability": 1 - missed_probability,
                "expected_missed_passengers": passengers[connection]
                * missed_probability,
            }
        )

    detail = pd.DataFrame(rows)
    hub_missed_rate = float(pyo.value(model.hub_missed_rate))
    regional_missed_rate = float(pyo.value(model.regional_missed_rate))
    summary: dict[str, float | str] = {
        "policy": policy.name,
        "objective": float(pyo.value(model.objective)),
        "total_extra_buffer": float(pyo.value(model.total_buffer)),
        "expected_missed_passengers": float(
            pyo.value(model.expected_missed_passengers)
        ),
        "hub_missed_rate": hub_missed_rate,
        "regional_missed_rate": regional_missed_rate,
        # Report the realised gap rather than the auxiliary variable. When the
        # policy gives fairness zero weight, that variable is only bounded from
        # below and a solver may legitimately return any larger feasible value.
        "fairness_gap": abs(hub_missed_rate - regional_missed_rate),
    }
    return summary, detail


def run_policy(
    instance: Instance, policy: Policy, tee: bool = False
) -> tuple[dict[str, float | str], pd.DataFrame]:
    """Build, solve, and extract one policy experiment."""

    model = build_model(instance, policy)
    solve_model(model, tee=tee)
    return extract_results(model, policy)
