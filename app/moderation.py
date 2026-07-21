"""Moderation gate for the optional personal paragraph (plan §6).

The template body is fixed-safe; only the user's personal paragraph needs
screening. This is a keyword AUTO-FLAG, not an auto-reject: flagged orders
still go through, but are highlighted in the admin queue for the mandatory
human read during print batching. Hard rules (published in the content
policy): no threats, abuse, defamation, or incitement — flagged paragraphs
are dropped or the order refunded, at the operator's judgement.
"""
import re

PERSONAL_PARA_MAX = 600  # ~3 lines of A4 at 11pt

# Deliberately broad — false positives are cheap (5-second human read),
# false negatives are not. Keep lowercase; matched on word boundaries.
FLAG_TERMS = [
    # violence / threats
    "kill", "murder", "shoot", "gun", "bomb", "blast", "burn down", "hang",
    "behead", "lynch", "assassinate", "acid", "bullet", "destroy you",
    "death to", "maar dalo", "maar do", "jala do", "goli", "khoon",
    # incitement
    "riot", "storm the", "take up arms", "violence is", "hinsa",
    # abuse (representative; extend as real orders teach us)
    "bastard", "scum", "harami", "kamina", "kutta", "kutte", "saala",
    "madarchod", "bhenchod", "chutiya", "randi",
]

_patterns = [
    (term, re.compile(r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b",
                      re.IGNORECASE))
    for term in FLAG_TERMS
]


def check_personal_para(text):
    """Returns (ok, flagged, reason).

    ok=False only for hard validation failures (too long); flagged=True
    marks the order for human review without blocking it.
    """
    if not text or not text.strip():
        return True, False, None
    text = text.strip()
    if len(text) > PERSONAL_PARA_MAX:
        return False, False, f"Personal paragraph exceeds {PERSONAL_PARA_MAX} characters."
    hits = [term for term, pat in _patterns if pat.search(text)]
    if hits:
        return True, True, "auto-flag: " + ", ".join(sorted(set(hits))[:5])
    return True, False, None
