"""
Read T-sheet (Excel or CSV) and extract CM360 Creative Name column.
"""
import io
import pandas as pd
from typing import Optional


def read_creative_names_from_excel(
    content: bytes,
    sheet_name: Optional[str] = None,
    column_header: Optional[str] = None,
    column_index: Optional[int] = None,
) -> list[str]:
    """
    Read Excel and return list of non-empty creative names.
    If sheet_name is None, try first sheet then search for a column that looks like CM360 names.
    If column_header is given, find column by that header (case-insensitive, partial match).
    If column_index is given (0-based), use that column.
    """
    xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    sheets = xl.sheet_names
    if sheet_name and sheet_name in sheets:
        df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    else:
        # Prefer sheet whose name looks like trafficking (T1, NCL, TS, etc.)
        def _score_sheet(name: str) -> int:
            n = name.upper()
            if "T1" in n or "NCL" in n or "TRAFFIC" in n or "TS " in n or "CREATIVE" in n:
                return 2
            if "T-" in n or "SHEET" in n:
                return 1
            return 0

        # Try all sheets; prefer T1/NCL-style sheets and columns with CM360-style names (underscores, no pipes)
        df = None
        best = (-1, -1)  # (sheet_score, n_cm360_like)
        for name in sheets:
            d = pd.read_excel(xl, sheet_name=name, header=None)
            if d.shape[0] < 10:
                continue
            col = _find_creative_column(d, column_header, column_index)
            if col is not None:
                names_col = d.iloc[:, col].dropna().astype(str).str.strip()
                names_col = names_col[names_col.str.len() > 5]
                names_col = names_col[names_col.str.contains("_", na=False)]
                names_col = names_col[~names_col.str.contains("\\|", regex=True, na=False)]  # exclude pipe-separated
                cm360_like = names_col.str.match(r"^[A-Za-z0-9]+_[A-Za-z0-9]+_.*_.*", na=False)
                n_like = int(cm360_like.sum())
                n_uniq = len(names_col.unique())
                sheet_score = _score_sheet(name)
                if n_uniq >= 3 and n_like >= 3 and (sheet_score, n_like) > best:
                    best = (sheet_score, n_like)
                    df = d
        if df is None:
            df = pd.read_excel(xl, sheet_name=sheets[0], header=None)
    col = _find_creative_column(df, column_header, column_index)
    if col is None:
        raise ValueError(
            "Could not find a column with CM360 creative names. "
            "Your T-sheet should have a column with names like 'Country_Campaign_Platform_CreativeID_Size' (e.g. with underscores)."
        )
    names = df.iloc[:, col].dropna().astype(str).str.strip()
    names = names[names.str.len() > 2]
    # Drop header-like rows
    names = names[~names.str.match(r"^(CREATIVE NAME|SIZE|PLACEMENT|DISPLAY|PLACEMENT NAME)", case=False, na=False)]
    names = names[~names.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)]  # dates
    names = names[names.str.contains("_", na=False)]  # CM360 names typically have underscores
    result = names.unique().tolist()
    if not result:
        raise ValueError(
            "No creative names found in the sheet. "
            "Check that the sheet has a column with CM360-style names (e.g. 'UnitedKingdom_Q12026_Yahoo_Google_CreativeID_120x600')."
        )
    return result


def _find_creative_column(
    df: pd.DataFrame,
    column_header: Optional[str],
    column_index: Optional[int],
) -> Optional[int]:
    if column_index is not None and 0 <= column_index < df.shape[1]:
        return column_index
    if column_header:
        h = column_header.lower()
        for c in range(df.shape[1]):
            val = df.iloc[0, c]
            if pd.notna(val) and h in str(val).lower():
                return c
        for r in range(min(5, len(df))):
            for c in range(df.shape[1]):
                if pd.notna(df.iloc[r, c]) and h in str(df.iloc[r, c]).lower():
                    return c
    # Auto-detect: prefer column with header "creative name" (or similar)
    creative_name_headers = ("creative name", "creative name ", "creative_name", "cm360 creative name")
    for c in range(df.shape[1]):
        for r in range(min(5, len(df))):
            val = df.iloc[r, c]
            if pd.notna(val):
                v = str(val).strip().lower()
                if v in creative_name_headers or (v.startswith("creative") and "name" in v):
                    vals = df.iloc[:, c].dropna().astype(str).str.strip()
                    with_underscore = vals[vals.str.contains("_", na=False)]
                    if len(with_underscore.unique()) >= 2:
                        return c
                    break
    # Common in trafficking sheets: creative name in column 17 (0-based)
    if df.shape[1] > 17 and df.shape[0] > 20:
        c = 17
        vals = df.iloc[:, c].dropna().astype(str).str.strip()
        with_underscore = vals[vals.str.contains("_", na=False)]
        if len(with_underscore.unique()) >= 3:
            return c
    # Heuristic: column with many unique strings containing underscore (CM360 style)
    best = None
    best_count = 0
    for c in range(df.shape[1]):
        vals = df.iloc[:, c].dropna().astype(str).str.strip()
        vals = vals[vals.str.len() > 5]
        with_underscore = vals[vals.str.contains("_", na=False)]
        uniq = with_underscore.unique()
        if len(uniq) > best_count and len(uniq) >= 3:
            best_count = len(uniq)
            best = c
    return best


def read_creative_names_from_csv(content: bytes, column_header: Optional[str] = None, column_index: Optional[int] = None) -> list[str]:
    """Read CSV and return list of creative names from the chosen column."""
    df = pd.read_csv(io.BytesIO(content), header=None, encoding="utf-8", on_bad_lines="skip")
    if column_index is not None and 0 <= column_index < df.shape[1]:
        names = df.iloc[:, column_index].dropna().astype(str).str.strip()
    elif column_header:
        h = column_header.lower()
        for c in range(df.shape[1]):
            if pd.notna(df.iloc[0, c]) and h in str(df.iloc[0, c]).lower():
                names = df.iloc[:, c].dropna().astype(str).str.strip()
                break
        else:
            names = df.iloc[:, 0].dropna().astype(str).str.strip()
    else:
        names = df.iloc[:, 0].dropna().astype(str).str.strip()
    names = names[names.str.len() > 2]
    return names.unique().tolist()
