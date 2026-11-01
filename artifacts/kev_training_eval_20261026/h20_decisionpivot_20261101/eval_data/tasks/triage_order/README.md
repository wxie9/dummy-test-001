# triage_order

Generated waiting queues: which case do the written ordering rules put at the position asked for? Layer D, generated, programmatic truth, EVALUATION ONLY.

## What is generated

Every state describes one service point (six domains with their own nouns, column names, flags and terms: walk-in clinic, IT support desk, repair workshop, berth planning in a harbour, render farm / print room / batch cluster, citizens' service counter), the current time, numbered ordering rules applied in the order given, the conventions that the rules need, the waiting queue (ticket id, class, arrival time, flag; from level 2 also an appointment time and an expected duration), the meaning of the fields and the position asked for (first; from level 2 also second; at level 3 also third). The question is the same for every item: "Which waiting case do the rules put at the position asked for in the state?" The options are five ticket ids of the queue. Groups of three items share one queue, differ in ONE element and have three different answers among the same five options; one group per level has two members (66 x 3 + 2 = 200).

Truth: `truth(spec)` sorts the cases by a key built from the rules (`sort_key`); a second implementation (`precedes`, pairwise duels over the rules) must give the same strict total order for every item. The order is total by construction: the last rule is the ticket number (unique), or at level 1 an arrival time that no two cases share (stated).

## Conventions written into the state (only those the rules of the item need)

- rules apply in the order given; a later rule only separates cases that every earlier rule leaves level
- class-changing rules are applied first to every case; afterwards "class" means the changed class; up one class = class number minus 1; never above class 1; a moved case is an ordinary member of its new class
- waiting time = current time minus arrival time in minutes (same day, 24-hour clock); "at least W minutes" counts W
- level 3: whether the two class changes add up (two classes up) or not (one class up at most) is stated per item
- an appointment is due when its time is the current time or earlier; due cases are level with each other, and so are not-due cases (no appointment or a later one)
- one order is computed at the current time; first / second / third are places in it
- columns and flags that no rule names have no effect; the ticket number is the number after the dash and is unique

## Levels

| level | cases | rules | class changes | positions asked | rule sets (items) |
|---|---|---|---|---|---|
| 1 | 6 | 2-3 (class is rule 1) | none | {1: 200} | class-arrival (102); class-arrival-ticket (50); class-ticket (48) |
| 2 | 9-10 | 4 | one (waiting limit or flag) | {1: 84, 2: 116} | flag-class-appt-ticket (29); flag-class-arrival-ticket (30); flag-class-mins-ticket (24); wait-class-appt-ticket (48); wait-class-arrival-ticket (24); wait-class-mins-ticket (45) |
| 3 | 12-14 | 5-6 | two (waiting limit and flag) | {1: 64, 2: 73, 3: 63} | wait-flag-class-appt-arrival-ticket (45); wait-flag-class-appt-mins-ticket (27); wait-flag-class-appt-ticket (21); wait-flag-class-arrival-mins-ticket (24); wait-flag-class-arrival-ticket (17); wait-flag-class-mins-arrival-ticket (42); wait-flag-class-mins-ticket (24) |

What makes level 3 hard: (1) the waiting time of every case against W, with waits on W and one to three minutes either side of it; (2) the named flag, among look-alike flags that do nothing; (3) the combination of the two class changes (cumulative or not, as stated) and the floor at class 1; (4) the comparison by changed class; (5) one or two tie-break rules (appointment due at the current time, arrival, duration) in the order written; (6) reading off the second or third place of the resulting order. Every level-3 group is built so that ignoring the waiting rule and ignoring the flag rule each give a wrong answer for at least one member, and ignoring both gives a wrong answer for (nearly) every member.

## Planted differences (items per level)

| kind | element changed | level 1 | level 2 | level 3 |
|---|---|---|---|---|
| arrival | one arrival time (+-1 to 10 min) | 101 | 66 | 50 |
| class | one listed class (+-1; level 1 only) | 99 | 0 | 0 |
| clock | the current time (+-1 to 15 min) | 0 | 68 | 51 |
| flag | one flag cell (set to the named flag, or removed / replaced by another flag) | 0 | 66 | 51 |
| position | the position asked for (level 3) | 0 | 0 | 48 |

`meta.deviation` is the kind of the group for all its members; `meta.variant` 0 is the base member and `meta.change` the element changed in the other members.

## Consistent times (gen_v4)

No time column contradicts another in any domain. The appointment time of a case (slot / callback / pickup / berth window / reserved start / booked time) is never before the arrival time of the same case, and in the workshop, where the appointment is the pickup of the repaired job, never before check-in + bench time; every arrival is before the current time. The dependent time is drawn after the times it depends on (offsets round the current time as before: due earlier, due on the minute, due up to three minutes later, later; an offset that would break the order is drawn again), and a planted arrival change that would break the order is not offered. For every item the queue is parsed back from the rendered text and checked (parsed queue = specification, arrival before the current time, appointment not before the time it depends on). Appointment times: level 2 810 (144 in the workshop), level 3 1168 (207); smallest gap to the time they depend on 0 minutes, exactly on it in 6 cases.

## The class-first shortcut (gen_v4)

The shortcut is the reading "lowest LISTED class first, then earliest arrival, then ticket", with the class changes, the flags, the appointments and the rules actually written all ignored (`meta.readings.class_first_listed`). The table counts the items in which this reading gives the key. Levels 2-3: the generator rejects a group in which the reading gives the key in more than one member and asserts at most 25 % of the items of a level. Level 1: class is rule 1 in every item (the class column is never shown without a rule that uses it); where the rules are class, arrival (, ticket) the reading is the written rule itself, so its hits are not a shortcut.

| level | items | class-first reading = key | of these, the reading is the written rule (level 1) | shortcut hits | share of the items |
|---|---|---|---|---|---|
| 1 | 200 | 152 | 152 | 0 | 0.000 |
| 2 | 200 | 25 | 0 | 25 | 0.125 |
| 3 | 200 | 15 | 0 | 15 | 0.075 |

Level 1, the shortcut "class first, ignore the second rule", is excluded in every member of every group: the top class holds at least two cases (sizes {2: 13, 3: 35, 4: 137, 5: 15}), so the class alone decides in 0 items; the other tie-break (ticket where arrival is written, arrival where ticket is written) gives the key in 0 items; picking at random in the top class would be right in 0.277 of the items, taking the first listed case of the top class in 55 of 200. Markers of level 1 are the neutral ones (no urgent-sounding flag that no rule uses).


## Options and misreadings

The five options of a group are the answers of its members plus the cases that most misreadings point to. Every wrong option of an item has its roles in `meta.option_roles` (counts over all wrong options):

- `no_adjustment` (303): listed class used, every class-changing rule ignored
- `wait_rule_ignored` (128): waiting-time rule ignored (level 3)
- `flag_rule_ignored` (107): flag rule ignored (level 3)
- `combination_swapped` (49): the two class changes combined the other way: added up instead of one step, or the reverse (level 3)
- `limit_not_counted` (63): a wait of exactly W minutes not counted
- `near_wait_counted` (99): waits up to 3 minutes short of W counted
- `no_floor` (163): class allowed to go above class 1
- `any_flag_counted` (57): any flag counted, not only the one the rule names
- `earliest_arrival` (483): earliest arrival overall, rules ignored
- `lowest_ticket` (328): lowest ticket number overall
- `class_first_listed` (343): the class-first shortcut: the LISTED class, then the earliest arrival (adjustments, flags, appointments and the written rules ignored); at level 1 with class then ticket as the rules, the other tie-break
- `class_then_ticket` (152): level 1, class then arrival written: the other tie-break (class, then lowest ticket)
- `class_then_arrival` (208): adjusted class, then arrival, then ticket: the tie-break rules actually written ignored
- `class_reversed` (325): class numbers read the wrong way round
- `last_rule_reversed` (274): the last rule (the tie-break) read in reverse
- `arrival_reversed` (143): arrival rule read in reverse
- `mins_reversed` (101): duration rule read in reverse
- `rules_swapped` (73): the two rules between class and ticket applied in swapped order
- `appointment_any_time` (69): every case with an appointment counted as due
- `appointment_ignored` (67): appointment rule ignored
- `appointment_before_class` (49): appointment rule applied before the class rule
- `appointment_minute_not_due` (34): an appointment at exactly the current time counted as not due
- `next_place` (557): the case one place after the right one
- `previous_place` (140): the case one place before the right one
- `first_place` (21): the first case of the order when the third is asked
- `answer_of_group_member` (1194): the right answer of another member of the group (same queue, one element changed)
- `filler` (58): no misreading points to it

Share of items in which a sloppy reading gives a WRONG answer (wrong / items where the reading applies):

| reading | level 1 | level 2 | level 3 |
|---|---|---|---|
| no_adjustment | - | 183/200 | 191/200 |
| earliest_arrival | 184/200 | 180/200 | 188/200 |
| class_first_listed | 48/200 | 175/200 | 185/200 |
| class_then_ticket | 152/152 | - | - |
| class_then_arrival | - | 107/146 | 136/183 |
| wait_rule_ignored | - | - | 150/200 |
| flag_rule_ignored | - | - | 123/200 |
| combination_swapped | - | - | 59/200 |
| limit_not_counted | - | 32/117 | 37/200 |
| appointment_minute_not_due | - | 8/77 | 30/93 |
| appointment_ignored | - | 23/77 | 55/93 |
| last_rule_reversed | 167/200 | 95/200 | 55/200 |
| lowest_ticket | 188/200 | 178/200 | 182/200 |

Second and third place: how many of the cases ahead of the answer are among the options (ranking only the five options gives the answer only when all of them are; taking the best option only when none is): L2 second: 0 of the cases ahead listed (55); L2 second: 1 of the cases ahead listed (61); L3 second: 0 of the cases ahead listed (31); L3 second: 1 of the cases ahead listed (42); L3 third: 0 of the cases ahead listed (24); L3 third: 1 of the cases ahead listed (20); L3 third: 2 of the cases ahead listed (19).

Rule that separates the answer from its neighbours in the order (items per level): level 1: {'arrival': 135, 'ticket': 65}; level 2: {'appt': 8, 'arrival': 37, 'class': 8, 'mins': 43, 'ticket': 104}; level 3: {'appt': 11, 'arrival': 85, 'class': 1, 'mins': 45, 'ticket': 58}.

## Balance and checks run by the script

- 600 items, 200 per level, 201 groups; gold option place per level L1 [40, 40, 40, 40, 40], L2 [40, 40, 40, 40, 40], L3 [40, 40, 40, 40, 40]
- gold case per row of the listing (queues of one level and size): L1 n=6 [33, 33, 34, 33, 33, 34]; L2 n=9 [11, 11, 11, 11, 12, 11, 12, 11, 11]; L2 n=10 [9, 10, 10, 10, 10, 10, 10, 10, 10, 10]; L3 n=12 [6, 5, 5, 5, 6, 6, 6, 5, 6, 6, 6, 6]; L3 n=13 [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6]; L3 n=14 [5, 5, 5, 5, 5, 5, 4, 5, 4, 4, 5, 5, 4, 5]; by fifths of the list: L1 [66, 34, 33, 33, 34], L2 [41, 42, 43, 43, 31], L3 [46, 41, 40, 41, 32]; mean Kendall tau between listing and true order L1 -0.019, L2 -0.015, L3 -0.003
- asserted for every item: the order is strict and total, `truth` equals the duel implementation, the members of a group differ in exactly the planted element, have different answers, the same number of lines (length gap max 14 characters), all answers are among the five options; no duplicate state; one instruction string
- asserted per level: gold places 40 each, gold rows spread over the rows of the listing (counts per row differ by at most 2), deviation kinds as equal as groups of three allow; at levels 2-3 ignoring the class changes gives a wrong answer in at least 80 % of the items
- the listing order of a queue is redrawn while it equals the true order of a member (or its reverse) or the order by arrival, ticket or listed class
- asserted for every item (gen_v4): the queue parsed back from the rendered text equals the specification; every arrival is before the current time; no appointment time is before the time it depends on (arrival; workshop: arrival + bench time); levels 2-3: the class-first reading gives the key in at most 25 % of the items; level 1 (class is rule 1): the top class has at least two cases in every member and the other tie-break never gives the key
- state characters min/median/max: L1 907/1102/1231; L2 1810/2256/2786; L3 2313/2773/3378
- external checks: `python3 validate.py triage_order`, `python3 audit.py triage_order`, `audit_v3.py triage_order` (numpy)

## Sealed split

`BENCH_OUT=<dir>` writes `<dir>/triage_order/` instead of `tasks/triage_order/`; `BENCH_SEED=<k>` (only together with BENCH_OUT) roots every generator at k instead of 20261007; ids become `triage_order:s<k>:<n>`.

## Examples (one per level)

### Level 1

id `triage_order:00001` (group `triage_order:g0001`, level 1, domain clinic, deviation `class`, variant 1, gold **K-257**; true order K-257, K-225, K-248, K-192, K-253, ...; decided by rule 2 (arrival))

```
Location: Ibarge minor-injuries unit, front counter 9
Current time: 09:52

Rules, applied in the order given:
1. A patient with a lower class number goes before a patient with a higher class number.
2. Earlier arrival first.

Notes on the rules:
- The rules are applied in the order given: a rule decides only between patients that all rules before it leave level.
- Columns and flags that no rule mentions have no effect on the order.
- Every patient in the list has its own "arrived" time; no two are equal.

6 patients are waiting; the list is not sorted in any meaningful way:
ticket,class,arrived,flag
K-253,3,08:38,newfile
K-248,3,08:19,-
K-225,2,09:32,interpreter
K-257,2,09:02,-
K-192,3,08:32,-
K-179,3,09:40,-

Fields of the list:
- ticket: the code under which the patient is queued
- class: the triage class (1 = most urgent)
- arrived: time the patient arrived (today, 24-hour clock)
- flag: a marker noted for the patient; "-" means no marker

Wanted: the patient standing first in the order worked out at the current time
```
question: Which waiting case do the rules put at the position asked for in the state?

- `K-179`: the patient with ticket K-179  (lowest_ticket)
- `K-253`: the patient with ticket K-253  (answer_of_group_member)
- `K-257`: the patient with ticket K-257  (answer)
- `K-248`: the patient with ticket K-248  (earliest_arrival, class_reversed, answer_of_group_member)
- `K-225`: the patient with ticket K-225  (next_place, last_rule_reversed, class_then_ticket)

### Level 2

id `triage_order:00002` (group `triage_order:g0121`, level 2, domain helpdesk, deviation `clock`, variant 0, gold **R-5131**; true order R-5099, R-5131, R-5150, R-5066, R-5070, ...; decided by rule 4 (ticket))

```
Location: customer support queue of Gryurra, shift desk 4
Clock at the moment of the decision: 15:17

10 requests are waiting; the list is not sorted in any meaningful way:
ticket,class,logged,flag,callback,effort
R-5070,3,14:15,-,-,5
R-5099,1,14:27,-,15:20,10
R-5076,3,14:25,remote,-,25
R-5098,4,14:17,-,15:17,15
R-5136,3,14:16,remote,-,20
R-5150,1,13:26,-,-,15
R-5066,2,14:22,blocked,16:01,20
R-5131,2,14:11,-,15:54,15
R-5106,2,14:18,-,-,40
R-5147,3,15:04,hardware,-,25

Meaning of the fields:
- ticket: the code under which the request is queued
- class: priority class; a smaller number means more urgent
- logged: time the request was logged, as HH:MM on today's 24-hour clock
- flag: marker of the request, "-" if none
- callback: time of the agreed callback; "-" means none
- effort: estimated effort in minutes

Rules, applied in the order given:
1. Once the waiting time of a request is at least 60 minutes, it is moved up one class.
2. Lower class number first.
3. Among requests of one class, a request with a due callback slot is ahead of a request without a due one.
4. Lower ticket number first.

Notes on the rules:
- An earlier rule always outranks a later one; a later rule only breaks ties that remain after the rules above it.
- First apply rule 1 to each request; from rule 2 on, the word "class" stands for the changed class.
- "Up one class" is the class number minus 1; for example, class 4 turns into class 3.
- Class 1 is the top: a request never moves above class 1.
- Once moved, a request competes inside its new class on equal terms with the requests already there.
- The waiting time of a request is counted in minutes from the time under "logged" to the current time; all times are today, on a 24-hour clock.
- "At least 60 minutes" includes exactly 60 minutes; 59 minutes are not enough.
- A callback slot counts as due from its own minute on, that is, when it is not later than the current time.
- Two requests that are both due, or both not due (no callback slot, or one that is still to come), stay level under this rule.
- Rank every waiting request once, as things stand at the current time; the position asked for is a place in that ranking.
- Only what the rules name counts; any other column or flag changes nothing.
- Ticket numbers are the digits after the dash, compared as numbers, and they are unique.

Position asked for: second
```
question: Which waiting case do the rules put at the position asked for in the state?

- `R-5106`: request R-5106  (near_wait_counted, answer_of_group_member)
- `R-5131`: request R-5131  (answer)
- `R-5076`: request R-5076  (class_reversed)
- `R-5066`: request R-5066  (answer_of_group_member)
- `R-5150`: request R-5150  (next_place, no_adjustment)

### Level 3

id `triage_order:00003` (group `triage_order:g0196`, level 3, domain helpdesk, deviation `flag`, variant 2, gold **R-643**; true order R-648, R-643, R-667, R-646, R-701, ...; decided by rule 6 (ticket))

```
Location: IT support desk of Kesavenn, line 3
Time now: 15:12

Waiting requests (13), in no particular order:
ticket,class,logged,flag,callback,effort
R-652,2,14:38,-,15:13,15
R-679,3,14:39,outage,15:12,15
R-649,3,14:35,blocked,-,10
R-656,4,14:25,blocked,15:12,15
R-643,2,14:17,-,-,15
R-684,4,14:38,outage,-,25
R-632,3,14:38,outage,-,40
R-701,2,14:37,remote,-,20
R-669,2,13:56,remote,-,40
R-648,2,15:01,outage,15:21,5
R-646,1,14:05,-,15:40,20
R-622,2,14:39,-,15:12,15
R-667,1,14:37,outage,-,15

Fields of the list:
- ticket: queue identifier of the request
- class: the priority class (1 = most urgent)
- logged: time the request was logged (today, 24-hour clock)
- flag: marker of the request, "-" if none
- callback: time of the agreed callback, "-" if there is none
- effort: estimated effort in minutes, whole minutes

The order is fixed by these rules, taken in the order given:
1. Waiting at least 35 minutes lifts a request by one class.
2. A request with the flag "outage" counts one class more urgent.
3. The requests are taken class by class, smallest class number first.
4. Among requests of one class, a request with a due callback slot is ahead of a request without a due one.
5. Shorter estimated effort first.
6. Lower ticket number first.

Notes on the rules:
- The rules are applied in the order given: a rule decides only between requests that all rules before it leave level.
- Rules 1 and 2 change the class of a request and are applied to every request before anything is compared; in the rules after them, "class" means the class after these changes.
- Moving up one class means that the class number becomes one smaller (class 3 becomes class 2).
- Class 1 is the top: a request never moves above class 1.
- A request that has moved up is an ordinary member of its new class; nothing else about it changes.
- To get the waiting time, subtract the "logged" time from the current time (in minutes; same day; 24-hour clock).
- "At least 35 minutes" includes exactly 35 minutes; 34 minutes are not enough.
- Rules 1 and 2 do not add up: a request that meets both still moves up one class only.
- A callback slot is due when its time is the current time or earlier; a later one is not due yet.
- Two requests that are both due, or both not due (no callback slot, or one that is still to come), stay level under this rule.
- The order is worked out once, for all waiting requests, at the current time; first, second and third are positions in this one order.
- Whatever the list shows that no rule uses (a column, a flag) is for information only.
- The ticket number is the number after the dash; no two requests have the same one.

Asked: the request that is second in the order
```
question: Which waiting case do the rules put at the position asked for in the state?

- `R-679`: the request with ticket R-679  (appointment_before_class)
- `R-652`: the request with ticket R-652  (answer_of_group_member)
- `R-667`: the request with ticket R-667  (next_place, last_rule_reversed, class_first_listed, wait_rule_ignored, flag_rule_ignored, answer_of_group_member)
- `R-643`: the request with ticket R-643  (answer)
- `R-646`: the request with ticket R-646  (earliest_arrival, class_then_arrival, no_adjustment, no_floor, appointment_any_time, mins_reversed)

## Independence

The generator is new: all wording, layouts, rules and names were written for this family. It shares no template, sentence or code with the authors' training-data generators or with benchmark v0, and no item comes from an existing data set. All service points, names and identifiers are invented (syllable generator and code-like ticket ids).
