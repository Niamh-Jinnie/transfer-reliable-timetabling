"""Tests for the optimisation model and its policy comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transfer_timetable import Policy, load_instance, run_policy  # noqa: E402


def test_solution_respects_buffer_budget_and_bounds() -> None:
    instance = load_instance(ROOT / "data")
    policy = Policy("test", 12, 2, 1, 100)
    summary, detail = run_policy(instance, policy)

    assert summary["total_extra_buffer"] <= policy.buffer_budget + 1e-8
    max_buffer = instance.connections.set_index("connection_id")[
        "max_extra_buffer"
    ]
    for row in detail.itertuples():
        assert 0 <= row.extra_buffer <= max_buffer.loc[row.connection_id]
        assert 0 <= row.success_probability <= 1


def test_fairness_weight_reduces_group_gap() -> None:
    instance = load_instance(ROOT / "data")
    reliability = Policy("reliability", 12, 2, 1, 0)
    fair = Policy("fair", 12, 2, 1, 150)

    reliability_summary, _ = run_policy(instance, reliability)
    fair_summary, _ = run_policy(instance, fair)

    assert fair_summary["fairness_gap"] <= reliability_summary["fairness_gap"] + 1e-8


def test_expected_missed_passengers_matches_connection_breakdown() -> None:
    instance = load_instance(ROOT / "data")
    policy = Policy("consistency", 12, 2, 1, 150)
    summary, detail = run_policy(instance, policy)

    assert detail["expected_missed_passengers"].sum() == pytest.approx(
        summary["expected_missed_passengers"]
    )


def test_invalid_scenario_probabilities_are_rejected(tmp_path: Path) -> None:
    connections = pd.read_csv(ROOT / "data" / "connections.csv")
    scenarios = pd.read_csv(ROOT / "data" / "delay_scenarios.csv")
    scenarios.loc[0, "probability"] = 0.50
    connections.to_csv(tmp_path / "connections.csv", index=False)
    scenarios.to_csv(tmp_path / "delay_scenarios.csv", index=False)

    with pytest.raises(ValueError, match="probabilities must sum to 1"):
        load_instance(tmp_path)
