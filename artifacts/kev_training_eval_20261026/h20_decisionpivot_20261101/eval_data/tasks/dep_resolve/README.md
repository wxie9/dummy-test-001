# dep_resolve

Generated package indexes: does the proposed set of pinned versions install cleanly in the target environment?
(layer E, generated, programmatic truth)

- Question (same for every item): "Does the proposed set install cleanly in the target environment?" Options `yes` / `no` (order drawn per item, balanced inside every level and class).
- Source: generator `build/gen_dep_resolve.py` (Python 3.9, standard library only, root seed 20261007; identical output on every run).
  `BENCH_OUT=<dir>` writes elsewhere; `BENCH_SEED=<k>` (only with `BENCH_OUT`) gives a sealed split of the same design.
- Rows: 600 = 300 contrast pairs, 200 per level, 300 yes / 300 no; metric accuracy, chance 0.5.

## What is generated

A state of four parts: the conventions in plain words; the target environment (from level 2 with its runtime version);
the index of an invented package registry - every listed version of every package with its requirements (a package name and
one or more bounds `>=V`, `>V`, `<=V`, `<V`, `==V`, `!=V`), from level 2 its runtime bounds, at level 3 its conflict entries;
and the proposed pins (one package at one version per line). Three layouts (an indented block, a pipe table, one fact per
line), five domains (pipeline plugins, firmware modules, analysis packages, game-server extensions, robot components), three
phrasings for every convention sentence and every label, versions listed oldest first, newest first or mixed. Package names are
built from invented syllables; some pairs of names share a stem (look-alikes).

## Conventions written into every state

1. Versions compare number by number as whole numbers (1.10.0 is newer than 1.9.3); runtime versions have two numbers and
   compare the same way (from level 2).
2. The meaning of every operator; several bounds after one name must all hold.
3. The set installs cleanly when every pinned version is listed, every requirement of every pinned version names a package that
   is pinned at a version inside all its bounds, (level 2+) the environment's runtime meets every runtime bound of every pinned
   version, and (level 3) no conflict entry of a pinned version applies to another pin.
4. Only the entries of pinned versions count. 5. Nothing is installed besides the pins (a requirement on an unpinned package
   fails). 6. Pins that nothing requires do no harm, but their own entries are checked. 7. (level 2+) `any` = no runtime bound.
8. (level 3) a conflict applies when the named package is pinned at a version meeting its bound, whichever side lists it.

## Levels

| level | pins | unpinned packages in the index | versions per package | runtime | conflicts | requirement chain from the first pin |
|---|---|---|---|---|---|---|
| 1 | 4-5 | 2 | 1-2 | - | - | 1-2 links |
| 2 | 6-8 | 2-3 | 2-3 | yes | - | 2 links |
| 3 | 9-12 | 3 | 3-4 | yes | yes | 3 links |

State length (characters, min / median / max): level 1 1482 / 1750 / 2059, level 2 2658 / 3348 / 5161, level 3 4815 / 7159 / 10286.

**What makes level 3 hard.** To answer yes the reader must, for each of 9-12 pins, (1) find the entry of the pinned version
among 3-4 look-alike entries of that package (the other entries differ in their bounds, and 45% of their requirements on
pinned packages would fail with the given pins), (2) look up the pin of every package it requires (1-3 per entry) and
compare versions number by number (several packages have 1.9 / 1.10 neighbours), (3) compare its runtime bounds with the
environment's runtime and (4) check its conflict entries against the pins: 20 to 50, median 34 checks per positive. A negative fails on one link that combines at least
three facts from different places: the pin of the dependant, the entry of that pinned version in the index and the pin (or the
missing pin) of the required package - for `own_req`, `runtime` and `conflict` also the entry of the moved version. In 74 of the
100 level-3 pairs the moved or missing package is the second or third link of the chain of three requirements. Decoys in both classes: failing bounds and
runtime bounds under versions that are not pinned, conflicts under unpinned versions or about unpinned packages, pins that
nothing requires, pins exactly on an included bound or just inside an excluded one.

## Planted problems (negatives; the positive of the pair differs in that one pin line)

| `meta.deviation` | level 1 | level 2 | level 3 |
|---|---|---|---|
| `bound` | 34 | 25 | 20 |
| `missing` | 33 | 25 | 20 |
| `own_req` | 33 | 25 | 20 |
| `runtime` | - | 25 | 20 |
| `conflict` | - | - | 20 |

- `bound`: one pin moved to the neighbouring listed version, just outside the bound of ONE dependant; all other dependants accept
  it and its own entry is met. Bound forms (the positive sits ON an included bound or just inside an excluded one; the negative one
  listed step beyond):

| form | level 1 | level 2 | level 3 |
|---|---|---|---|
| included | 10 (5 with 1.9 / 1.10) | 8 (4 with 1.9 / 1.10) | 6 (3 with 1.9 / 1.10) |
| excluded | 11 (5 with 1.9 / 1.10) | 9 (5 with 1.9 / 1.10) | 8 (4 with 1.9 / 1.10) |
| unlisted | 4 (3 with 1.9 / 1.10) | 2 (1 with 1.9 / 1.10) | 1 (1 with 1.9 / 1.10) |
| eq | 5 (0 with 1.9 / 1.10) | 3 (0 with 1.9 / 1.10) | 3 (0 with 1.9 / 1.10) |
| ne | 4 (0 with 1.9 / 1.10) | 3 (0 with 1.9 / 1.10) | 2 (0 with 1.9 / 1.10) |

- `own_req`: one pin moved to a neighbouring listed version that every dependant accepts, but one bound of its own entry misses the
  pin of another package by one step.
- `missing`: the pin line of a package that exactly one pinned version requires is replaced by a pin of a package that nothing
  requires (same number of lines, same line width; half of these pairs use look-alike names with a common stem).
- `runtime` (levels 2-3): one pin moved to a neighbouring version whose runtime bound the environment misses by one step (a third
  of these pairs use a runtime of x.9 or x.10 against x.10 / x.9: level 2: 9 / level 3: 7 pairs).
- `conflict` (level 3): one pin moved to a neighbouring version so that one conflict applies: declared by another pin about the
  moved package (10 pairs) or declared by the moved version about another pin (10 pairs).

## Shortcut readers (computed on the specification; accuracy per level, then wrong answers on yes / no items)

| reader | level 1 | level 2 | level 3 | wrong yes / no |
|---|---|---|---|---|
| text_compare | 0.925 | 0.820 | 0.835 | 72 / 12 |
| strict_as_inclusive | 0.840 | 0.915 | 0.545 | 88 / 52 |
| ignore_missing | 0.835 | 0.875 | 0.900 | 0 / 78 |
| ignore_runtime | 1.000 | 0.875 | 0.900 | 0 / 45 |
| ignore_conflicts | 1.000 | 1.000 | 0.900 | 0 / 20 |
| newest_entry | 0.630 | 0.510 | 0.500 | 261 / 11 |

`text_compare` compares versions as text (1.10.0 before 1.9.3); `strict_as_inclusive` reads > and < as >= and <=;
`newest_entry` reads the entry of the newest listed version instead of the pinned one; the other three skip one convention.

## Checks made by the script

- The truth is computed on the structured specification (`truth(spec)`: no entry in `violations(spec)`); the text is rendered
  from the same specification.
- Every positive has no violation; every negative has exactly one violation and it is the planted one (kind, package and side
  asserted); the two members have the same index, the same number of pins and of lines, and their states differ in exactly one
  line (length difference at most 2 characters: {'equal': 269, 'positive longer': 17, 'negative longer': 14}).
- Every bound helper asserts that a passing requirement is met by the versions it must accept and a failing one misses by
  exactly one bound; look-alike entries of a package never coincide with another entry of it.
- Classes 100 / 100 in every level; deviation kinds as equal as the numbers allow in every level; `yes` listed first in exactly
  half of the yes items and half of the no items of every level; no duplicate state; no word of frequency >= 20 occurs in one
  class at more than twice the rate of the other (worst ratio 1.00).
- Retries of unlucky draws (a fresh sub-seed per attempt): 332 in total.

## Examples (one per level)

### level 1

id `dep_resolve:00006` (group `dep_resolve:g0006`, level 1, gold **no**, deviation `bound`, layout facts)

```
A game server called skellok-42 is to receive extensions from the extension catalogue.

Conventions:
* Versions are compared number by number from the left, each number as a whole number: 1.10.0 is newer than 1.9.3, and 2.0.0 is newer than 1.12.7.
* Bounds read as follows: >= at least, > strictly newer, <= at most, < strictly older, == exactly this version, != anything but this version; where several bounds follow one name, all of them apply.
* The set is clean only if the extension catalogue lists every pinned version and every requirement of a pinned version is met by the pin of the required extension.
* Requirements and other entries of versions without a pin do not matter.
* Only pinned extensions get installed; a required extension that has no pin counts as unmet.
* Pinning an extension that nothing needs is allowed, but the entry of that pinned version must still be met.

Target environment: skellok-42.

Extension catalogue (one entry per listed version):
Each line holds a single fact about a version.
kovdru-save 1.7.0 needs krildex-loot >=7.13.0,<8.0.0
kovdru-save 1.7.0 needs daxux-voice <=10.0.3
kovdru-save 1.7.1 needs krildex-loot >7.13.1
kovdru-save 1.7.1 needs daxux-voice >9.6.0,<=10.0.3
kovdru-save 1.7.1 needs wezeth-shop <=0.14.0,!=0.13.1
wezeth-shop 0.13.1 needs daxux-voice >=10.0.0
wezeth-shop 0.14.0 needs daxux-voice >9.6.0
nibzel-voice 3.0.3 needs nothing
nibzel-voice 3.0.4 needs nothing
gratomi 2.0.3 needs daxux-voice >=10.0.0,<10.0.4
gratomi 2.0.3 needs nibilo-voice >4.3.0,<4.3.2
krildex-loot 7.13.1 needs nibzel-voice !=3.0.4
krildex-loot 7.13.1 needs daxux-voice >=10.0.3
nibilo-voice 4.3.1 needs kovdru-save >=1.7.0,<1.7.1
nibilo-voice 4.3.1 needs wezeth-shop >0.13.1
nibilo-voice 4.3.0 needs wezeth-shop <=0.14.0
daxux-voice 10.0.3 needs nothing
daxux-voice 9.6.0 needs gratomi >=2.0.0,<=2.0.3

The proposal pins exactly these extensions:
wezeth-shop 0.14.0
daxux-voice 10.0.3
nibzel-voice 3.0.4
krildex-loot 7.13.1
kovdru-save 1.7.0
```

question: Does the proposed set install cleanly in the target environment?

- `no`: No, the proposed set does not install cleanly.
- `yes`: Yes, the proposed set installs cleanly.

planted problem: bound: krildex-loot 7.13.1 requires nibzel-voice !=3.0.4, pinned 3.0.4

### level 2

id `dep_resolve:00009` (group `dep_resolve:g0009`, level 2, gold **yes**, deviation `None`, layout facts)

```
hultis-29 (an analysis workstation) should get the packages listed under the pins, drawn from the package index.

Conventions:
* Versions are compared number by number from the left, each number as a whole number: 1.10.0 is newer than 1.9.3, and 2.0.0 is newer than 1.12.7. Runtime versions (two parts) follow the same order, so 4.11 is later than 4.9.
* Bounds read as follows: >= at least, > strictly newer, <= at most, < strictly older, == exactly this version, != anything but this version; where several bounds follow one name, all of them apply.
* A clean install needs all of the following: each pin is a version that the package index lists; for each pinned version, each package it needs is pinned too, at a version inside the stated bounds; the runtime of the environment satisfies the runtime bounds of all pinned versions.
* Requirements and other entries of versions without a pin do not matter.
* Nothing is installed besides the pins, so a requirement on a package without a pin is not met.
* Pinning a package that nothing needs is allowed, but the entry of that pinned version must still be met.
* A runtime bound of a pinned version is met when the runtime of the target environment satisfies it; 'any' sets no runtime bound.

Environment: hultis-29 (analysis workstation); runtime version 3.13.

Entries of the package index:
Every line states one fact about one listed version.
zephlok 0.4.2 needs nothing
zephlok 0.4.2 runtime range >=3.13,<3.14
zephlok 0.6.2 needs nothing
zephlok 0.6.2 runtime range >3.12
dranrin 5.4.4 needs rukkam-core ==7.12.0
dranrin 5.4.4 runtime range ==3.14
dranrin 6.3.1 needs rukkam-core >=7.11.0,<=7.11.5
dranrin 6.3.1 runtime range >=3.12
dranrin 7.1.4 needs rukkam-core !=7.11.5
dranrin 7.1.4 runtime range <3.13
trovenk-plot 6.3.3 needs hulrin-io >=7.14.0
trovenk-plot 6.3.3 needs sorkiko-units >3.0.0
trovenk-plot 6.3.3 runtime range >3.13,<=3.15
trovenk-plot 6.4.6 needs sorkiko-units ==3.0.0
trovenk-plot 6.4.6 runtime range <4.0
sorkiko-units 2.5.1 needs quendex-fit >=3.2.0
sorkiko-units 2.5.1 runtime range >=3.12
sorkiko-units 3.0.0 needs nothing
sorkiko-units 3.0.0 runtime range <=3.12
sorkiko-units 3.0.1 needs nothing
sorkiko-units 3.0.1 runtime range >=3.12
hulrin-io 7.14.5 needs fexrin >=3.3.3,<=4.0.0
hulrin-io 7.14.5 needs dranrin <=7.1.4
hulrin-io 7.14.5 needs rukkam-core >=7.11.0,<=7.11.5
hulrin-io 7.14.5 runtime range <4.0
hulrin-io 7.15.2 needs fexrin ==4.0.0
hulrin-io 7.15.2 needs dranrin >=7.1.4
hulrin-io 7.15.2 needs rukkam-core ==7.11.5
hulrin-io 7.15.2 runtime range >=3.13
trovenk-bins 7.3.2 needs nothing
trovenk-bins 7.3.2 runtime range <3.14
trovenk-bins 8.0.0 needs nothing
trovenk-bins 8.0.0 runtime range >3.11,<=3.12
quendru 7.1.3 needs nothing
quendru 7.1.3 runtime range >3.12
quendru 8.0.0 needs trovenk-plot >=6.3.0,!=6.4.6
quendru 8.0.0 runtime range >=3.12,<4.0
quendru 8.0.1 needs jumryx-stats ==1.2.6
quendru 8.0.1 runtime range any
quendex-fit 3.1.4 needs hulrin-io >=7.15.2
quendex-fit 3.1.4 needs trovenk-bins >=7.3.0,<=7.3.2
quendex-fit 3.1.4 runtime range >=3.13,<=3.14
quendex-fit 3.2.0 needs hulrin-io >=7.14.5,<=7.15.2
quendex-fit 3.2.0 needs trovenk-bins >=7.3.2
quendex-fit 3.2.0 needs fexrin >3.3.0,<4.0.1
quendex-fit 3.2.0 runtime range ==3.13
quendex-fit 3.3.5 needs trovenk-bins >=7.3.0,!=8.0.0
quendex-fit 3.3.5 needs fexrin <4.0.0
quendex-fit 3.3.5 needs dranrin >6.3.1,<7.2.0
quendex-fit 3.3.5 runtime range >=3.13
fexrin 3.3.0 needs trovenk-bins >=7.3.2
fexrin 3.3.0 runtime range >=3.12,<3.14
fexrin 3.3.3 needs trovenk-bins >=8.0.0
fexrin 3.3.3 runtime range >3.12
fexrin 4.0.0 needs trovenk-bins >=7.3.0
fexrin 4.0.0 runtime range <3.14
jumryx-stats 1.0.1 needs nothing
jumryx-stats 1.0.1 runtime range <4.0
jumryx-stats 1.2.6 needs nothing
jumryx-stats 1.2.6 runtime range >3.12,<4.0
rukkam-core 7.11.5 needs nothing
rukkam-core 7.11.5 runtime range <4.0
rukkam-core 7.12.0 needs nothing
rukkam-core 7.12.0 runtime range ==3.12

Proposed pins:
rukkam-core at 7.11.5
fexrin at 4.0.0
quendex-fit at 3.2.0
hulrin-io at 7.14.5
quendru at 7.1.3
jumryx-stats at 1.0.1
dranrin at 6.3.1
trovenk-bins at 7.3.2
```

question: Does the proposed set install cleanly in the target environment?

- `yes`: Yes, the proposed set installs cleanly.
- `no`: No, the proposed set does not install cleanly.

### level 3

id `dep_resolve:00003` (group `dep_resolve:g0003`, level 3, gold **no**, deviation `missing`, layout facts)

```
vobtem-37 (an analysis workstation) should get the packages listed under the pins, drawn from the package index.

Conventions:
* Versions are ordered part by part as integers, not as text: 3.10.0 is later than 3.9.9, and 2.0.0 is later than 1.15.2. Runtime versions have two numbers and are compared the same way (3.10 is newer than 3.9).
* Each bound is an operator and a version: >= (that version or newer), > (newer only), <= (that version or older), < (older only), == (only that version), != (every version but that one); a list of bounds is met only when each bound is met.
* A clean install needs all of the following: each pin is a version that the package index lists; for each pinned version, each package it needs is pinned too, at a version inside the stated bounds; the runtime of the environment satisfies the runtime bounds of all pinned versions; no pinned version has a 'conflicts with' entry that applies to another pin.
* Requirements and other entries of versions without a pin do not matter.
* Nothing is installed besides the pins, so a requirement on a package without a pin is not met.
* Extra pins are fine: a pinned package that nothing requires is harmless as long as its own entry is satisfied.
* The environment's runtime must satisfy each runtime bound of each pinned version ('any' means no bound).
* Conflicts ('conflicts with'): a pinned version that names a package P with a bound blocks the set exactly when P is pinned at a version meeting that bound; if P has no pin, or its pin misses the bound, nothing happens.

Install target: vobtem-37, running runtime 4.12.

Package index (one entry per listed version):
One fact per line; a version without a 'conflicts with' line has no such entry.
umbvek-grid 6.3.2 needs vobryx-units <=2.1.1
umbvek-grid 6.3.2 supported runtime >=4.11,<5.0
umbvek-grid 5.6.0 needs vobryx-units ==2.2.4
umbvek-grid 5.6.0 supported runtime ==4.12
umbvek-grid 4.2.2 needs vobryx-units >=2.2.0
umbvek-grid 4.2.2 supported runtime <4.13
umbvek-grid 3.0.4 needs nothing
umbvek-grid 3.0.4 supported runtime ==4.11
umbvek-grid 3.0.4 conflicts with sevomi-table >5.2.1
miptem-fit 0.0.11 needs peskosk-units >=2.14.0,!=2.14.2
miptem-fit 0.0.11 needs ulvgan ==3.3.1
miptem-fit 0.0.11 needs yegmur-io >=2.9.9
miptem-fit 0.0.11 supported runtime >=4.13
miptem-fit 0.0.10 needs peskosk-units >=2.14.0,<=2.14.2
miptem-fit 0.0.10 needs ulvgan <3.2.6,!=3.1.3
miptem-fit 0.0.10 needs yegmur-io >2.9.9,!=2.9.11
miptem-fit 0.0.10 supported runtime >4.11
miptem-fit 0.0.9 needs peskosk-units >=2.13.3,!=2.14.2
miptem-fit 0.0.9 needs ulvgan >=3.2.5,<3.3.1
miptem-fit 0.0.9 supported runtime >4.11,<4.13
miptem-fit 0.0.9 conflicts with vobryx-units >2.1.1
ulvgan 3.3.1 needs fexmur-units >=2.2.4,<3.0.0
ulvgan 3.3.1 supported runtime ==4.13
ulvgan 3.2.5 needs nothing
ulvgan 3.2.5 supported runtime ==4.12
ulvgan 3.1.3 needs nothing
ulvgan 3.1.3 supported runtime >=4.12
ulvgan 3.0.3 needs nothing
ulvgan 3.0.3 supported runtime >=4.12,<5.0
umbdru-core 3.5.3 needs nothing
umbdru-core 3.5.3 supported runtime >=4.10
umbdru-core 3.5.3 conflicts with vobryx-units >=2.2.4
umbdru-core 3.4.1 needs nothing
umbdru-core 3.4.1 supported runtime >4.11
umbdru-core 3.2.4 needs nothing
umbdru-core 3.2.4 supported runtime >4.12,<5.0
umbdru-core 3.0.1 needs yegmur-io >2.9.9,<=2.9.10
umbdru-core 3.0.1 supported runtime >4.11
umbdru-core 3.0.1 conflicts with miptem-fit >0.0.9
pluilo-solve 5.3.3 needs vobryx-io >=6.4.0,<6.4.5
pluilo-solve 5.3.3 needs umbvek-grid >5.6.0
pluilo-solve 5.3.3 supported runtime >=4.12
pluilo-solve 5.3.3 conflicts with pluilo-units <4.6.0
pluilo-solve 5.2.3 needs nothing
pluilo-solve 5.2.3 supported runtime >=4.12,<4.13
pluilo-solve 5.2.3 conflicts with fexmur-units <=4.0.3
pluilo-solve 5.1.1 needs umbvek-units >=4.7.1
pluilo-solve 5.1.1 needs yegmur-io ==2.9.10
pluilo-solve 5.1.1 supported runtime >=4.12
pluilo-solve 5.1.1 conflicts with miptem-fit >=0.0.11
vobryx-units 2.3.0 needs fexmur-units <4.0.4
vobryx-units 2.3.0 supported runtime ==4.11
vobryx-units 2.2.4 needs nothing
vobryx-units 2.2.4 supported runtime >=4.11
vobryx-units 2.2.4 conflicts with pluilo-units >4.5.6
vobryx-units 2.1.1 needs pluilo-solve >=5.2.0
vobryx-units 2.1.1 supported runtime !=4.12
fexmur-units 4.0.3 needs ulvgan >=3.2.5,!=3.3.1
fexmur-units 4.0.3 needs pluilo-solve >5.2.3
fexmur-units 4.0.3 supported runtime >=4.10
fexmur-units 3.1.0 needs umbvek-grid >4.2.2,<6.3.2
fexmur-units 3.1.0 supported runtime <4.12
fexmur-units 3.1.0 conflicts with vobryx-units <=2.2.4
fexmur-units 2.2.4 needs hulnor-stats >=8.3.0
fexmur-units 2.2.4 needs umbvek-grid ==5.6.0
fexmur-units 2.2.4 supported runtime ==4.13
hulnor-stats 9.0.3 needs miptem-fit <0.0.10
hulnor-stats 9.0.3 supported runtime ==4.13
hulnor-stats 9.0.3 conflicts with sevomi-table <=6.6.3
hulnor-stats 8.3.4 needs miptem-fit <0.0.11,!=0.0.9
hulnor-stats 8.3.4 supported runtime >=4.12
hulnor-stats 8.3.4 conflicts with umbvek-units >=4.8.1
hulnor-stats 7.5.0 needs nothing
hulnor-stats 7.5.0 supported runtime >=4.11
hulnor-stats 7.5.0 conflicts with vobryx-io >6.2.2
yegmur-io 2.9.11 needs umbvek-grid >5.6.0,<=6.3.2
yegmur-io 2.9.11 supported runtime <4.12
yegmur-io 2.9.10 needs umbvek-grid >=5.0.0,<6.3.2
yegmur-io 2.9.10 supported runtime >=4.12
yegmur-io 2.9.9 needs umbvek-grid >=6.3.2,<6.4.0
yegmur-io 2.9.9 supported runtime >=4.12
pluilo-units 5.0.0 needs ulvgan >=3.1.0,<=3.1.3
pluilo-units 5.0.0 supported runtime >=4.13
pluilo-units 4.6.2 needs ulvgan >3.2.5,<=3.3.1
pluilo-units 4.6.2 supported runtime >=4.10
pluilo-units 4.6.0 needs ulvgan >=3.2.0,!=3.2.5
pluilo-units 4.6.0 needs sevomi-table >5.2.1
pluilo-units 4.6.0 supported runtime >=4.11
pluilo-units 4.5.6 needs ulvgan >=3.2.5
pluilo-units 4.5.6 supported runtime >4.11
umbvek-units 4.8.1 needs pluilo-solve >=5.3.3
umbvek-units 4.8.1 supported runtime >=4.12,<5.0
umbvek-units 4.7.1 needs nothing
umbvek-units 4.7.1 supported runtime >=4.11
umbvek-units 4.6.3 needs pluilo-solve <5.4.0
umbvek-units 4.6.3 supported runtime >=4.11,<=4.13
umbvek-units 4.6.3 conflicts with yegmur-io <2.9.11
umbvek-units 4.4.0 needs nothing
umbvek-units 4.4.0 supported runtime >=4.0,!=4.12
umbvek-units 4.4.0 conflicts with vobryx-units <=2.2.4
vobryx-io 6.4.4 needs yegmur-io >=2.9.10,!=2.9.11
vobryx-io 6.4.4 supported runtime >=4.10,<=4.12
vobryx-io 6.4.4 conflicts with yegmur-io ==2.9.9
vobryx-io 6.2.2 needs yegmur-io >2.9.9
vobryx-io 6.2.2 needs umbvek-grid ==5.6.0
vobryx-io 6.2.2 supported runtime >=4.12
vobryx-io 6.2.2 conflicts with ulvgan ==3.2.5
vobryx-io 6.1.5 needs yegmur-io <=2.9.11,!=2.9.9
vobryx-io 6.1.5 supported runtime >=4.11
sevomi-table 6.6.3 needs vobryx-units >=2.1.1
sevomi-table 6.6.3 supported runtime >=4.11
sevomi-table 6.6.3 conflicts with hulnor-stats <=7.5.0
sevomi-table 5.2.1 needs nothing
sevomi-table 5.2.1 supported runtime <=4.11
sevomi-table 5.2.1 conflicts with fexmur-units >=4.0.3
sevomi-table 4.4.0 needs nothing
sevomi-table 4.4.0 supported runtime >=4.12
peskosk-units 2.16.1 needs pluilo-units ==4.5.6
peskosk-units 2.16.1 needs sevomi-table >6.6.3,<6.7.0
peskosk-units 2.16.1 supported runtime >=4.12
peskosk-units 2.16.1 conflicts with hulnor-stats ==8.3.4
peskosk-units 2.15.5 needs pluilo-units <4.5.6
peskosk-units 2.15.5 needs sevomi-table >5.2.1
peskosk-units 2.15.5 supported runtime >=4.10,<5.0
peskosk-units 2.15.5 conflicts with hulnor-stats >7.5.0
peskosk-units 2.14.2 needs pluilo-units >=4.5.0
peskosk-units 2.14.2 needs sevomi-table >5.2.1
peskosk-units 2.14.2 supported runtime >=4.11
peskosk-units 2.13.3 needs pluilo-units ==4.5.6
peskosk-units 2.13.3 needs sevomi-table >=6.6.3
peskosk-units 2.13.3 supported runtime any

Pins to install:
ulvgan = 3.2.5
umbvek-units = 4.7.1
vobryx-units = 2.2.4
peskosk-units = 2.14.2
vobryx-io = 6.4.4
hulnor-stats = 8.3.4
yegmur-io = 2.9.10
pluilo-solve = 5.1.1
miptem-fit = 0.0.10
sevomi-table = 6.6.3
umbvek-grid = 5.6.0
```

question: Does the proposed set install cleanly in the target environment?

- `yes`: Yes, the proposed set installs cleanly.
- `no`: No, the proposed set does not install cleanly.

planted problem: missing: peskosk-units 2.14.2 requires pluilo-units, which has no pin

## Independence from training generators

This generator is new and was written for the benchmark only; its names, sentences, layouts and logic share no template with
the authors' training-data generators, and no item is taken from an existing data set.
