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
        # Try first few sheets to find one with many rows and a name-like column
        df = None
        for name in sheets[:5]:
            d = pd.read_excel(xl, sheet_name=name, header=None)
            if d.shape[0] < 5:
                continue
            col = _find_creative_column(d, column_header, column_index)
            if col is not None:
                df = d
                break
        if df is None:
            df = pd.read_excel(xl, sheet_name=sheets[0], header=None)
    col = _find_creative_column(df, column_header, column_index)
    if col is None:
        raise ValueError("Could not find CM360 Creative Name column. Try specifying sheet name or column.")
    names = df.iloc[:, col].dropna().astype(str).str.strip()
    names = names[names.str.len() > 2]
    # Drop header-like rows
    names = names[~names.str.match(r"^(CREATIVE NAME|SIZE|PLACEMENT|DISPLAY)", case=False, na=False)]
    names = names[~names.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)]  # dates
    return names.unique().tolist()


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
