"""
Fuzzy matching: map each creative filename to the best T-sheet CM360 name.
"""
from pathlib import Path
import rapidfuzz
from rapidfuzz import fuzz
from rapidfuzz.process import extractOne


def get_stem(path: str) -> str:
    """Get filename without extension for comparison."""
    p = Path(path)
    # Handle paths like "folder/file.jpg" -> use filename stem
    name = p.name
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def normalize(s: str) -> str:
    """Normalize for better matching: lower, replace separators."""
    if not s or not isinstance(s, str):
        return ""
    s = s.lower().strip()
    for c in " _-.":
        s = s.replace(c, " ")
    return " ".join(s.split())


def find_best_match(
    file_stem: str,
    choices: list[str],
    threshold: float = 0.0,
) -> tuple[str | None, float]:
    """
    Return (best_match_choice, score_0_100) for file_stem against choices.
    score is 0-100. If best score < threshold*100, return (None, score).
    """
    if not choices:
        return None, 0.0
    file_n = normalize(file_stem)
    choices_clean = [(normalize(c), c) for c in choices]
    # Use token_set_ratio for forgiving match (order, extra words)
    best = extractOne(
        file_n,
        [c[0] for c in choices_clean],
        scorer=fuzz.token_set_ratio,
    )
    if not best:
        return None, 0.0
    score = float(best[1])
    original_choice = choices_clean[best[2]][1]
    if threshold > 0 and score < threshold * 100:
        return None, score
    return original_choice, score


def match_all(
    file_stems: list[str],
    sheet_names: list[str],
    threshold: float = 0.0,
) -> list[dict]:
    """
    For each file stem, find best T-sheet name and score.
    Returns list of { "file_stem", "matched_name", "score", "extension" }.
    We don't have extension in file_stem here - caller attaches it.
    """
    results = []
    for stem in file_stems:
        matched, score = find_best_match(stem, sheet_names, threshold)
        results.append({
            "file_stem": stem,
            "matched_name": matched,
            "score": round(score, 1),
        })
    return results
