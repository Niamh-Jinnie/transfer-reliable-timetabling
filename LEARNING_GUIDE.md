# Learning guide

This guide is intended for a mathematics graduate learning optimisation
modelling for the first time. Do not begin by memorising the Pyomo syntax.
Begin with the mathematical objects and then identify where each one appears
in the code.

## Lesson 1  Understand the data

Open `data/connections.csv` and answer:

1. Which connections have the least existing slack?
2. Which connections carry the most passengers?
3. Why might a passenger-count-only objective favour hub passengers?

Then open `data/delay_scenarios.csv` and verify that scenario probabilities
sum to one.

## Lesson 2  Match mathematics to Pyomo

Read `MODEL.md` before `model.py`.

| Mathematics | Pyomo code |
| --- | --- |
| Set \(C\) | `model.C` |
| Integer variable \(b_c\) | `model.buffer` |
| Binary variable \(y_{cs}\) | `model.made` |
| Buffer budget | `model.buffer_budget` |
| Big-M connection constraint | `model.connection_protection` |
| Objective function | `model.objective` |

Write down, in words, what would happen if `model.made[c, s]` were one and
the feeder delay exceeded the available slack. This is the key to understanding
the binary decision.

## Lesson 3  Run one experiment

After installing the requirements, run:

```bash
python scripts/run_experiments.py
```

Read `results/policy_summary.csv`. Explain why the policies allocate different
amounts of timetable buffer.

## Lesson 4  Perform sensitivity analysis

Change only one parameter at a time:

1. Increase the buffer budget from 12 to 18 minutes.
2. Increase `fairness_weight` from 150 to 300.
3. Double the number of passengers on connection C5.

Before solving, predict the direction of the change. Then compare the solution
with your prediction.

## Lesson 5  Explain the limitations

The data are synthetic, scenarios are few, and connections are linked only by
a shared buffer budget. A larger study would include train circulation,
platform capacity, headway constraints, and empirically estimated delay
distributions. Stating these limitations clearly is part of rigorous research.

## Questions to prepare for an interview

1. Why is this model a MILP rather than an LP?
2. What role does the big-M constant play?
3. Why can a very large M harm numerical performance?
4. Why does passenger weighting create a possible fairness problem?
5. How would you compare this MILP with a decision-diagram formulation?

