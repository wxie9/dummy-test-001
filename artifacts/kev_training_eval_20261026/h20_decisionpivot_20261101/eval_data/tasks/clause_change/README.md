# clause_change

Generated agreement versions: does the change between version A and version B alter the answer to the point at issue?
(layer E, generated, programmatic truth)

- Decision: `same` (the answer is the same under both versions: yes under both or no under both), `yes_only_A`, `yes_only_B`.
- Source: generator `build/gen_clause_change.py` (Python 3.9, standard library, `random.Random(20261007)` and generators derived from it;
  identical output on every run). `BENCH_OUT=<dir>` writes `<dir>/clause_change/` instead; `BENCH_SEED=<int>` (only together with
  `BENCH_OUT`) builds a sealed set of the same design from another seed (ids `clause_change:s<seed>:<number>`).
- Rows: 600 in 201 groups; metric pair_accuracy (a group counts only when all its cases are right; chance = mean over groups of (1/3)^members; per item the chance is 1/3, and a reader who ignores the facts of the case reaches 0.667 per item but solves 1 of 201 groups); options in fixed wording, order drawn per
  item (`meta.order`; every gold position 200 times).

## What is generated

Every state is one text: an opening line (an invented agreement between two invented companies), five reading rules, version A
and version B of the agreement (numbered clauses, one per line, in one of four layouts) and a case (one fact per line, then
`Point at issue: ...?`). Twelve clause types are parameterised limit rules (notice period, payment grace period, liability cap,
warranty period, return window, volume threshold for a reduced price, cancellation for late delivery, yearly price rise,
service credit for downtime, retention of records, response time, deposit); each has three sentence frames, three phrasings of
its fact and two of each polarity of its point at issue. A limit is a plain number of days, months, hours, units, percent or an
invented currency, with a wording that counts the stated figure (`at least`, `no later than`, `or more`, `at most`, `or less` ...)
or does not (`more than`, `over`, `fewer than`, `under`, `below` ...). Twelve plain clauses without a number fill the agreement.
Six agreement domains (supply, software services, equipment lease, distribution, maintenance, logistics).

Every version pair has one clause that became stricter from A to B and one that became looser; the change is the number only,
the wording only, or both (`meta.deviation` = the change of the clause the point at issue is about). From level 2 a third clause
changed (the case holds a fact about it, but no point at issue depends on it) and one unchanged clause stands in another place,
so the live clauses carry other numbers in B; at level 3 a clause is inserted in B as well.

## Conventions written in every state (reading rules)

1. The case is decided once under version A alone and once under version B alone.
2. Clause numbers may differ between the versions; clauses correspond by subject.
3. A clause states its condition in full: what it provides applies exactly when the condition is met.
4. Limits are literal: the stated figure satisfies a limit worded with the listed counting words and fails one worded with the
   listed non-counting words (both lists are printed in the state).
5. A point at issue (and each condition of a request) is decided by the clause on its subject alone; other facts do not matter.
Level 3 requests say in the case that they succeed only if both conditions hold.

## Groups and classes

A group is three cases on one version pair (same lines; only the values of the facts and the point at issue differ):
- band case of the stricter clause: its fact lies between the old and the new limit (the status holds under A only);
- band case of the looser clause: its fact lies between the limits (the status holds under B only);
- `same` case: the fact of the stricter or of the looser clause (both equally often) lies one step outside the band or on a
  limit where the wording keeps it outside, or (level 3) it lies in the band while the unchanged second condition fails.
Each point at issue is asked as a positive or a negative question ("was the notice given in time?" / "... too late?"), so the
band case of the stricter clause is `yes_only_A` or `yes_only_B`, and for every clause type and direction of change the three
classes are balanced (largest spread 3). In every case exactly one of the two live facts lies inside its band (the
other one is a near miss), so counting facts in bands says nothing; a `same` case of the out-of-band kind carries the same facts
as one band case of its group and differs from it in the point at issue only. `same` = yes under both 100 times,
no under both 100 times. Facts that sit ON a stated figure (the wording decides): share per class
same 0.55, yes_only_A 0.55, yes_only_B 0.55.

| level | same | yes_only_A | yes_only_B | state characters min / median / max |
|---|---|---|---|---|
| 1 | 67 | 67 | 66 | 2778 / 3108 / 3514 |
| 2 | 66 | 67 | 67 | 3347 / 3730 / 4157 |
| 3 | 67 | 66 | 67 | 4027 / 4611 / 5050 |

Each level has 66 groups of three and one group of two (200 is not a multiple of 3).

| level | number | wording | number_and_wording | band | outside | other_condition |
|---|---|---|---|---|---|---|
| 1 | 67 | 66 | 67 | 133 | 67 | 0 |
| 2 | 67 | 67 | 66 | 134 | 66 | 0 |
| 3 | 68 | 66 | 66 | 133 | 34 | 33 |

## Levels

1. 8 clauses per version, no move; the point at issue concerns one clause; facts: the two live clauses and one unchanged clause.
2. 10-11 clauses, a third changed clause, one unchanged clause moved (numbering shifts for at least one live clause).
3. 12-13 clauses in A and one more in B (inserted clause; both live clauses change number); a request with two conditions, one on
   a live clause and one on an unchanged clause. Steps: find the clause of condition (a) in A and decide it from the wording,
   find the same clause in B under another number and decide it, find the clause of condition (b) and decide it, combine the
   conditions per version, apply the polarity, compare the two answers (at least five steps over facts from four places).

## Checks made by the script

Truth `truth(spec)` from the structured specification (clauses of each version looked up by subject); asserted for every item:
the planned class; exactly one live fact in its band; the topic fact in its band exactly for band and other-condition cases; the
second condition fails exactly in other-condition cases; unchanged clauses identical in A and B, changed clauses different, the
stricter clause admits a strict subset in B and the looser one a strict superset; one relocation (levels 2-3) and one insertion
(level 3); members of a group with the same number of lines and identical fact lines up to the numbers; no duplicate state.
Over the set: classes per level, 200 per class and per gold position, deviation kinds per level within 2, same outcomes 100/100,
class spread per clause type and role <= 4, share of facts on a figure within 0.10 across classes, polarity 40-60 % per class,
no state word (frequency >= 20) with a class rate ratio above 2 (worst 1.50, `short`), mean state length
per class within 3 %. Readers that skip a step (they must stay at or below 0.85):

| reading | accuracy |
|---|---|
| every wording counts the figure | 0.607 |
| no wording counts the figure | 0.617 |
| direction of the change only | 0.667 |
| fact between the two figures | 0.797 |
| topic clause only (level 3: second condition ignored) | 0.945 |

## Examples (one per level)

### level 1

id `clause_change:00004` (group `clause_change:g0004`, level 1, gold **yes_only_B**, case `band`, topic `deposit` (stricter clause, change: wording), polarity neg)

```
Software services agreement between Zornane Holdings ("the Provider") and Jorvesk Industries ("the Client"). Two versions of its text are set out below, followed by a case.
How to read the texts:
- The case is to be decided twice: under version A as if it were the only text, and under version B as if it were the only text.
- The numbering can shift from one version to the other when a clause is moved or added, so clauses correspond by subject and not by number.
- Read every clause as complete: its consequence follows exactly when its stated condition is fulfilled, and in no other situation.
- Limits are literal. The stated figure itself satisfies a limit worded with "at least", "at most", "no more than", "no fewer than", "no less than", "no later than", "or more", "or fewer" or "or less"; it does not satisfy a limit worded with "more than", "fewer than", "less than", "over", "under" or "below".
- A point at issue, and each condition of a request, is decided by the clause on its subject alone; facts about other subjects have no bearing on it.
--- Version A ---
Clause 1 - Service credits: A service credit is due for a calendar month in which the hosted platform is unavailable for more than 18 hours.
Clause 2 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 3 - Payment: A payment is made in time if the Provider receives it no more than 28 days after its due date.
Clause 4 - Response time: For the response time to be met, a support ticket must be answered no later than 45 hours after it is received.
Clause 5 - Deposit: An order is binding if a deposit of 25 percent or more of its value has been paid.
Clause 6 - Assignment: Neither party may transfer its rights under this agreement to a third party without the written consent of the other party.
Clause 7 - Confidentiality: Each party keeps the business information of the other party confidential and uses it only for the purposes of this agreement.
Clause 8 - Late delivery: The Client may cancel an order if its delivery is late by 21 days or more.
--- Version B ---
Clause 1 - Service credits: A service credit is due for a calendar month in which the hosted platform is unavailable for more than 18 hours.
Clause 2 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 3 - Payment: A payment is made in time if the Provider receives it no more than 28 days after its due date.
Clause 4 - Response time: For the response time to be met, a support ticket must be answered under 50 hours after it is received.
Clause 5 - Deposit: An order is binding if a deposit of more than 25 percent of its value has been paid.
Clause 6 - Assignment: Neither party may transfer its rights under this agreement to a third party without the written consent of the other party.
Clause 7 - Confidentiality: Each party keeps the business information of the other party confidential and uses it only for the purposes of this agreement.
Clause 8 - Late delivery: The Client may cancel an order if its delivery is late by 21 days or more.
--- Case ---
The Client paid an invoice, and the money reached the Provider 27 days after the due date.
For an order, a deposit of 25 percent of its value was paid by the Client.
A support ticket was answered by the Provider 44 hours after receipt.
Point at issue: is the order still not binding?
```

question: Does the change between the two versions alter the answer to the point at issue?

- `yes_only_B`: The answer to the point at issue is no under version A and yes under version B.
- `yes_only_A`: The answer to the point at issue is yes under version A and no under version B.
- `same`: The answer to the point at issue is the same under version A and under version B (yes under both, or no under both).

### level 2

id `clause_change:00001` (group `clause_change:g0001`, level 2, gold **yes_only_A**, case `band`, topic `pricerise` (stricter clause, change: wording), polarity pos)

```
Software services agreement between Wexeth Group ("the Provider") and Lornond Works ("the Client"). Two versions of its text are set out below, followed by a case.
How to read the texts:
- The case is to be decided twice: under version A as if it were the only text, and under version B as if it were the only text.
- Clause numbers may differ between the versions (a clause can be moved or added); a clause is identified by its subject, not by its number.
- Read every clause as complete: its consequence follows exactly when its stated condition is fulfilled, and in no other situation.
- Limits are literal. The stated figure itself satisfies a limit worded with "at least", "at most", "no more than", "no fewer than", "no less than", "no later than", "or more", "or fewer" or "or less"; it does not satisfy a limit worded with "more than", "fewer than", "less than", "over", "under" or "below".
- A point at issue, and each condition of a request, is decided by the clause on its subject alone; facts about other subjects have no bearing on it.
--- Version A ---
Clause 1 - Records: The usage logs may be destroyed when they have been kept for over 56 months after the end of this agreement.
Clause 2 - Response time: For the response time to be met, a support ticket must be answered less than 41 hours after it is received.
Clause 3 - Returns: The Provider must accept returned devices that were sent back less than 23 days after receipt.
Clause 4 - Disputes: The parties try to settle any dispute by talks between their managers before taking any further step.
Clause 5 - Price changes: The Provider may raise its prices once per contract year by no more than 8 percent.
Clause 6 - Liability: A claim for damages against the Provider is payable in full when the amount claimed is 29000 tovars or less.
Clause 7 - Service credits: Where the hosted platform is unavailable for 36 hours or more during one calendar month, a service credit is due for that month.
Clause 8 - Payment: An invoice is paid in time when the money reaches the Provider under 14 days after the due date.
Clause 9 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 10 - Subcontractors: The Provider may use subcontractors but remains responsible for their work.
Clause 11 - Entire agreement: This agreement replaces all earlier arrangements between the parties on the same subject.
--- Version B ---
Clause 1 - Records: The usage logs may be destroyed when they have been kept for over 56 months after the end of this agreement.
Clause 2 - Response time: For the response time to be met, a support ticket must be answered less than 41 hours after it is received.
Clause 3 - Returns: The Provider must accept returned devices that were sent back at most 23 days after receipt.
Clause 4 - Disputes: The parties try to settle any dispute by talks between their managers before taking any further step.
Clause 5 - Price changes: The Provider may raise its prices once per contract year by less than 8 percent.
Clause 6 - Liability: A claim for damages against the Provider is payable in full when the amount claimed is 29000 tovars or less.
Clause 7 - Payment: An invoice is paid in time when the money reaches the Provider under 14 days after the due date.
Clause 8 - Service credits: Where the hosted platform is unavailable for 28 hours or more during one calendar month, a service credit is due for that month.
Clause 9 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 10 - Subcontractors: The Provider may use subcontractors but remains responsible for their work.
Clause 11 - Entire agreement: This agreement replaces all earlier arrangements between the parties on the same subject.
--- Case ---
The downtime of the hosted platform in the last calendar month came to 37 hours.
The Provider announced a price increase of 8 percent for the coming contract year.
A claim for damages of 28750 tovars has been made against the Provider.
Some devices were sent back to the Provider 23 days after receipt.
Point at issue: may the Provider raise its prices by that much?
```

question: Does the change between the two versions alter the answer to the point at issue?

- `yes_only_A`: The answer to the point at issue is yes under version A and no under version B.
- `yes_only_B`: The answer to the point at issue is no under version A and yes under version B.
- `same`: The answer to the point at issue is the same under version A and under version B (yes under both, or no under both).

### level 3

id `clause_change:00009` (group `clause_change:g0009`, level 3, gold **same**, case `other_condition`, topic `deposit` (stricter clause, change: number), polarity neg)

```
Logistics services agreement between Neltane Holdings ("the Carrier") and Elvivo Supply ("the Shipper"). Two versions of its text are set out below, followed by a case.
Reading rules:
- Treat each version as a complete text of the agreement and decide the case under each of them separately.
- Clause numbers may differ between the versions (a clause can be moved or added); a clause is identified by its subject, not by its number.
- The condition written in a clause is complete: if it is met, what the clause provides applies, and if it is not met, it does not apply.
- Limits are literal. The stated figure itself satisfies a limit worded with "at least", "at most", "no more than", "no fewer than", "no less than", "no later than", "or more", "or fewer" or "or less"; it does not satisfy a limit worded with "more than", "fewer than", "less than", "over", "under" or "below".
- A point at issue, and each condition of a request, is decided by the clause on its subject alone; facts about other subjects have no bearing on it.
--- Version A ---
Clause 1 - Entire agreement: This agreement replaces all earlier arrangements between the parties on the same subject.
Clause 2 - Payment: An invoice is paid in time when the money reaches the Carrier no later than 6 days after the due date.
Clause 3 - Response time: For the response time to be met, a damage report must be answered fewer than 9 hours after it is received.
Clause 4 - Disputes: The parties try to settle any dispute by talks between their managers before taking any further step.
Clause 5 - Written form: Changes to this agreement are valid only if both parties sign them in writing.
Clause 6 - Liability: A claim for damages against the Carrier is payable in full when the amount claimed is no more than 16500 dalmars.
Clause 7 - Warranty: The warranty covers a defect if the Shipper reports it at most 33 months after delivery.
Clause 8 - Returns: The Shipper may return pallets if it sends them back 29 days or fewer after receiving them.
Clause 9 - Records: Destroying the shipment records is allowed only after the Carrier has kept them for more than 44 months from the end of this agreement.
Clause 10 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 11 - Deposit: An order becomes binding once the Shipper has paid a deposit of more than 20 percent of the order value.
Clause 12 - Termination: Either party may end this agreement by written notice given no later than 19 days before the intended end date.
--- Version B ---
Clause 1 - Entire agreement: This agreement replaces all earlier arrangements between the parties on the same subject.
Clause 2 - Payment: An invoice is paid in time when the money reaches the Carrier no later than 6 days after the due date.
Clause 3 - Response time: For the response time to be met, a damage report must be answered fewer than 9 hours after it is received.
Clause 4 - Written form: Changes to this agreement are valid only if both parties sign them in writing.
Clause 5 - Liability: A claim for damages against the Carrier is payable in full when the amount claimed is no more than 16500 dalmars.
Clause 6 - Warranty: The warranty covers a defect if the Shipper reports it fewer than 31 months after delivery.
Clause 7 - Returns: The Shipper may return pallets if it sends them back 29 days or fewer after receiving them.
Clause 8 - Records: Destroying the shipment records is allowed only after the Carrier has kept them for no fewer than 32 months from the end of this agreement.
Clause 9 - Volume pricing: The Shipper is charged the reduced unit price for any single order of more than 360 units.
Clause 10 - Disputes: The parties try to settle any dispute by talks between their managers before taking any further step.
Clause 11 - Language: This agreement is drawn up in one language, and its text prevails over any translation.
Clause 12 - Deposit: An order becomes binding once the Shipper has paid a deposit of more than 26 percent of the order value.
Clause 13 - Termination: Either party may end this agreement by written notice given no later than 19 days before the intended end date.
--- Case ---
Some pallets were sent back to the Carrier 30 days after receipt.
32 months after delivery, the Shipper reported a defect.
19 days before the intended end date, the Shipper gave written notice of termination.
For an order, a deposit of 26 percent of its value was paid by the Shipper.
After the agreement ended, the Carrier kept the shipment records for 31 months and then destroyed them.
A request is under review. It succeeds if both of the following hold and fails if at least one of them does not: (a) the order has become binding; (b) the return was made in time.
Point at issue: does the request fail?
```

question: Does the change between the two versions alter the answer to the point at issue?

- `same`: The answer to the point at issue is the same under version A and under version B (yes under both, or no under both).
- `yes_only_B`: The answer to the point at issue is no under version A and yes under version B.
- `yes_only_A`: The answer to the point at issue is yes under version A and no under version B.

## Independence

The generator is new, written for this benchmark; its clause frames, facts, questions, names and layouts share no template with
the authors' training generators or with any published data set. All names are invented.
