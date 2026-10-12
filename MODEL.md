# Mathematical formulation

## Sets

- \(C\): passenger connections.
- \(S\): delay scenarios.
- \(C_H\) and \(C_R\): connections serving hub and regional passengers.

## Parameters

- \(p_s\): probability of scenario \(s\).
- \(n_c\): passenger volume for connection \(c\).
- \(a_c\): existing connection slack in minutes.
- \(d_{cs}\): feeder delay in scenario \(s\).
- \(\bar b_c\): maximum additional buffer for connection \(c\).
- \(B\): total timetable-buffer budget.
- \(\alpha\): cost per added buffer minute.
- \(\beta\): cost per expected missed passenger.
- \(\gamma\): weight placed on service fairness.

## Decision variables

- \(b_c \in \mathbb{Z}_{\ge 0}\): additional buffer allocated to connection \(c\).
- \(y_{cs} \in \{0,1\}\): one when connection \(c\) is protected in scenario \(s\).
- \(g \ge 0\): absolute gap between the hub and regional missed-connection rates.

## Objective

The model minimizes scheduled buffer, expected missed passengers, and the
difference in service reliability between passenger groups:

\[
\min \quad
\alpha \sum_{c \in C} b_c
+ \beta \sum_{c \in C}\sum_{s \in S} p_s n_c(1-y_{cs})
+ \gamma g.
\]

## Constraints

Connection protection is represented by a big-M constraint:

\[
d_{cs} \le a_c+b_c+M(1-y_{cs})
\qquad \forall c \in C, s \in S.
\]

If \(y_{cs}=1\), the existing and additional slack must absorb the feeder
delay. If \(y_{cs}=0\), the constraint is relaxed.

The total additional buffer is limited:

\[
\sum_{c \in C} b_c \le B,
\qquad
0 \le b_c \le \bar b_c.
\]

Let \(r_H\) and \(r_R\) be the passenger-weighted expected missed-connection
rates for hub and regional passengers. The absolute fairness gap is linearized
with:

\[
g \ge r_R-r_H,
\qquad
g \ge r_H-r_R.
\]

This is a mixed-integer linear programme because all objective terms and
constraints are linear, while \(b_c\) is integer and \(y_{cs}\) is binary.

