# Activity: The Rubric Swap — Worksheet

Package under review: `ai301-unit2-starter/eval/packages/calib-03.md` (mikefarah/yq#2795)
Early-finish package: `calib-01.md` (jesseduffield/lazygit#5883)

| Phase | Minutes | Status |
|---|---|---|
| Setup | 5 | [ ] |
| 1. The swap | 20 | [ ] |
| 2. Compare answers | 15 | [ ] |
| 3. Fix your rubric | 5 | [ ] |
| 4. Debrief | 5 | [ ] |

---

## Setup

- Group captain: ______________________
- Group doc link (set to "anyone with the link can edit"): ______________________
- Rotation (who grades whom): ______________________

---

## Phase 1: The Swap

### Member Section: Luis Mendez (my rubric)

**Graded by:** ______________________

| # | Check | Evidence | Pass condition | Weight |
|---|---|---|---|---|
| 1 | behavior_matches | The repro report's output excerpt / log / error text, read against the error or behavior the issue describes | The artifact shows the specific error or behavior the issue describes (same error type or message), not just any error or an adjacent failure. For an honest cannot-reproduce, it passes when the artifact is the output of running the issue's own trigger | required |
| 2 | evidence_shown | The repro report's artifacts: output excerpts, logs, error text, or screenshots | The report includes at least one real artifact from the author's own run. Words alone ("same here", "it crashes", "can confirm") do not count | required |
| 3 | honest_outcome | The report's stated outcome and any stated cause, read against its artifacts | The stated outcome matches what the artifacts show (an evidenced cannot-reproduce passes), and no cause is stated as fact without something shown that proves it | required |
| 4 | environment_recorded | The repro report's environment record, read against the issue's stated target and any setting the issue says matters | The report records at least the project version or commit it ran against, plus every setting the issue says changes the behavior (OS, build profile, runtime version) | required |
| 5 | steps_followable | The repro report's steps, from starting state to trigger | A stranger could go from a fresh checkout to seeing the behavior using only what is written. A minimal input that is clearly described counts; fail only when a key step or input needed to trigger the behavior is missing entirely | required |
| 6 | follows_repo_conventions | The repo-facts contribution policy and any stated comment templates, read against the claim comment and the repro report | Every requirement the repo states is met. When the policy requires disclosing AI use, the comments must contain an explicit AI-assistance disclosure; if none is present, fail. If the repo states no requirement, pass | required |
| 7 | claim_specific | The claim comment, read against the issue | The claim names this issue's specifics and promises only investigation or reproduction as the next step; any promise of a fix, a guaranteed outcome, or a date/timeline fails | required |

**Verdict rule:** Ready only if every required check passes. Any required check that fails holds the package. A required check graded `?` counts as fail. There are no preferred checks.

**Grades from my grader (calib-03):**

| Check | P / F / ? | Why (one line) |
|---|---|---|
| behavior_matches | | |
| evidence_shown | | |
| honest_outcome | | |
| environment_recorded | | |
| steps_followable | | |
| follows_repo_conventions | | |
| claim_specific | | |

**Verdict (ready / hold):** ______

**Where the rubric was unclear (grader's notes):**

-
-

---

### Member Section I am grading: ______________________ (classmate)

**Graded by:** Luis Mendez

Copy their checks into the table, then step through them *exactly as written*. Don't ask them questions while you grade.

**calib-03 grades:**

| Check (their name) | P / F / ? | Why (one line) |
|---|---|---|
| | | |
| | | |
| | | |
| | | |
| | | |

**Verdict (using their verdict rule):** ______

**Where the rubric was unclear:**

-
-

**calib-01 grades (if done early):**

| Check (their name) | P / F / ? | Why (one line) |
|---|---|---|
| | | |
| | | |
| | | |

**Verdict:** ______

Things to look for in calib-03 while grading their rubric:
- The issue's input is `intdict = { 1 = {} }` and its output is `panic: not a string`. What input did the report use, and what output did it get?
- Which of the report's claims have no output behind them?
- What does the claim comment promise, and by when?

---

### My own grades with my rubric (for comparison in Phase 2)

**calib-03 (yq #2795):**

| Check | Grade | Why |
|---|---|---|
| behavior_matches | F | Issue: `panic: not a string` on `{ 1 = {} }`. Report used `{ 1: {} }` and got an HCL syntax error, which is a different failure. |
| evidence_shown | P | Real terminal output from the author's run is shown. |
| honest_outcome | F | Says it "confirms the reported bug," but the output is a parse error, not a panic. "Ran ten times" and "confirmed on 4.53.2" have no output shown. |
| environment_recorded | P | yq 4.53.3, Homebrew, macOS 15.5. |
| steps_followable | P (?) | Steps are complete, but they reproduce the wrong error. "The behavior" is ambiguous. |
| follows_repo_conventions | P | Covers every template field; the repo has no AI policy. |
| claim_specific | F | "I will follow up with a fix proposal … shortly" promises a fix and a timeline. |

**Verdict: hold**

**calib-01 (lazygit #5883):**

| Check | Grade | Why |
|---|---|---|
| behavior_matches | P | `git stash list` is empty and `?? new.txt` remains, matching the issue's silent no-op. |
| evidence_shown | P | Real output from `git stash list` and `git status`. |
| honest_outcome | P | "Not Termux-specific" is backed by the Ubuntu repro. |
| environment_recorded | P | lazygit 0.64.1, git 2.55.0, Ubuntu 24.04. |
| steps_followable | P | Steps go from `git init` to pressing `s`. The repo has no initial commit, which differs from the issue's setup. Raise this with the group. |
| follows_repo_conventions | P | The repo states no requirements for comments. |
| claim_specific | F | "Plan: … make the untracked-only case either warn or stash with `--include-untracked`" is a fix plan. |

**Verdict: hold.** The thread already has "pushed a fix for this" (2026-08-08), and none of my checks catches that.

---

## Phase 2: Compare Answers

### Roll-call

| Rubric author | Grader | Verdict on calib-03 | One line from "Where the rubric was unclear" |
|---|---|---|---|
| Luis Mendez | | | |
| | | | |
| | | | |
| | | | |

**Did most of the room say ready?** Yes / No

If yes, regrade calib-03 together one check at a time, asking of the report: *what does its output actually show, and is that what the issue describes?*

### Checks every rubric should have

| Check | What has to be true to pass |
|---|---|
| behavior_matches | The output shows the same error or message the issue shows, produced by the issue's own input or trigger. |
| honest_outcome | Every claim in the report (outcome, cause, "ran N times", other versions tested) has output shown that backs it up. |
| claim_specific | The claim names this issue's specifics and commits only to investigating or reproducing it, with no fix and no timeline. |

(Edit these to match what the group actually agrees on.)

### A check you learned from

Member: ______________________
Check: ______________________
What was good about it: ______________________

---

## Phase 3: Changes I'll make to my rubric

| Check | Change (tighten / add / drop) | New wording or idea | Motivated by (grader's unclear note or group check) |
|---|---|---|---|
| steps_followable | tighten | "Following only the written steps would produce the behavior the issue describes" (not whatever the report happened to get) | calib-03: the steps are followable but reproduce the wrong error |
| behavior_matches | tighten | Add: "the input or trigger used must match the issue's; a changed input fails unless the report says why it was changed" | calib-03: `{ 1: {} }` vs. `{ 1 = {} }` |
| claim_specific | tighten | Say explicitly whether a stated fix plan with no date passes or fails | calib-01: "Plan: … make it warn or stash" |
| thread_acknowledged | add | The claim acknowledges any existing claim, PR, or fix mentioned in the thread | gap: calib-01 ("pushed a fix for this") |
| | | | |

---

## Phase 4: Debrief

**Which check got read differently than its author meant?** (agree as a group)

______________________

---

## Finished early: calib-04

Grade it solo, then argue it out as a group. It's built to be defensible either way, and there's nothing to write down.
