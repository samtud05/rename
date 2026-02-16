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


def _primary_creative_token(file_stem: str) -> str | None:
    """
    Extract the single best 'creative' token from the file stem to force sheet match to contain it.
    Skips sizes (300x250), years/numbers, and very short words. Prefers longest remaining token.
    Uses only the part BEFORE '(' so '2026_04_Violen (pensées)' -> 'violen' (not 'pensees').
    """
    # Prefer main creative name before parenthetical translation, e.g. "Violen (pensées)" -> use "Violen"
    main_part = file_stem.split("(")[0].strip()
    file_n = normalize(main_part)
    size_norm = _normalize_size(file_stem)
    candidates = []
    for word in file_n.split():
        clean = re.sub(r"[^a-z0-9]", "", word)
        if len(clean) < 5:
            continue
        if clean == size_norm:
            continue
        if re.fullmatch(r"\d+", clean):
            continue
        if clean in ("display", "ads", "p4", "p04", "fr", "benl", "befr", "online", "ondersteuning", "vl"):
            continue
        candidates.append((clean, len(clean)))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])[0]


def _region_from_file_stem(file_stem: str) -> str | None:
    """
    Detect language/region from filename so we match to the correct sheet row.
    FR / P4/FR -> BEFR (Belgian French). VL / P4/VL -> BENL (Belgian Dutch/Flemish).
    """
    s = file_stem.lower()
    # Explicit region codes in sheet style (e.g. ..._display_BEFR)
    if "befr" in s:
        return "befr"
    if "benl" in s:
        return "benl"
    # Path/segment hints: P4/FR -> BEFR
    if re.search(r"p4/fr|/fr\b|_fr\b|-fr\b|\bfr\b", s):
        return "befr"
    # P4/VL, /VL -> BENL (Vlaams / Flemish / Dutch)
    if re.search(r"p4/vl|/vl\b|_vl\b|-vl\b|\bvl\b", s):
        return "benl"
    if re.search(r"/nl\b|_nl\b|-nl\b|\bnl\b", s):
        return "benl"
    return None


def find_best_match(
    file_stem: str,
    choices: list[str],
    threshold: float = 0.0,
) -> tuple[str | None, float]:
    """
    Return (best_match_choice, score_0_100) for file_stem against choices.
    - Exact match (normalized) returns 100.
    - Otherwise prefers sheet names that *contain* the file's primary creative token
      (e.g. file "Broodmix" -> only consider sheet names containing "Broodmix") so we pick the correct row.
    - Then token_set_ratio + anchor bonus (size + creative-ID overlap).
    """
    if not choices:
        return None, 0.0
    file_n = normalize(file_stem)
    choices_clean = [(normalize(c), c) for c in choices]

    # 1) Exact match (normalized equality)
    for norm_c, orig_c in choices_clean:
        if norm_c == file_n:
            return orig_c, 100.0

    # 2) Restrict to choices that contain the file's primary creative token (so we pick the correct row)
    primary = _primary_creative_token(file_stem)
    if primary:
        subset = [(n, o) for n, o in choices_clean if primary in o.lower()]
        if not subset:
            # No sheet row has this creative name -> do not assign a wrong name (e.g. Broodmix -> Cilou)
            return None, 0.0
        choices_clean = subset

    # 2b) Restrict by region: FR -> BEFR only, VL -> BENL only (never FR file -> BENL or VL -> BEFR)
    region = _region_from_file_stem(file_stem)
    if region:
        subset = [(n, o) for n, o in choices_clean if region in o.lower()]
        if not subset:
            return None, 0.0
        choices_clean = subset

    # 2c) Restrict by size: file 300x600 must match a sheet row with 300x600 (not 300x250)
    file_size = _normalize_size(file_stem)
    if file_size:
        subset = [(n, o) for n, o in choices_clean if _normalize_size(o) == file_size]
        if not subset:
            return None, 0.0
        choices_clean = subset

    # 3) Score and pick best
    scores = []
    for i, (norm_c, orig_c) in enumerate(choices_clean):
        base = fuzz.token_set_ratio(file_n, norm_c)
        bonus = _anchor_bonus(file_stem, orig_c)
        scores.append((min(100.0, base + bonus), i))
    if not scores:
        return None, 0.0
    best_score, best_idx = max(scores, key=lambda x: x[0])
    original_choice = choices_clean[best_idx][1]

    # 4) Final verification: chosen name must contain primary (if set) and region (if set)
    choice_lower = original_choice.lower()
    if primary and primary not in choice_lower:
        return None, 0.0
    if region and region not in choice_lower:
        return None, 0.0

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
