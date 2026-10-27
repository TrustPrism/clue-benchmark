# How to read a clue

Each report has a readable sentence and a formal constraint. This page pairs each active clue type with a true example and a counterexample.
{.lead}

## Reading the notation

- `x(s, a)` means suspect **s** has a value for attribute **a**.
- `c` means the responsible suspect. Crime values equal `x(c, a)`.
- Examples use suspects **A** and **B**, colors red/blue and rooms hall/study.
- Unmentioned attributes can take any permitted values.

Reports may be false only under the public **at-most-k** rule. Structural rules stay trusted. Values may repeat unless distinct assignment is explicitly required.

## A suspect has a value {#unary_positive}

Type: `unary_positive`.

> Suspect "A" has "color" = "red".

- **Formal:** `x(A, color) = red`.
- **True example:** A is red.
- **Counterexample:** A is blue.

## A suspect does not have a value {#unary_negative}

Type: `unary_negative`.

> Suspect "A" has "color" != "red".

- **Formal:** `x(A, color) ≠ red`.
- **True example:** A is blue.
- **Counterexample:** A is red.

## The culprit has a value {#crime_positive}

Type: `crime_positive`.

> The murderer has "color" = "red".

- **Formal:** `x(c, color) = red`.
- **True example:** culprit A is red.
- **Counterexample:** culprit A is blue.

## The culprit does not have a value {#crime_negative}

Type: `crime_negative`.

> The murderer has "color" != "red".

- **Formal:** `x(c, color) ≠ red`.
- **True example:** culprit A is blue.
- **Counterexample:** culprit A is red.

The sampling code categorizes this as indirect. That internal category can differ from everyday language.

## The culprit shares a suspect's value {#crime_same_as}

Type: `crime_same_as`.

> The murderer has the same "color" value as suspect "A".

- **Formal:** `x(c, color) = x(A, color)`.
- **True example:** culprit B is blue and A is blue.
- **Counterexample:** culprit B is red and A is blue.

This does **not** assert that A is responsible. Different suspects can share a value.

## The culprit differs from a suspect {#crime_different_from}

Type: `crime_different_from`.

> The murderer has a different "color" value as suspect "A".

- **Formal:** `x(c, color) ≠ x(A, color)`.
- **True example:** culprit B is red and A is blue.
- **Counterexample:** culprit B is blue and A is blue.

If A is responsible, this report is always false.

## Two suspects share a value {#suspect_same_as}

Type: `suspect_same_as`.

> Suspects "A" and "B" have the same "color" values.

- **Formal:** `x(A, color) = x(B, color)`.
- **True example:** both are red.
- **Counterexample:** A is red and B is blue.

## Two suspects have different values {#suspect_different_from}

Type: `suspect_different_from`.

> Suspects "A" and "B" have different "color" values.

- **Formal:** `x(A, color) ≠ x(B, color)`.
- **True example:** A is red and B is blue.
- **Counterexample:** both are red.

## Someone has both properties {#indirect_positive}

Type: `indirect_positive`.

> At least one suspect has "color" = "red" and "room" = "hall".

- **Formal:** there exists an `s` with `x(s, color) = red` **and** `x(s, room) = hall`.
- **True example:** A is red and in the hall.
- **Counterexample:** A is red/in the study; B is blue/in the hall.

The **same suspect** must satisfy both halves. The clue does not identify that suspect as the culprit.

## Nobody has both properties {#indirect_negative}

Type: `indirect_negative`.

> No suspect has both "color" = "red" and "room" = "hall".

- **Formal:** no `s` has both `x(s, color) = red` and `x(s, room) = hall`.
- **True example:** A is red/in the study; B is blue/in the hall.
- **Counterexample:** A is red/in the hall.

Red by itself is allowed. Being in the hall by itself is allowed. Only their combination is forbidden.

## An unrelated record has a value {#record_positive}

Type: `record_positive`.

> Record COMPONENT: its independent value equals "0".

- **Formal:** `y(COMPONENT, value) = 0`, with declared domain `{0, 1}` and no target variables.
- **True example:** the component's value is 0.
- **Counterexample:** its value is 1.

Each generated component has one in-domain assertion, so the stream is satisfiable and leaves target candidates unchanged. It is not an entailed fact about suspects or culprit attributes.
