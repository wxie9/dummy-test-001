# sched_conflict

Generated room calendars: can the requested booking be confirmed as it stands? (layer D, generated, programmatic truth)

- Decision: one booking request is checked against the rooms, the written rules and the confirmed bookings; `yes` = it breaks
  nothing and can be confirmed unchanged, `no` = it breaks exactly one planted rule.
- Source: generator `build/gen_sched_conflict.py` (Python 3.9, standard library only, no argument; root `random.Random(20261007)`, every
  other generator derived from it; two runs give identical files). No third-party text; all names are built from syllables.
- Rows: 600 in 300 contrast pairs (`group`), 300 yes / 300 no, 200 per level; metric accuracy (chance 0.5).
- Rebuild: `python3 build/gen_sched_conflict.py` (optional `BENCH_OUT=<dir>`; `BENCH_SEED=<int>` only together with `BENCH_OUT`).

## What is generated

The state is one text with five parts (their order is drawn per pair from three orders): an opening line, the rooms, the rules,
the confirmed bookings and the request. Three layouts (`meta.layout`: table 204, records 198, lines 198 items),
three phrasings of every rule sentence, title and opening sentence, rules as bullets / numbered / one paragraph, rule order
shuffled, five domains with their own words for organiser, attendees, seats and equipment (`meta.domain`), room names as
invented words or codes, booking ids as `B01` or `#214`, list sorted by time, by room or unsorted (`meta.listing`).

Formats that never change: times `HH:MM` (24-hour clock, multiples of 5 minutes), ranges `HH:MM-HH:MM`, durations `N min`,
days `Mon` .. `Fri`, a repeating booking `Mon/Thu`, people `Given Family` separated by `, `, equipment items separated by `, `.
The request gives `start` and `end` at level 1 and `start` and `duration` at levels 2 and 3.

## Conventions (all of them are written in every state that needs them)

| rule | wording in the state (one of three phrasings) | level |
|---|---|---|
| room, touching | two bookings of one room may touch but not overlap | 1 |
| room, reset gap | after a booking the room is blocked for G minutes; the next one may start exactly G minutes later; no gap at opening / closing time. G is one number in the rule (level 2) or listed per kind of room (level 3; a kind may have 0 min) | 2, 3 |
| people | organiser and attendees are busy for the whole booking; nobody is in two bookings that overlap on the same day, whatever the rooms; touching is fine for people, the gap is for rooms only | 2, 3 |
| full names | only identical full names are the same person | 2, 3 |
| hours | inside the opening hours of the room; start at opening time and end at closing time allowed | 1, 2, 3 |
| seats | attendees + 1 for the organiser (never repeated in the attendee list) <= seats; a full room is allowed | 1, 2, 3 |
| equipment | the requested room itself has every needed item, exact names | 2, 3 |
| duration | end = start + duration | 2, 3 |
| repeating | a day field with slashes means the booking exists on each listed day (same room, time, people) | 3 |
| days | bookings on different days never clash | 3 |

At level 1 the people rule is not stated; the script still guarantees that nobody of the request is in an overlapping booking,
so a reader who assumes that rule gets the same answer. The confirmed bookings respect every rule among themselves in both members.

## Levels

| level | rooms | booking lines | days | rules that can be broken | request | reset gap | attendees |
|---|---|---|---|---|---|---|---|
| 1 | 2 | 6-8 | 1 | overlap, hours, seats | start, end | none (touching allowed) | 2-4 |
| 2 | 3-4 | 12-16 | 1 | overlap, person, seats, hours, equipment | start, duration | one value for all rooms | 3-6 |
| 3 | 5-6 | 20-28 (3-8 of them repeating) | 2-3 | the same five | start, duration | by kind of room | 5-8 |

State length in characters (min / median / max): level 1 1276 / 1487 / 1742, level 2 2605 / 3029 / 3645,
level 3 4162 / 4908 / 5916.

**What makes level 3 hard.** A yes needs all of these, a no needs the one that fails, and nothing marks which one:
1. end of the request = start + duration;
2. the kind of the requested room (room list) and the reset gap of that kind (list of gaps);
3. the bookings of that room on that day, including repeating ones whose day field only contains the day among others
   (`Mon/Thu` is a booking on Thursday too), and excluding bookings of the same room at the same clock time on other days
   (present in every level-3 item);
4. for each neighbour: its end + gap <= start of the request, or end of the request + gap <= its start (the positive of an
   `overlap` pair keeps exactly the gap; the negative is 5-15 minutes inside the gap or inside the booking);
5. for each of the 6-9 people of the request: every booking of that day that names them, in the 4-5 other rooms (touching ones
   are fine, a same-time booking on another day is fine, a namesake is another person);
6. opening hours of the room against start and computed end, seats against the count of names plus one, each needed item
   against the equipment list of that one room.
Steps 1, 2 and 4 alone are four operations on facts from four places (request, room list, gap list, booking lines).

**Which check decides (gen_v4).** The reviewers' complaint was that the decisive check was too often one cheap sum on the request
line (start + duration beyond closing time) or the seat count, so that the booking list did not matter. Target shares of the
planted rule among the negatives (and so the accuracy of a reader who checks only hours, seats and equipment and otherwise says
yes: 0.5 + 0.5 x cheap share), and what the items measure:

| negatives per level | level 1 | level 2 | level 3 |
|---|---|---|---|
| target: planted rule needs the booking list (`overlap`, `person`) | 34 % (unchanged, easy level) | 70 % | 85 % |
| target: planted rule is a cheap check (`hours`, `seats`, `equipment`) | 66 % | 30 % | 15 % |
| measured: negatives decided by a cheap check | 66 % | 30 % | 15 % |
| measured: accuracy of the cheap-checks-only reader (table below) | 0.830 | 0.650 | 0.575 |
| measured: `overlap` negatives that lie inside the reset gap only (the request does not touch the neighbour's own time) | - | 94 % (33 of 35) | 91 % (39 of 43) |
| measured: `overlap` / `person` negatives whose decisive booking is a repeating one | - | - | 78 % |
| measured: ... and the day of the request is NOT the first day of its day field | - | - | 64 % |

Level 3 in detail: `overlap` 43, `person` 42, `hours` 5, `seats` 5, `equipment` 5 negatives; level 2: 35 / 35 / 10 / 10 / 10. About 90 %
of the planted overlaps lie in the reset gap of the room kind (the gap list decides, a reader who ignores the gap says yes) and
the neighbour or the conflicting booking is a repeating booking in about 80 % of the items (a reader who reads only the first
day of the day field misses about two thirds of the decisive bookings). The cheap negatives that remain at level 3 are the
ones that need a computation over several facts: `hours` always crosses the closing time through start + duration (or a
closing time moved 15 minutes), `seats` needs a count of 5-8 attendee names plus the organiser against the room, `equipment` needs 2-3
items against the list of one room. In all other items hours, seats and equipment are decoys exactly at their limit: the
requested room is exactly full in about 80 % of them, has exactly the needed equipment in about 70 %, and the request starts
at opening time / ends at closing time in both members wherever the changed field leaves that edge alone (about a quarter of
the items; where the whole request shifts the limit would stay in one member only and would mark a class, so a neighbour of the
room exactly at the gap is the decoy there).

## Deviation kinds (negatives; the positive of the pair is the same state without the change)

| `meta.deviation` | level 1 | level 2 | level 3 | all |
|---|---|---|---|---|
| `overlap` | 34 | 35 | 43 | 112 |
| `person` | - | 35 | 42 | 77 |
| `seats` | 33 | 10 | 5 | 48 |
| `hours` | 33 | 10 | 5 | 48 |
| `equipment` | - | 10 | 5 | 15 |

- `overlap`: a time of the request is moved by 5, 10 or 15 minutes into the neighbouring booking of the room or into its reset gap
  (levels 2 and 3: in about 90 % of the items into the reset gap only, so that the minutes of the gap decide; level 3: the gap is the
  one listed for the kind of the requested room, and the neighbour is a repeating booking in about 80 % of the items).
- `person`: one attendee name is replaced by a person who is in a booking of another room that overlaps the request by 5-15 minutes
  (the replaced person has a booking that only touches the request), or a time of the request is moved by 5-15 minutes into
  a booking that one attendee has in another room. The conflicting person is always in the attendee list of that booking.
- `seats`: the seat number of the requested room is one less than organiser + attendees (positive: exactly equal).
- `hours`: a time of the request is moved 5-15 minutes before opening / after closing time, or the opening / closing time
  of the room is moved by 15 minutes (positive: starts exactly at opening time or ends exactly at closing time). Level 3: only
  the closing side (the end is start + duration, or the closing time is moved 15 minutes earlier), 5 negatives.
- `equipment`: one needed item is replaced by an item the room does not have, or the needed item in the room's list is
  replaced by another item (the other item exists in another room in both members). Levels 2 and 3: the request needs 2-3 items.

The one changed field (`meta.field`), negatives per level 1 / 2 / 3:

| kind | field | level 1 | level 2 | level 3 |
|---|---|---|---|---|
| `overlap` | `request.duration` | 0 | 12 | 15 |
| `overlap` | `request.end` | 18 | 0 | 0 |
| `overlap` | `request.start` | 16 | 23 | 28 |
| `person` | `request.attendee` | 0 | 18 | 21 |
| `person` | `request.duration` | 0 | 6 | 8 |
| `person` | `request.start` | 0 | 11 | 13 |
| `seats` | `room.seats` | 33 | 10 | 5 |
| `hours` | `request.duration` | 0 | 0 | 2 |
| `hours` | `request.end` | 8 | 0 | 0 |
| `hours` | `request.start` | 9 | 5 | 1 |
| `hours` | `room.close` | 8 | 2 | 2 |
| `hours` | `room.open` | 8 | 3 | 0 |
| `equipment` | `request.needs` | 0 | 5 | 2 |
| `equipment` | `room.equipment` | 0 | 5 | 3 |

Domains (items per level 1 / 2 / 3):

| domain | level 1 | level 2 | level 3 |
|---|---|---|---|
| `office` | 40 | 40 | 40 |
| `campus` | 40 | 40 | 40 |
| `studio` | 40 | 40 | 40 |
| `centre` | 40 | 40 | 40 |
| `workshop` | 40 | 40 | 40 |

## Near-limit situations and decoys (share of items that have at least one; yes / no)

| `meta.features` | level 1 | level 2 | level 3 |
|---|---|---|---|
| `room_neighbour_exact` | 0.77 / 0.70 | 0.75 / 0.56 | 0.76 / 0.46 |
| `starts_at_opening` | 0.15 / 0.03 | 0.26 / 0.20 | 0.19 / 0.19 |
| `ends_at_closing` | 0.14 / 0.02 | 0.18 / 0.14 | 0.18 / 0.13 |
| `room_exactly_full` | 0.61 / 0.28 | 0.80 / 0.70 | 0.83 / 0.78 |
| `equipment_exactly_needed` | 0.00 / 0.00 | 0.72 / 0.65 | 0.75 / 0.71 |
| `attendee_meeting_touches` | 0.04 / 0.04 | 0.58 / 0.57 | 0.69 / 0.88 |
| `other_room_same_time` | 0.90 / 0.90 | 1.00 / 1.00 | 1.00 / 1.00 |
| `other_room_booking_touches` | 0.24 / 0.23 | 0.61 / 0.59 | 0.70 / 0.88 |
| `namesake_same_time` | 0.00 / 0.00 | 0.56 / 0.56 | 0.58 / 0.58 |
| `same_room_other_day` | 0.00 / 0.00 | 0.00 / 0.00 | 1.00 / 1.00 |
| `attendee_busy_other_day` | 0.00 / 0.00 | 0.00 / 0.00 | 1.00 / 1.00 |
| `repeating_on_the_day` | 0.00 / 0.00 | 0.00 / 0.00 | 1.00 / 1.00 |
| `other_room_too_small` | 0.40 / 0.40 | 0.64 / 0.64 | 0.93 / 0.93 |
| `other_room_closed` | 0.17 / 0.18 | 0.41 / 0.42 | 0.66 / 0.69 |
| `other_room_lacks_item` | 0.00 / 0.00 | 0.97 / 0.97 | 0.99 / 0.99 |
| `other_room_has_all_items` | 0.00 / 0.00 | 0.65 / 0.65 | 0.69 / 0.69 |

`room_neighbour_exact` = a booking of the requested room keeps exactly the gap to the request (touches it at level 1);
`attendee_meeting_touches` = somebody of the request has a booking in another room that ends when the request starts or starts
when it ends; `other_room_same_time` = a booking in another room during the request; `namesake_same_time` = that booking holds a
person who shares only the first or only the family name with somebody of the request; `same_room_other_day` /
`attendee_busy_other_day` = a booking of the requested room / of somebody of the request at the clock time of the request on
another day; `other_room_*` = another room is too small, closed at that time, or lacks a needed item. All of them are part of
the shared state, so they occur in both classes (small differences come from pairs whose changed field is a time).
The one larger difference is `room_neighbour_exact`: the positive of an `overlap` pair sits ON the gap of its planted neighbour and
its negative, whose time moved, cannot (levels 2 / 3: 43 and 35 of the pairs). Decoys that are exact for the negative only (the
neighbour at exactly the gap of the moved time, in the `person` pairs with a shifted time) and decoys exact in both members (the
start of an `overlap` pair that changes the duration, the unchanged times of the other pairs) compensate part of it; the
hours limit (`starts_at_opening`, `ends_at_closing`), the full room and the exact equipment are equal in the two classes up to
the pairs whose planted rule is that very check.

How far a careless reader gets (accuracy per level 1 / 2 / 3; each row switches ONE convention off, computed on the specification):

| reading | level 1 | level 2 | level 3 |
|---|---|---|---|
| touching bookings of a room read as a clash | 0.615 | 0.625 | 0.620 |
| reset gap ignored | 1.000 | 0.835 | 0.805 |
| largest listed reset gap used for every room | 1.000 | 1.000 | 0.750 |
| smallest listed reset gap used for every room | 1.000 | 1.000 | 0.850 |
| reset gap also demanded between the meetings of a person | 1.000 | 0.655 | 0.575 |
| room ignored: any booking at that time blocks | 0.550 | 0.500 | 0.500 |
| day ignored | 1.000 | 1.000 | 0.500 |
| repeating bookings read on their first day only | 1.000 | 1.000 | 0.730 |
| organiser not counted for the seats | 0.835 | 0.950 | 0.975 |
| opening / closing time itself read as outside | 0.855 | 0.780 | 0.815 |
| people matched by first name | 1.000 | 0.765 | 0.815 |
| only the bookings of the requested room are read (people, seats, hours, equipment skipped) | 0.670 | 0.675 | 0.715 |
| people never checked | 1.000 | 0.825 | 0.790 |
| cheap checks only: hours, seats, equipment (no booking read), otherwise yes | 0.830 | 0.650 | 0.575 |
| always yes | 0.500 | 0.500 | 0.500 |

## Checks made by the script (it stops on the first failure)

- per pair: the confirmed bookings respect every rule among themselves (rooms with the gap, people, hours, seats); the positive
  breaks no rule; the negative breaks exactly the planted rule and nothing else - exactly one neighbour (the planted one, by the
  planted number of minutes), exactly one (person, booking) with an overlap of the planted minutes in another room and in an
  attendee list, exactly one seat, exactly one item, exactly the planted minutes outside the hours; the positive sits on that
  limit (gap kept exactly, room exactly full, start at opening / end at closing, the other booking touches);
- per pair (gen_v4): the route of the planted rule (`meta.route`: rule, decisive booking, repeating or not, day of the request not the
  first listed day, inside the reset gap only) is recomputed from the two specifications and must agree with the draw; a decoy
  placed at opening / closing time stands in both members; an `equipment` pair needs at least two items;
- per pair: exactly one leaf of the two specifications differs and it is the planted field; the two texts have the same number
  of lines and differ in exactly one line; their lengths differ by at most 12 characters (negative longer / equal / shorter:
  0 / 293 / 7 pairs);
- every level-3 item has a booking of the requested room and a booking of somebody of the request at the same clock time on
  another day; every item has a booking in another room during the request; everybody of the request occurs in a confirmed booking;
- whole set: 600 distinct states, 300 / 300, 100 / 100 inside every level, the kinds as in the table, `yes` listed first in
  exactly half of the yes rows and half of the no rows of every level, truth recomputed from `meta.spec` for every row;
- no word occurring in at least 20 states is more than twice as frequent in one class (700 words tested, worst ratio
  1.00); best single threshold on the number of characters 0.502 and on the number of lines 0.500.

Random draws that cannot be completed (no free room for a planted booking, and so on) are drawn again with the next derived
generator: 1.3 draws per pair on average, at most 5.

## Examples (one per level)

### Level 1

`sched_conflict:00002` (group `sched_conflict:g0209`, level 1, domain centre, gold **no**, planted kind of the pair `overlap`, changed field of the pair `request.end`)

```
Booking sheet for the activity rooms of Linford Community Centre; 24-hour clock. All listed bookings are confirmed and cannot be moved. The request is judged as written: every rule must hold for it.

Booking rules:
- A room holds one activity at a time. Back-to-back is fine: a booking may begin exactly when the previous one in that room ends.
- Everyone needs a place: the host plus all guests must not exceed the places of the room. The host is never repeated among the guests.
- No booking may start before its room opens or end after it closes. Starting at opening time or ending at closing time is fine.

Rooms:
- Pephis: places 2; open 08:30-16:00
- Ixalume: places 4; open 07:00-17:45

Bookings already confirmed:
- #435: room Ixalume; day Mon; time 09:20-10:00; host Phobel Mundune; guests Gresso Falkald, Jodra Frorald
- #441: room Pephis; day Mon; time 09:40-10:15; host Kyvek Jorveth; guests Robel Thornume
- #447: room Ixalume; day Mon; time 11:05-12:35; host Kyvek Jorveth; guests Robel Thornume
- #454: room Pephis; day Mon; time 11:15-12:05; host Gresso Falkald; guests Silia Halven
- #455: room Pephis; day Mon; time 13:10-13:50; host Jodra Frorald; guests Samir Rundune
- #456: room Ixalume; day Mon; time 15:05-15:45; host Samir Rundune; guests Alsha Tolvald, Lumir Selvume

Request:
- room: Ixalume
- day: Mon
- start: 10:00
- end: 11:15
- host: Lumir Selvume
- guests: Alsha Tolvald, Samir Rundune
```

Question: Can the requested booking be confirmed as it stands?

- `no`: No - the request breaks at least one of the stated rules and cannot be confirmed as written.
- `yes`: Yes - the request breaks none of the stated rules and can be confirmed as written.

what the request breaks (`meta.evidence`): `{"overlap": ["#447"]}`

### Level 2

`sched_conflict:00040` (group `sched_conflict:g0028`, level 2, domain office, gold **yes**, planted kind of the pair `person`, changed field of the pair `request.attendee`)

```
Dorby Group: meeting rooms and their bookings (24-hour clock). The listed bookings are confirmed and fixed. The new request is confirmed only if, exactly as written, it breaks none of the rules.

== Conventions ==
- Capacity: the number of attendees plus one for the organiser (who is not listed among the attendees) must not exceed the seats of the room; equal is allowed.
- Opening hours are binding: start not earlier than the opening time of the room, end not later than its closing time, equality allowed.
- The request gives a start time and a duration; it ends at start + duration.
- Full names identify people: the same first name with another family name is another person.
- Everyone named in a booking (organiser or attendee) is occupied for its whole length; the request fails if one of its people is occupied by another booking of that day during any part of it. Back-to-back meetings are fine for people; only rooms need the reset gap.
- A room needs 5 minutes of reset between bookings: if one ends at time T, the next booking of that room may start at T + 5 minutes or later, not before. No reset is needed after opening or before closing time.
- Each item the request needs must be in the equipment list of the requested room itself; an item with a different name is a different item.

== Available rooms ==
- L-142: seats 5; equipment projector, wall screen, whiteboard, video link; open 07:30-18:45
- N-141: seats 9; equipment whiteboard, wall screen, video link; open 07:00-18:30
- H-467: seats 7; equipment document camera, projector; open 07:30-18:45
- P-419: seats 5; equipment flip chart, document camera, video link, conference phone; open 07:00-13:30

== Confirmed bookings ==
- #378: room N-141; day Wed; time 07:50-08:25; organiser Aldra Oskossa; attendees Lerik Daskune, Darik Vardald, Kasha Cresossa, Ludan Yeldard
- #380: room H-467; day Wed; time 17:00-17:45; organiser Elbel Skarholm; attendees Ludan Yeldard
- #387: room P-419; day Wed; time 07:50-08:10; organiser Sadan Frorell; attendees Frevek Thornen
- #393: room L-142; day Wed; time 08:35-09:20; organiser Aldra Oskossa; attendees Darik Vardald, Nisha Dunnista, Lerik Daskune
- #398: room P-419; day Wed; time 08:15-08:45; organiser Panis Arvume; attendees Elbel Skarholm
- #403: room L-142; day Wed; time 11:25-12:10; organiser Clenna Hestossa; attendees Aldra Oskossa
- #409: room H-467; day Wed; time 14:05-14:35; organiser Nisha Dunnista; attendees Phonna Halvard, Ludan Yeldard
- #410: room H-467; day Wed; time 08:30-09:15; organiser Ludan Yeldard; attendees Phonna Halvard
- #416: room N-141; day Wed; time 08:30-09:10; organiser Britor Iskik; attendees Orsha Grimari
- #422: room P-419; day Wed; time 07:15-07:45; organiser Tolia Lindald; attendees Roya Kirsald
- #429: room P-419; day Wed; time 08:50-09:15; organiser Tolia Lindald; attendees Grelo Rostald, Roya Kirsald, Kasha Cresossa, Panis Arvume
- #433: room H-467; day Wed; time 08:00-08:25; organiser Tolia Lindald; attendees Britor Iskik

== Requested booking ==
- room: L-142
- day: Wed
- start: 07:30
- duration: 60 min
- organiser: Orsha Grimari
- attendees: Nisha Dunnista, Phonna Halvard, Clenna Hestossa
- needs: whiteboard, wall screen
```

Question: Can the requested booking be confirmed as it stands?

- `no`: No - the request breaks at least one of the stated rules and cannot be confirmed as written.
- `yes`: Yes - the request breaks none of the stated rules and can be confirmed as written.

the request breaks nothing; in its partner item the field named above is changed

### Level 3

`sched_conflict:00006` (group `sched_conflict:g0190`, level 3, domain workshop, gold **no**, planted kind of the pair `person`, changed field of the pair `request.start`)

```
Varford Makers Yard: training rooms and their bookings (24-hour clock). Confirmed bookings stay as they are. The request is confirmed unchanged or not at all, which needs every rule to hold for it.

Requested booking
B-375, Wed, start 13:30, duration 120 min. Trainer: Salo Thornari. Trainees: Gator Rostari, Witor Garnari, Lemir Evrell, Ulrik Cresald, Quimir Laskari, Xalia Oskari, Nesso Wrenell. Needs: laser cutter, welding bay.

Rooms
N-266 (classroom): 4 seats; open 09:00-19:00; equipment: soldering irons.
H-201 (classroom): 12 seats; open 08:45-16:00; equipment: table saw, laser cutter.
B-375 (machine shop): 8 seats; open 08:00-18:15; equipment: welding bay, laser cutter.
G-250 (machine shop): 12 seats; open 07:00-13:00; equipment: welding bay, plasma cutter, test rig.
T-138 (electronics lab): 4 seats; open 07:45-18:30; equipment: soldering irons.

Kinds of room and their reset gap
classroom 30 min; machine shop 15 min; electronics lab 10 min.

Confirmed bookings
#592. H-201, Tue/Wed, 12:20-13:40. Trainer: Sidan Nervard. Trainees: Allia Yeldossa, Tevin Jorvow, Xalia Oskari, Modra Lindune, Frelia Perrari.
#598. N-266, Tue, 17:10-17:40. Trainer: Modra Lindune. Trainees: Driya Tolvov.
#603. N-266, Tue/Wed, 18:10-18:30. Trainer: Xalia Oskari. Trainees: Sidan Nervard, Modra Lindune, Ulrik Cresald.
#609. G-250, Wed, 10:20-10:45. Trainer: Nesso Wrenell. Trainees: Rulia Dunnista, Xalia Oskari, Ulrik Cresald.
#612. H-201, Tue, 15:10-15:40. Trainer: Rulia Dunnista. Trainees: Quimir Laskari.
#616. H-201, Tue/Wed, 10:35-11:50. Trainer: Frelia Perrari. Trainees: Salo Thornari, Gator Rostari, Quimir Laskari, Masso Vardow.
#621. N-266, Wed, 12:35-13:30. Trainer: Nesso Wrenell. Trainees: Lemir Evrell, Kaya Ulmune, Lumir Martista.
#624. G-250, Wed, 07:55-09:40. Trainer: Lumir Martista. Trainees: Masso Vardow, Frelia Perrari, Lemir Evrell, Witor Garnari.
#627. T-138, Wed, 13:10-13:30. Trainer: Salo Thornari. Trainees: Yaren Skarossa, Ulrik Cresald.
#629. G-250, Tue, 08:45-09:10. Trainer: Driya Tolvov. Trainees: Quimir Laskari, Lemir Evrell, Modra Lindune, Witor Garnari, Lumir Martista.
#632. H-201, Wed, 14:10-15:10. Trainer: Masso Vardow. Trainees: Kaya Ulmune.
#633. B-375, Tue, 14:45-15:30. Trainer: Ulrik Cresald. Trainees: Tevin Jorvow, Nesso Wrenell, Witor Garnari, Xalia Oskari, Lumir Martista.
#640. N-266, Tue/Wed, 14:00-14:45. Trainer: Modra Lindune. Trainees: Yaren Skarossa, Tevin Jorvow, Sidan Nervard.
#641. B-375, Wed, 12:20-13:15. Trainer: Witor Garnari. Trainees: Jovek Pellen, Rulia Dunnista, Ellia Munden, Driya Tolvov, Quimir Laskari, Ilya Zanneth.
#644. G-250, Tue, 10:50-11:20. Trainer: Allia Yeldossa. Trainees: Lumir Martista.
#647. T-138, Wed, 13:40-14:20. Trainer: Ellia Munden. Trainees: Driya Tolvov, Lumir Martista, Jovek Pellen.
#649. G-250, Tue, 10:15-10:35. Trainer: Sidan Nervard. Trainees: Lumir Martista, Quimir Laskari, Nesso Wrenell, Witor Garnari, Salo Thornari, Ulrik Cresald.
#652. T-138, Tue, 13:40-14:55. Trainer: Ilya Zanneth. Trainees: Lemir Evrell, Kaya Ulmune, Frelia Perrari.
#659. G-250, Wed, 12:15-12:55. Trainer: Masso Vardow. Trainees: Gator Rostari, Salo Thornari.
#665. N-266, Tue, 10:15-11:15. Trainer: Modra Lindune. Trainees: Tevin Jorvow.
#671. T-138, Wed, 08:50-09:30. Trainer: Gator Rostari. Trainees: Nesso Wrenell, Tevin Jorvow, Quimir Laskari.
#675. B-375, Tue/Wed, 15:55-17:25. Trainer: Rulia Dunnista. Trainees: Ellia Munden, Gator Rostari, Kaya Ulmune.

Booking rules
1. The room must have every item the request needs; equipment of other rooms does not count, and names must match exactly.
2. Capacity: the number of trainees plus one for the trainer (who is not listed among the trainees) must not exceed the seats of the room; equal is allowed.
3. The request gives a start time and a duration; it ends at start + duration.
4. Opening hours are binding: start not earlier than the opening time of the room, end not later than its closing time, equality allowed.
5. The trainer and all trainees are busy for the whole booking, and nobody may be in two bookings that overlap on the same day, whatever the rooms. Bookings that only touch are fine for a person: the reset gap is for rooms, not for people.
6. A day field with slashes, such as Tue/Wed/Fri, marks a repeating booking: it occupies its room and its people on each listed day at the stated time.
7. After a booking, its room is blocked for the reset gap listed for its kind of room: the next booking there may start exactly when the gap is over, not earlier. Opening and closing times need no gap.
8. Full names identify people: the same first name with another family name is another person.
9. Bookings on different days never clash.
```

Question: Can the requested booking be confirmed as it stands?

- `yes`: Yes - the request breaks none of the stated rules and can be confirmed as written.
- `no`: No - the request breaks at least one of the stated rules and cannot be confirmed as written.

what the request breaks (`meta.evidence`): `{"person": [["Xalia Oskari", "#592"]]}`

## Independence

This generator was written from scratch for the benchmark. It shares no template, no sentence, no name list and no item
layout with the generators the authors use for training data, and none of its sentences is taken from benchmark v0 or from
a published data set. Evaluation only.
