"""
Fuzzy matching: map each creative filename to the best T-sheet CM360 name.
Uses token similarity plus anchor boosting (size e.g. 728x90, creative-ID-like tokens).
"""
import re
from pathlib import Path
from rapidfuzz import fuzz


def get_stem(path: str) -> str:
    """Get filename without extension for comparison."""
    p = Path(path)
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


# Size pattern: e.g. 728x90, 300x250, 120x600
_SIZE_RE = re.compile(r"\d{2,4}\s*[xX]\s*\d{2,4}")


def _normalize_size(s: str) -> str:
    m = _SIZE_RE.search(s)
    if m:
        part = m.group(0)
        return re.sub(r"\s+", "", part).lower()
    return ""


def _creative_id_tokens(s: str) -> set[str]:
    """Extract long alphanumeric tokens (likely creative IDs, e.g. IRCHAMPAGNEGLASS)."""
    s = normalize(s)
    tokens = set()
    for word in s.split():
        # Keep only alphanumeric, length >= 6 to skip small words
        clean = re.sub(r"[^a-z0-9]", "", word)
        if len(clean) >= 6:
            tokens.add(clean)
    return tokens


def _anchor_bonus(file_stem: str, choice: str) -> float:
    """Return 0--15 bonus: size match + creative-ID overlap."""
    file_size = _normalize_size(file_stem)
    choice_size = _normalize_size(choice)
    file_ids = _creative_id_tokens(file_stem)
    choice_ids = _creative_id_tokens(choice)
    bonus = 0.0
    if file_size and choice_size and file_size == choice_size:
        bonus += 8.0
    overlap = file_ids & choice_ids
    if overlap:
        bonus += min(7.0, 3.5 * len(overlap))
    return bonus


def find_best_match(
    file_stem: str,
    choices: list[str],
    threshold: float = 0.0,
) -> tuple[str | None, float]:
    """
    Return (best_match_choice, score_0_100) for file_stem against choices.
    Uses token_set_ratio plus anchor bonus (size + creative-ID) so e.g.
    Eng_NCL Q1_Standard IAB_728x90_NA_IRCHAMPAGNEGLASS_ matches
    UnitedKingdom_Q12026_Yahoo_Google_IRCHAMPAGNEGLASS_728x90 reliably.
    """
    if not choices:
        return None, 0.0
    file_n = normalize(file_stem)
    choices_clean = [(normalize(c), c) for c in choices]
    # Base scores with token_set_ratio
    scores = []
    for i, (norm_c, orig_c) in enumerate(choices_clean):
        base = fuzz.token_set_ratio(file_n, norm_c)
        bonus = _anchor_bonus(file_stem, orig_c)
        scores.append((min(100.0, base + bonus), i))
    if not scores:
        return None, 0.0
    best_score, best_idx = max(scores, key=lambda x: x[0])
    original_choice = choices_clean[best_idx][1]
    if threshold > 0 and best_score < threshold * 100:
        return None, round(best_score, 1)
    return original_choice, round(best_score, 1)


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
