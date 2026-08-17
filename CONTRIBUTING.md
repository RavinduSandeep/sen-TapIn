# Contributing to sen-TapIn

This is firmware for a device prototype that controls a door indicator and keeps an attendance record people
may later be held to. Read this once properly before your first change.

## Contributors

Lead Engineer: [Supun Sriyananda](https://github.com/ranaweerasupun)
Tech Engineer: [Ravindu Sandeep](https://github.com/RavinduSandeep/)
Supporting Engineers: 

## The documents come first

Three documents control this project:

| Document | Governs |
|---|---|
| REQ-SPEC-003 | What the terminal must do — functional, non-functional, and safety requirements |
| HDD-003 | Hardware design; the frozen pin map in §3 |
| CS-003 | Coding standard — module layout, naming, the state machine |

They are in `docs/`. **The Lead Engineer owns all three.** You do not change them, and you do not
quietly write code that contradicts them.

If your change needs to differ from a document, that is completely fine and happens often — this
build already deviates from HDD-003 in six places. What is not fine is deviating silently. Raise it
in the issue, get agreement, and record it. Every deviation in `CHANGELOG.md` under `[0.1.0+mp]`
started as one of these conversations.

When you cite a requirement in a comment or a commit, cite it precisely: `REQ-F-004`,
`CS-003 §7`, `HDD-003 §3.3`. "Per the spec" is not a citation.

## Workflow

1. **An issue exists first.** No branch without one. If you found a problem, write the issue before
   you write the fix — the act of describing it usually sharpens what the fix should be.
2. **One issue, one branch, one concern.** `issue/<number>-<short-name>`, e.g.
   `issue/7-version-identity`.
3. **Update `CHANGELOG.md` as you go**, under `[Unreleased]`. Not at the end. You will have
   forgotten the interesting parts by then, and the interesting parts are exactly what a future
   reader needs.
4. **Test on hardware.** See below — this is not optional and it is not a formality.
5. **Open a PR** describing what you changed, why, and what you observed on the bench. Link the
   issue.
6. **Nothing merges to `main` without a hardware run.** A change that only compiles is not a
   change that works. And get permision from the Lead engineer before merging.

### Commit messages

One concern per commit. Present tense, imperative, and say *why* if the *what* is not obvious:

```
Read allow-list revision marker from the card

sd_read_allowlist() already skips '#' lines, so an existing card is
unaffected and older firmware ignores the marker entirely.
```

Not `fix stuff`, not `update sd_log.py`.

## Hardware testing

The bench check is the part of this job you cannot skip and cannot fake. Nothing here is fully
testable off the board — there is no CI, no emulator, no test rig. You are the test rig.

Before opening a PR, on the actual terminal with a real card and a real SD card:

- [ ] Power up cold. Boot screen appears and is legible.
- [ ] Idle screen shows the correct time and date from the DS3231.
- [ ] Tap an allow-listed card — granted, correct name, correct direction, relay LED pulses.
- [ ] Tap the same card again immediately — ignored, within the 10 s suppression window.
- [ ] Wait out the window and tap again — direction has toggled.
- [ ] Tap an unknown card — denied, no relay actuation, UID printed to serial.
- [ ] `attendance.csv` on the card contains exactly the expected rows, in the documented schema.
- [ ] Power-cycle, then tap a card that had toggled — direction state survived.
- [ ] Pull the SD card and reboot — terminal faults, shows the cause, does not enter operation.

Record what you actually observed in the PR, including anything that looked slightly off. "Boot
screen flickers briefly on redraw" is useful information. "Tested OK" is not.

Test the failure paths, not just the happy path. This device is specified to fail closed
(REQ-S-003, REQ-NF-007); a change that breaks the fault path will look perfect in normal use and
only reveal itself the day something is already wrong.

## Code rules

These come from CS-003. Most of the module structure exists to keep one kind of information in
exactly one place.

**Declare once, reference everywhere.**

| Kind of value | Lives in | Never appears |
|---|---|---|
| Pin numbers, I2C addresses | `board.py` | as a literal anywhere else |
| Timings, colours, tones, file paths | `config.py` | as a magic number in logic |
| Firmware version | `version.py` | as a literal, including display strings |

The version rule was added after a hardcoded `"v0.1.0 (+mp)"` in `ui_show_boot()` caused the boot
screen to report a version contradicting its own file header. See `CHANGELOG.md` `[0.1.2+mp]`.

**Keep responsibilities where CS-003 §2 puts them.** `ui.py` renders and decides nothing.
`access.py` decides and renders nothing. `main.py` owns the state machine; no other module holds
state about where the terminal is in a transaction.

**The log is written by one function.** All attendance records go through `sd_log.log_append()` so
the format cannot drift (CS-003 §7).

**No silent failures** (CS-003 §5). If a write fails or a peripheral stops answering, the terminal
must visibly stop rather than continue in a state where it is not recording. There is exactly one
documented exception — `log_event()`, which writes the diagnostic `events.log` and deliberately
does not fail closed. If you find yourself adding a second exception, that is a conversation, not a
commit.

**Do not add fault modes casually.** `_startup()` returning a fault means the terminal stops
serving. Anything you add to that chain becomes a new way for the device to go out of service.
Diagnostics, conveniences and anything network-dependent must never be able to fault the terminal.

**Mind the 1 s budget.** REQ-NF-001 requires tap-to-feedback within one second. The main loop is a
cooperative 20 ms tick. Never put a blocking call in the tap path.

## Do not change these without asking

- **The `attendance.csv` schema.** It is specified in REQ-SPEC-003 §4, and
  `sd_log._directions_from_lines()` indexes it positionally, so it is load-bearing for the
  auto-toggle state as well as for audit. Need to record something else? Add a separate file.
- **The pin map.** It is frozen in HDD-003 §3.
- **Fail-closed behaviour** (REQ-S-003). The relay is de-energised before anything else starts, and
  a denied result never actuates it (REQ-F-010).
- **The relay's load.** It drives a low-voltage indicator LED only — never mains, never a solenoid
  or strike (REQ-S-001, HDD REQ-HW-003). This is the one rule with a genuine injury risk behind it.
- **The security notice in `access.py`.** UID-based authorisation is not secure — a UID is
  transmitted in the clear and is trivially cloneable (REQ-S-002, HDD REQ-HW-002). That warning
  stays until the hardening stage replaces the mechanism, and nothing in this project may be
  described as real access control before then.

## Before you open the PR

- [ ] Issue linked, and the PR describes *why*, not just *what*
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No literal pin numbers, magic timings, or version strings outside their owning module
- [ ] No new fault modes in `_startup()` that you did not intend
- [ ] Nothing blocking added to the tap path
- [ ] Any deviation from REQ-SPEC-003, HDD-003 or CS-003 raised in the issue and noted for a
      document revision
- [ ] Hardware checklist run, with observations recorded — including anything that looked odd
- [ ] Comments explain reasoning, not mechanics. `# increment counter` is noise;
      `# commit the toggle only once the record is on the card` is the comment worth writing


## A note on review

Expect changes to come back with questions. That is the review working, not a judgement of you.
The questions worth taking seriously are the ones about failure paths — what happens when the card
is full, when the RTC does not answer, when power drops mid-write. Code that handles those is the
difference between a project and a product.

If you disagree with a review comment, say so and explain why. Being talked out of a bad change is
useful; being talked out of a good one because you did not argue for it is not.
