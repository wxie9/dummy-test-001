# perm_inherit

Generated access exports: is the request allowed? (layer B, generated, programmatic truth). EVALUATION ONLY.

- Decision: whether one user may perform one action on one node (folder, namespace, section, zone, collection) of an invented
  access system, under conventions that are written into every state.
- Source: generator `build/gen_perm_inherit.py` (Python 3.9, standard library, `random.Random` generators derived from seed 20261007; two runs give
  identical files). `BENCH_OUT=<dir>` writes elsewhere; `BENCH_SEED=<int>` (only with `BENCH_OUT`) builds a sealed split of the same design.
- Rows: 600 = 300 contrast pairs (`group`), 200 per level, 100 yes and 100 no per level. Metric: accuracy (chance 0.5).
  The option order is drawn per item (`meta.order`; half of the yes rows and half of the no rows of each level list `yes` first).

## What is generated

The state is an access export of an invented system in one of five domains (document workspace, code hosting service, records
system, building access system, data catalogue): the rules in plain words, the actions, the listed inclusions between actions, the
roles (own actions; from level 2 a role may extend one other role), the users, the groups (members are users and, from level 2,
other groups), the node tree (three layouts: "X lies in Y", "X (parent: Y)", full paths), the sealed nodes (levels 2-3), the
assignments (a role given to a user or a group AT a node), the deny entries (level 3, some items of level 2) and one request
(user, action, node). Two record layouts (sentences or `field: value | ...` records), two section orders, three phrasings of every
rule, title and request sentence. Names come from syllable generators (users `x.surname`, groups `first-second`, roles one word,
nodes domain words with suffixes); look-alike pairs (same surname / same first part / same stem / same base) are planted.

## Conventions written in every state

1. Membership: an assignment to a group counts for all its members; from level 2 membership passes upward through nested groups
   (a member of X is a member of every group that lists X), never downward.
2. Scope: an assignment covers its node and everything below it, nothing beside or above it.
3. Seals (levels 2-3): an assignment made above a sealed node covers neither that node nor anything below it; an assignment made at the
   sealed node or below it is not affected; seals elsewhere have no effect.
4. Roles: a role allows its own actions plus everything of the role it extends, along the chain, one way only.
5. Inclusions: only the listed inclusions exist; they chain and never run backwards.
6. Deny entries: a deny (user or group, action, node) applies when the requester is that user or a (nested) member of that group, the
   requested action is exactly that action and the requested node is that node or below it - seals do not stop it; it beats every
   assignment; it blocks no other action, also not one linked by an inclusion.
7. Decision: allowed when some assignment that counts for the requester covers the node with a role that allows the action, and no
   deny entry applies.

## Pairs and planted differences

The positive has exactly ONE allowing path (one assignment, one membership chain, one role of the chain that carries the action) and
no deny entry that applies. The negative is the same specification with one line changed; on the designated path exactly one link
fails and no other path allows the request (`meta.deviation`, `meta.edit`, `meta.path`):
`membership` (a member line points to a look-alike, or the request names a look-alike user who sits in a look-alike group or only in
an outer group), `sealed` (a seal moved onto the way between assignment and node, or the request names a node inside a sealed branch),
`role_chain` (an extension line points to a look-alike role, or the request asks for an action that only a look-alike or an extending
role carries), `action` (an inclusion line or a role's own action changed, or the request asks for a stronger or unlinked action),
`scope` (the assignment moved to a sibling, a child off the way or below the node, or the request names a look-alike node elsewhere
or a node above the assignment), `deny` (a deny line changed in its user/group, action or node so that it applies, or the request
changes its action, node or user into one that an existing deny entry covers while the assignment still allows it).
Request-line differences: 150 pairs (50 per level), structure-line differences: 150 pairs (50 per level).

| deviation | level 1 | level 2 | level 3 |
|---|---|---|---|
| `membership` | 34 | 17 | 16 |
| `sealed` | 0 | 17 | 16 |
| `role_chain` | 0 | 17 | 17 |
| `action` | 33 | 17 | 17 |
| `scope` | 33 | 16 | 17 |
| `deny` | 0 | 16 | 17 |

Decoys in both classes (shared by the two members of a pair): near-miss assignments for the requester that each fail one link
(look-alike group or user, group nested INSIDE the requester's group, sibling node, node below the request, an assignment above a seal
that lies on the way, a role that lacks the action, a role that is only extended by the carrier), seals on the way at or above the
assignment and off the way, deny entries on another (often linked) action, on a sibling node, below the requested node or for a
look-alike or inner group. The words "deny" and "sealed" occur equally often in the two classes (deny: 931 / 931,
sealed: 1191 / 1191 occurrences in yes / no states).

## Levels

| level | groups / nesting | role extension | tree depth | sealed | deny entries | users |
|---|---|---|---|---|---|---|
| 1 | one layer, also direct assignments | none | 2 (flat) | 0 | 0 | 4-6 |
| 2 | nested, 1 layer | chains of one | 3 | 1 | 0-2 (some items) | 6-9 |
| 3 | nested, 2 layers | chains of two | 4 | 2 | 2-3 | 10-14 |

Level 3 is hard because the allowing path combines at least six facts from different sections (`meta.path_facts` >= 6: two or three
membership lines, the assignment line, one to three role lines, inclusion lines, one to three tree lines), and the reader must also
check two seals against the way from the assignment down to the node and two or three deny entries against the requester's nested
groups, the exact action and the node's ancestors. State length (characters) min / median / max: level 1 2061 / 2329 / 3084,
level 2 3247 / 3926 / 5449, level 3 4522 / 5167 / 6305.

## Checks made by the script

- Every pair: the positive is allowed through exactly one assignment (one membership chain, one carrier role, no applicable deny);
  in the negative exactly the planted link of the designated path fails (`links`), no other assignment allows it (for `deny`: the
  assignment still allows it and exactly one deny entry applies); undoing the edit gives the positive.
- `truth` and an independently written second evaluator (`judge`, used with all switches at the written rules) agree on all items.
- The two states of a pair have the same number of lines, differ in exactly one line and contain the same set of words.
- Balance: 100 yes / 100 no per level; kinds as in the table; 50 request and 50 structure differences per level; gold position;
  no duplicate state; vocabulary test (520 words, worst ratio 1.00); negative longer / equal / shorter than its positive:
  72 / 157 / 71 pairs.

Accuracy of sloppy readings (the rules with one convention misread), level 1 / 2 / 3:

| reading | level 1 | level 2 | level 3 |
|---|---|---|---|
| membership through nesting ignored | 1.000 | 0.815 | 0.500 |
| nesting read in both directions | 1.000 | 0.845 | 0.745 |
| assignments cover every node | 0.615 | 0.630 | 0.630 |
| assignments also cover upward | 0.900 | 0.930 | 0.940 |
| seals ignored | 1.000 | 0.850 | 0.845 |
| any seal on the way refuses | 1.000 | 0.825 | 0.750 |
| role extension ignored | 1.000 | 0.800 | 0.645 |
| extension read in both directions | 1.000 | 0.825 | 0.800 |
| inclusions ignored | 0.715 | 0.645 | 0.635 |
| inclusions read in both directions | 0.835 | 0.805 | 0.820 |
| deny entries ignored | 1.000 | 0.920 | 0.915 |
| deny entries only for direct members | 1.000 | 0.990 | 0.950 |
| a deny blocks every action | 1.000 | 0.890 | 0.705 |
| a deny also blocks linked actions | 1.000 | 0.905 | 0.780 |
| seals also stop deny entries | 1.000 | 0.975 | 0.980 |

## Examples

id `perm_inherit:00001` (group `perm_inherit:g0044`, level 1, domain building, gold **no**, deviation `scope`, variant request, planted edit `["request", "node", "serverhall"]`)

```
Permission data of a fictional building access system, followed by the rules that govern it.

Access rules (they apply exactly as written):
- Each assignment names a role and either a user or a group. If it names a group, exactly the users listed as members of that group hold the role.
- The role of an assignment is valid on the zone named in the assignment and on all zones below that zone at any depth, not on any other zone.
- Holding a role permits the actions on that role's list.
- Actions can include other actions, exactly as listed. Being allowed an action means being allowed every action it includes, directly or through a chain of listed inclusions. An inclusion is never read backwards, and actions without a listed link do not include each other.
- A request is allowed only when an assignment whose role the requester holds covers the requested zone and that role allows the requested action.

Actions of this system: enter, service, unlock, rekey

Listed inclusions (only these exist):
- rekey includes enter
- rekey includes unlock
- service includes enter

Roles and what they allow:
- role graspex: allows unlock
- role pontum: allows enter, service
- role teldor: allows enter, rekey
- role trimbal: allows service, unlock

Users: t.zondish, d.teftack, f.pivrov, c.jindilt, a.niftath

Groups:
- group guard-beta: members user a.niftath, user c.jindilt, user f.pivrov, user d.teftack
- group guard-late: members user c.jindilt, user t.zondish, user d.teftack
- group duty-two: members user a.niftath, user t.zondish, user d.teftack, user c.jindilt

Zone tree (each line: a zone and its parent):
- whole-site (top zone, no parent)
- workshop (parent: pantry)
- cleanroom (parent: whole-site)
- serverhall (parent: whole-site)
- yard (parent: whole-site)
- dock (parent: whole-site)
- hangar (parent: serverhall)
- vault (parent: serverhall)
- pantry (parent: whole-site)
- atrium (parent: pantry)

Role assignments:
- role trimbal given to user f.pivrov at zone vault
- role trimbal given to group guard-beta at zone hangar
- role graspex given to user f.pivrov at zone workshop
- role pontum given to user f.pivrov at zone serverhall
- role graspex given to group guard-late at zone serverhall

The request: may user f.pivrov unlock in the zone serverhall?
```

question: Is the request allowed?

- `yes`: The request is allowed.
- `no`: The request is not allowed.

id `perm_inherit:00004` (group `perm_inherit:g0102`, level 2, domain workspace, gold **yes**, deviation `None`, variant structure, planted edit `["role_action", "hoftis", "view", "comment"]`)

```
Access export of an invented document workspace. The rules in this export decide every request.

The request: may user n.lazdack view in the folder legal-new?

Access rules (they apply exactly as written):
1. An assignment gives one role to one user or to one group. An assignment to a group counts for every member of the group. Membership passes through nested groups: when group X is listed as a member of group Y, all members of X (also those X has through its own nested groups) are members of Y. It does not pass the other way: a user listed directly in Y is not thereby a member of X.
2. Assignments reach downward only: the folder where an assignment is made and everything below it, however deep, are covered; folders beside it or above it are not.
3. Exception for sealed folders: an assignment never passes into a sealed folder from a folder above it, so the sealed folder and everything below it stay out of its reach. A seal does nothing to an assignment made at the sealed folder or below it, and nothing to folders that are not inside the sealed folder.
4. Holding a role permits the actions on its own list and, when the role extends a second role, every action the second role permits (its own list and whatever it takes over by extension). The second role takes over nothing from the first.
5. The inclusion list says which action includes which. If X includes Y, a role that allows X allows Y as well; inclusions chain, so if Y in turn includes Z, then X includes Z. Only the listed inclusions exist, and none works in reverse.
6. A request is allowed only when an assignment whose role the requester holds covers the requested folder and that role allows the requested action.

Folders as full paths from the top folder (parts separated by /):
- all-files
- all-files/contracts
- all-files/research
- all-files/research/minutes-south
- all-files/contracts/briefs-a/legal-old
- all-files/contracts/briefs-a/audits
- all-files/forecasts/minutes-north
- all-files/forecasts/minutes-north/budgets-2026
- all-files/forecasts
- all-files/forecasts/briefs-b
- all-files/research/minutes-south/legal-new
- all-files/research/templates
- all-files/contracts/briefs-a
- all-files/contracts/tenders

Seals:
sealed folder: forecasts

Users: a.zerkurn | w.trulmuph | b.trerziz | n.dirvath | t.zoftard | k.kovrurd | j.guskugh | n.lazdack | n.vandath

Groups:
group: admin-alpha | members: user t.zoftard, user k.kovrurd, user n.dirvath
group: audit-west | members: user a.zerkurn, user n.lazdack, user w.trulmuph, user b.trerziz, user t.zoftard
group: duty-two | members: user k.kovrurd, user n.lazdack
group: admin-amber | members: group duty-two, user n.dirvath
group: visitor-blue | members: user j.guskugh, user a.zerkurn, user n.vandath, user t.zoftard, user b.trerziz, group admin-alpha

Actions: view | comment | export | edit | share

Inclusion list:
inclusion: edit includes view
inclusion: export includes comment

Roles and what they allow:
role: hirzis | allows: view | extends: none
role: stindid | allows: export | extends: none
role: hoftis | allows: view | extends: stindid
role: softan | allows: view | extends: none

Assignments:
assignment: role softan | holder: group admin-alpha | folder: audits
assignment: role softan | holder: group admin-alpha | folder: legal-new
assignment: role hirzis | holder: user n.lazdack | folder: budgets-2026
assignment: role hirzis | holder: group admin-amber | folder: minutes-north
assignment: role hoftis | holder: group admin-amber | folder: minutes-south
assignment: role stindid | holder: user n.lazdack | folder: minutes-north
```

question: Is the request allowed?

- `yes`: The request is allowed.
- `no`: The request is not allowed.

id `perm_inherit:00006` (group `perm_inherit:g0282`, level 3, domain catalog, gold **no**, deviation `membership`, variant request, planted edit `["request", "user", "e.trumbuz"]`)

```
What follows are the access rules and the current permission records of an invented data catalogue.

Rules:
1. An assignment gives one role to one user or to one group. An assignment to a group counts for every member of the group. Membership passes through nested groups: when group X is listed as a member of group Y, all members of X (also those X has through its own nested groups) are members of Y. It does not pass the other way: a user listed directly in Y is not thereby a member of X.
2. The role of an assignment is valid on the collection named in the assignment and on all collections below that collection at any depth, not on any other collection.
3. Sealing cuts off what comes from above. If the requested collection is a sealed collection or lies below one, an assignment made above that sealed collection does not cover it. Assignments made at the sealed collection or below it work as usual, and a sealed collection elsewhere in the tree has no effect.
4. The actions a role allows are its own actions plus the actions of the role it extends, plus those of the role that one extends, and so on. Nothing is passed in the opposite direction, from the extending role to the extended one.
5. The inclusion list says which action includes which. If X includes Y, a role that allows X allows Y as well; inclusions chain, so if Y in turn includes Z, then X includes Z. Only the listed inclusions exist, and none works in reverse.
6. Deny entries win over assignments. An entry blocks its action for the user it names, or for every member of the group it names (members through nested groups included), on its collection and on everything below that collection, sealed or not. It blocks that single action only; requests for other actions are judged as if the entry were not there, also when the actions are linked by an inclusion.
7. A request is allowed only when an assignment whose role the requester holds covers the requested collection and that role allows the requested action; in addition no deny entry may apply.

Actions of this system: query | sample | export | load | alter | drop

Listed inclusions (only these exist):
inclusion: drop includes load
inclusion: alter includes query
inclusion: drop includes sample

Roles:
role: berkan | allows: sample, drop | extends: none
role: drulvan | allows: query | extends: none
role: fildum | allows: drop | extends: berkan
role: bivran | allows: sample | extends: none
role: ponten | allows: drop | extends: drirkum
role: drirkum | allows: alter, drop | extends: berkan
role: stiskor | allows: sample, export | extends: none

People with an account: m.gulkirn | d.jivruth | p.galkock | h.dizdorn | h.kernuck | r.stirzesh | e.torkaph | e.trumbuz | p.galverd | s.tifterd | n.tulvuph | j.trumbuz

Groups and their members:
group: crew-west | members: user j.trumbuz
group: core-green | members: user e.trumbuz, user r.stirzesh, group review-one, group field-late
group: review-one | members: user n.tulvuph, user h.dizdorn, user h.kernuck, user s.tifterd, user e.torkaph
group: field-late | members: user m.gulkirn, user d.jivruth, group crew-west, user n.tulvuph
group: duty-green | members: user j.trumbuz, user p.galverd, user e.trumbuz, user h.kernuck
group: shift-east | members: user h.kernuck, user r.stirzesh, user e.trumbuz
group: guard-day | members: user p.galkock, user e.trumbuz, user s.tifterd, user e.torkaph

Collections as full paths from the top collection (parts separated by /):
- catalog-root
- catalog-root/crm_hrs/geo/churn_raw
- catalog-root/crm_hrs
- catalog-root/crm_day/devices_us/weather/sessions
- catalog-root/tickets/payments/sensors/clicks
- catalog-root/crm_hrs/geo/churn_raw/visits
- catalog-root/crm_day/devices_us/forecasts
- catalog-root/tickets/payments/sensors
- catalog-root/tickets/payments/surveys
- catalog-root/crm_hrs/staffing_2026
- catalog-root/crm_day/returns/refunds
- catalog-root/crm_day/devices_us/weather
- catalog-root/crm_day
- catalog-root/crm_day/returns
- catalog-root/crm_hrs/geo/pricing_raw
- catalog-root/tickets
- catalog-root/tickets/devices_eu
- catalog-root/crm_hrs/geo
- catalog-root/crm_hrs/geo/pricing_raw/telemetry
- catalog-root/crm_day/returns/fraud_eu
- catalog-root/tickets/payments
- catalog-root/crm_hrs/geo/pricing_raw/tariffs
- catalog-root/crm_day/devices_us

Collections marked as sealed:
sealed collection: crm_day
sealed collection: churn_raw

Assignments:
assignment: role ponten | holder: group core-green | collection: catalog-root
assignment: role ponten | holder: group field-late | collection: crm_day
assignment: role drulvan | holder: group review-one | collection: geo
assignment: role ponten | holder: user e.trumbuz | collection: catalog-root
assignment: role drirkum | holder: group guard-day | collection: crm_hrs
assignment: role drulvan | holder: group review-one | collection: crm_day
assignment: role ponten | holder: group core-green | collection: crm_hrs
assignment: role drulvan | holder: user j.trumbuz | collection: crm_hrs

Deny entries:
deny: action query | for: user e.trumbuz | collection: staffing_2026
deny: action alter | for: user e.trumbuz | collection: catalog-root

Request: user e.trumbuz asks to query at the collection refunds.
```

question: Is the request allowed?

- `yes`: The request is allowed.
- `no`: The request is not allowed.

## Independence

The generator is new, written for this benchmark; its wording, names and templates share nothing with the authors' training
generators or with benchmark v0.
