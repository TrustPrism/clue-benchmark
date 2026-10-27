# Every active clue predicate

Let x(s,a) be suspect s's value for attribute a, and c the responsible suspect.
Crime values equal x(c,a). A report can be false only under the public at-most-k
rule; structural rules stay trusted. Values may repeat unless distinct is explicit.
In the examples below, A and B are suspect IDs, color has red/blue, and room has
hall/study. Unmentioned assignments are arbitrary permitted values.

## unary_positive

English: `Suspect "A" has "color" = "red".` Formal: x(A,color)=red.
Satisfying: A red. Counterexample: A blue.

## unary_negative

English: `Suspect "A" has "color" != "red".` Formal: x(A,color)≠red.
Satisfying: A blue. Counterexample: A red.

## crime_positive

English: `The murderer has "color" = "red".` Formal: x(c,color)=red.
Satisfying: culprit A red. Counterexample: culprit A blue.

## crime_negative

English: `The murderer has "color" != "red".` Formal: x(c,color)≠red.
Satisfying: culprit A blue. Counterexample: culprit A red. This is categorized as
indirect by the current sampling code; everyday language categories can differ.

## crime_same_as

English: `The murderer has the same "color" value as suspect "A".`
Formal: x(c,color)=x(A,color). Satisfying: culprit B blue, A blue.
Counterexample: culprit B red, A blue. This does not assert c=A; sharing values is allowed.

## crime_different_from

English: `The murderer has a different "color" value as suspect "A".`
Formal: x(c,color)≠x(A,color). Satisfying: culprit B red, A blue.
Counterexample: culprit B blue, A blue. With c=A this report is always false.

## suspect_same_as

English: `Suspects "A" and "B" have the same "color" values.`
Formal: x(A,color)=x(B,color). Satisfying: both red. Counterexample: A red, B blue.

## suspect_different_from

English: `Suspects "A" and "B" have different "color" values.`
Formal: x(A,color)≠x(B,color). Satisfying: A red, B blue. Counterexample: both red.

## indirect_positive

English: `At least one suspect has "color" = "red" and "room" = "hall".`
Formal: ∃s: x(s,color)=red ∧ x(s,room)=hall.
Satisfying: A red/hall. Counterexample: A red/study and B blue/hall.
The same suspect must satisfy both halves; this does not identify the culprit.

## indirect_negative

English: `No suspect has both "color" = "red" and "room" = "hall".`
Formal: ¬∃s: x(s,color)=red ∧ x(s,room)=hall.
Satisfying: A red/study and B blue/hall. Counterexample: A red/hall.
This does not forbid red alone or hall alone.

## record_positive

English: `Record COMPONENT: its independent value equals "0".`
Formal: y(COMPONENT,value)=0 with declared domain {0,1}, disjoint from target variables.
Satisfying: that component's value 0. Counterexample: that value 1.
Each generated component has one such in-domain assertion, so it is satisfiable;
conjoining the stream leaves target candidates unchanged. This is not an entailed
fact about suspects and does not assert anything about culprit attributes.
