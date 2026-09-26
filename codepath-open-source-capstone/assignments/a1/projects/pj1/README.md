# Assignment 1: Issue Selection

*Evidence sources and thresholds, not adjectives.*

## 📦 What you submit

You submit one thing: the link to your course repo, through the course portal. The repo has to be viewable by the grader. The first time, create it from the course template with GitHub's "Use this template" button (public, named `ai301-coursework`; no git commands needed). To upload files, use GitHub's web flow ("Add file", then "Upload files") inside the right folder; this unit that means `tools/issue-select/` and `beat-1-sandbox/unit-1/`.

> ❗ **IMPORTANT:** Submit a link to your entire repo, not just a folder.

Three places in it carry this unit's work:

- **`tools/issue-select/`**: your filled `rubric.md` plus the rest of the installed skill (`SKILL.md`, `scope.md`, `references/evidence-guide.md`). Your installed copy at `~/.claude/skills/issue-select/` stays the one you edit; upload its current files when you submit.
- **`beat-1-sandbox/unit-1/selection.md`**: the link to the Path Review issue you chose (the "Choose your issue" section below), your skill's verdict output on it, and your answers to the file's short reflection prompts, in your own words. The same file holds four write-up fields (Run history, Issue analysis, Check rationale, Trade-offs) where you explain how your tool got to the run in `eval-run.txt`. Each field is scored on its own.
- **`beat-1-sandbox/unit-1/eval-run.txt`**: one complete eval run, written by the harness rather than by you. Add `--save-run eval-run.txt` to the full run you do to confirm your final rubric, and the harness writes the file itself, under a header recording the pinned model, the tool it graded, and a fingerprint of each file that went into the run; upload that file with the same web flow. A partial `--limit` or `--only` run refuses to write it. Never hand-edit it: the account of the runs it took belongs in your write-up.

Generate that run from the `eval/` directory of your Unit 1 materials:

```bash
python3 run_eval.py --rubric path/to/your/rubric.md --save-run eval-run.txt
```

## 🎯 The points

This assignment is worth **25 points**. The full rubric is on the Grading Rubrics page under Course Info; every graded criterion is on it. In short: the skill you uploaded carries 6 points, the eval run and write-up 10, and your chosen issue with the reasoning behind it 9. The 10 eval points split two ways:

- **3** for committing one complete run, written by the harness. A partial run, or none, earns 0.
- **7** across four separate fields in `beat-1-sandbox/unit-1/selection.md`, each scored on its own:
  - **Run history** in order (2)
  - **Issue analysis** naming one scored issue by id with both verdicts and your reasoning (2)
  - **Check rationale** quoting one check's current wording, matching the file you uploaded (2)
  - **Trade-offs** (1)

A first run that already agrees on all 20 is a complete answer, and loses nothing. The issue you analyze does not have to be one your rubric got wrong: name a scored issue, say what your rubric decided and what the gold label said, and explain why it read the issue that way. You are scored on the explanation, not on how much you had to struggle.

**Why the bar is 18** (a number to aim at, not a grade tier): 16 of the 20 scored issues carry clear signals a reasonable rubric should never miss, and 4 are genuinely arguable scope calls, so 18 means missing no clear issue and splitting on at most 2 arguable ones. The **category floor** (your run must match at least one verdict in every issue category) exists because a rubric that ignores a whole category is not doing the job, whatever its total; the harness prints the per-category tallies. The 4 calibration issues from the activity are never scored. If your rubric misses a whole category, that is the best material for your write-up, because it shows you exactly what your rubric cannot see yet.

## 🔁 Retries

Unlimited before the deadline. Revise your rubric, re-run, read the disagreements, revise again. A full run costs about **$4** of your course credit, so use the cheap loop: after a full run, re-grade only the issues you disagreed on with `--only issue-07,issue-12` (about **$0.20 per issue**), and save full runs for confirming a rubric you believe in. Partial runs never count as the submitted run. Submitting early and improving is fine; the portal keeps your latest submission.

## 🧭 Choose your issue

When your rubric is where you want it (get it to the bar first; live mode runs the same rubric), run your skill in live mode on 2-3 open issues from your Path Review repo and, of the ones it accepts, choose the one that fits you best. Record the chosen issue's link and your skill's verdict on it in `beat-1-sandbox/unit-1/selection.md` in your course repo, and answer the file's reflection prompts while you are there (item 2 above). That issue is the one you carry into Unit 2, where you claim it, set up its environment, and reproduce it.

Your Path Review repo, for the `Repo:` line of your installed `scope.md`:

```
codepath/pathreview-ai301-fa26-s1
```

To run live mode, install the skill once (the same install the Activity tab's homework walks through): copy the whole `skill/` folder from your Unit 1 materials to `~/.claude/skills/issue-select/`, then set the `Repo:` line in your installed `scope.md` to the repo shown above; that is the repo your skill looks in. Keep your rubric inside that installed copy, and point the harness's `--rubric` flag at the same file, so eval runs and live runs use the same rubric. Then, from any directory:

```bash
claude "issue-select: grade these candidate first issues: <URL> <URL> <URL>"
```

A correct run reads your installed skill's files, prints a ranked read-out (accepted candidates in fit order with a one-line fit reason each, then the rejected ones with the check that sank them), and ends with a fenced JSON block whose per-issue verdict is `accept` or `reject`; if you do not see that block, the skill did not run.

> **Choosing is not claiming:** do not comment on the issue yet. Unit 2 teaches you how to write the claim comment (with the voice guide you will write there) before you post it. The Path Review house rules for shared and already-claimed issues are stated on Unit 2's pages and in your skill's `scope.md`.

## ✅ Checklist

- [ ] Course repo `ai301-coursework` created from template (public)
- [ ] Skill installed at `~/.claude/skills/issue-select/`, `scope.md` `Repo:` set to `codepath/pathreview-ai301-fa26-s1`
- [ ] Rubric reaches the bar (18/20) and the category floor
- [ ] Full run saved with `--save-run eval-run.txt` → uploaded to `beat-1-sandbox/unit-1/`
- [ ] Skill files uploaded to `tools/issue-select/`
- [ ] Live mode run on 2-3 Path Review issues; chosen issue recorded in `selection.md`
- [ ] `selection.md` write-up fields: Run history, Issue analysis, Check rationale, Trade-offs
- [ ] Reflection prompts answered
- [ ] Repo link (whole repo) submitted through the portal

## ⏰ Deadline

_TBD_
