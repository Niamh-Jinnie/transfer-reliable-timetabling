"""Run the four policy experiments and create reproducible output files."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transfer_timetable import Policy, load_instance, run_policy  # noqa: E402


POLICIES = [
    Policy(
        name="current_timetable",
        buffer_budget=0,
        buffer_cost=0,
        missed_passenger_cost=1,
        fairness_weight=0,
    ),
    Policy(
        name="cost_priority",
        buffer_budget=12,
        buffer_cost=12,
        missed_passenger_cost=1,
        fairness_weight=0,
    ),
    Policy(
        name="reliability_priority",
        buffer_budget=12,
        buffer_cost=2,
        missed_passenger_cost=1,
        fairness_weight=0,
    ),
    Policy(
        name="fair_service",
        buffer_budget=12,
        buffer_cost=2,
        missed_passenger_cost=1,
        fairness_weight=150,
    ),
    Policy(
        name="strong_fairness",
        buffer_budget=12,
        buffer_cost=2,
        missed_passenger_cost=1,
        fairness_weight=300,
    ),
]


def create_plots(summary: pd.DataFrame, details: pd.DataFrame) -> None:
    """Create two figures used in the README and result discussion."""

    figure_dir = ROOT / "results" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    buffer_table = details.pivot(
        index="connection_id", columns="policy", values="extra_buffer"
    )
    buffer_table = buffer_table[[policy.name for policy in POLICIES]]
    ax = buffer_table.plot(kind="bar", figsize=(10, 5))
    ax.set_title("Extra connection buffer allocated by policy")
    ax.set_xlabel("Connection")
    ax.set_ylabel("Extra buffer (minutes)")
    ax.legend(title="Policy")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(figure_dir / "buffer_allocation.png", dpi=180)
    plt.close()

    rates = summary.set_index("policy")[[
        "hub_missed_rate",
        "regional_missed_rate",
    ]]
    rates.columns = ["Hub passengers", "Regional passengers"]
    ax = (100 * rates).plot(kind="bar", figsize=(10, 5))
    ax.set_title("Expected missed-connection rate by passenger group")
    ax.set_xlabel("Policy")
    ax.set_ylabel("Missed-connection rate (%)")
    ax.grid(axis="y", alpha=0.25)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(figure_dir / "missed_rate_by_group.png", dpi=180)
    plt.close()


def main() -> None:
    instance = load_instance(ROOT / "data")
    summaries: list[dict[str, float | str]] = []
    details: list[pd.DataFrame] = []

    for policy in POLICIES:
        summary, detail = run_policy(instance, policy)
        summaries.append(summary)
        details.append(detail)

    summary_frame = pd.DataFrame(summaries)
    detail_frame = pd.concat(details, ignore_index=True)

    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    summary_frame.to_csv(output_dir / "policy_summary.csv", index=False)
    detail_frame.to_csv(output_dir / "connection_results.csv", index=False)
    create_plots(summary_frame, detail_frame)

    display_columns = [
        "policy",
        "total_extra_buffer",
        "expected_missed_passengers",
        "hub_missed_rate",
        "regional_missed_rate",
        "fairness_gap",
    ]
    print(summary_frame[display_columns].round(4).to_string(index=False))
    print(f"\nResults written to {output_dir}")


if __name__ == "__main__":
    main()

