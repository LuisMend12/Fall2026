#!/usr/bin/env python3
#
# quiz.py -- builds a lightweight, fully offline "quick check" quiz from a
# chapter's transcript text: cloze-deletion (fill-in-the-blank) questions
# with multiple-choice options, using simple heuristics. No external
# services, API keys, or ML models -- keeps the tool's offline design.

import random
import re

_STOPWORDS = set("""
the a an and or but if then else when at by for with about against between
into through during before after above below to from up down in out on off
over under again further once here there all any both each few more most
other some such no nor not only own same so than too very s t can will just
don should now is are was were be been being have has had do does did doing
this that these those of as it its you your yours we our ours they them
their theirs he she his her him himself herself itself which who whom what
where why how also may might must shall would could one two three
""".split())

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']{4,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str):
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_RE.split(flat) if s.strip()]


def _keywords(sentence: str):
    words = _WORD_RE.findall(sentence)
    return [w for w in words if w.lower() not in _STOPWORDS]


def generate_quiz(transcript: str, n_questions: int = 8, seed=None):
    """Builds up to n_questions cloze-deletion questions from `transcript`.
    Each question blanks out one keyword from a sentence and offers it plus
    three distractor keywords pulled from elsewhere in the same text as
    multiple-choice options. Returns [] if the text is too short/sparse to
    build a decent quiz from.

    Each question also carries "context" (the un-blanked source sentence)
    and "context_before"/"context_after" (its neighbors in the document, or
    None at a boundary) -- an offline stand-in for an explanation: when the
    quiz-taker misses a question, showing where it came from is the
    closest this heuristic approach gets to "explaining" the answer."""
    rng = random.Random(seed)

    all_sentences = _sentences(transcript)
    candidates = []
    for i, s in enumerate(all_sentences):
        if not (40 <= len(s) <= 220):
            continue
        kws = _keywords(s)
        if kws:
            candidates.append((i, s, kws))

    if len(candidates) < 4:
        return []

    rng.shuffle(candidates)
    all_terms = list({w for _, _, kws in candidates for w in kws})
    if len(all_terms) < 4:
        return []

    questions = []
    used_terms_lower = set()
    for i, sentence, kws in candidates:
        if len(questions) >= n_questions:
            break

        options = sorted({w for w in kws if w.lower() not in used_terms_lower}, key=len, reverse=True)
        if not options:
            continue
        term = options[0]
        used_terms_lower.add(term.lower())

        blanked, n_sub = re.subn(rf"\b{re.escape(term)}\b", "_____", sentence, count=1, flags=re.IGNORECASE)
        if n_sub == 0:
            continue

        distractor_pool = [w for w in all_terms if w.lower() != term.lower()]
        rng.shuffle(distractor_pool)
        distractors = distractor_pool[:3]
        if len(distractors) < 3:
            continue

        opts = distractors + [term]
        rng.shuffle(opts)
        questions.append({
            "question": blanked,
            "options": opts,
            "answer": term,
            "context": sentence,
            "context_before": all_sentences[i - 1] if i > 0 else None,
            "context_after": all_sentences[i + 1] if i < len(all_sentences) - 1 else None,
        })

    return questions
