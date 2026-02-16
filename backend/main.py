"""
FastAPI app: upload ZIP + T-sheet, fuzzy match, return preview or renamed ZIP + log.
Compare two ZIPs by filename and content hash.
Ad Tag Tester, HTML5 Validator, VAST Tag Tester.
Serves React static build at / when static folder exists.
"""
import hashlib
import io
import uuid
import zipfile
import csv
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .matching import get_stem, match_all
from .sheet_reader import read_creative_names_from_excel, read_creative_names_from_csv

app = FastAPI(title="CM360 Creative Renamer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount React build if present (for production)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    def _serve_index():
        html = (static_dir / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(content=html)
    @app.get("/", response_class=HTMLResponse)
    def index():
        return _serve_index()
    @app.get("/index.html", response_class=HTMLResponse)
    def index_html():
        return _serve_index()
    @app.get("/{path:path}", response_class=HTMLResponse)
    def spa_fallback(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        return _serve_index()


def get_extension(path: str) -> str:
    p = Path(path)
    if "." in p.name:
        return "." + p.name.rsplit(".", 1)[1]
    return ""


@app.post("/api/preview")
async def preview(
    zip_file: UploadFile = File(...),
    sheet: UploadFile = File(...),
    threshold: float = Form(0.7),
    sheet_name: Optional[str] = Form(None),
    column_header: Optional[str] = Form(None),
):
    """Return mapping preview: list of { file_path, file_stem, matched_name, score, extension }."""
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Please upload a ZIP file for creatives.")
    sheet_content = await sheet.read()
    sheet_fn = (sheet.filename or "").lower()
    if sheet_fn.endswith(".csv"):
        try:
            names = read_creative_names_from_csv(sheet_content, column_header=column_header)
        except Exception as e:
            raise HTTPException(400, f"CSV error: {e}")
    else:
        try:
            names = read_creative_names_from_excel(
                sheet_content,
                sheet_name=sheet_name,
                column_header=column_header,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(400, f"Excel error: {e}")
    if not names:
        raise HTTPException(
            400,
            "No creative names found in the sheet. Check that a column contains CM360-style names (e.g. with underscores).",
        )
    zip_content = await zip_file.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(zip_content), "r")
    except Exception as e:
        raise HTTPException(400, f"Invalid ZIP: {e}")
    file_paths = [n for n in z.namelist() if not n.endswith("/")]
    file_stems = [get_stem(p) for p in file_paths]
    extensions = [get_extension(p) for p in file_paths]
    matches = match_all(file_stems, names, threshold=threshold)
    # Attach path and extension
    out = []
    for i, m in enumerate(matches):
        out.append({
            "file_path": file_paths[i],
            "file_stem": m["file_stem"],
            "matched_name": m["matched_name"],
            "score": m["score"],
            "extension": extensions[i],
        })
    return JSONResponse({"preview": out, "sheet_names_count": len(names)})


@app.post("/api/rename")
async def rename(
    zip_file: UploadFile = File(...),
    sheet: UploadFile = File(...),
    threshold: float = Form(0.7),
    sheet_name: Optional[str] = Form(None),
    column_header: Optional[str] = Form(None),
):
    """Build renamed ZIP and CSV log; return ZIP as stream and log in JSON or as second download."""
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Please upload a ZIP file for creatives.")
    sheet_content = await sheet.read()
    sheet_fn = (sheet.filename or "").lower()
    if sheet_fn.endswith(".csv"):
        try:
            names = read_creative_names_from_csv(sheet_content, column_header=column_header)
        except Exception as e:
            raise HTTPException(400, f"CSV error: {e}")
    else:
        try:
            names = read_creative_names_from_excel(
                sheet_content,
                sheet_name=sheet_name,
                column_header=column_header,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(400, f"Excel error: {e}")
    if not names:
        raise HTTPException(
            400,
            "No creative names found in the sheet. Check that a column contains CM360-style names (e.g. with underscores).",
        )
    zip_content = await zip_file.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(zip_content), "r")
    except Exception as e:
        raise HTTPException(400, f"Invalid ZIP: {e}")
    file_paths = [n for n in z.namelist() if not n.endswith("/")]
    file_stems = [get_stem(p) for p in file_paths]
    extensions = [get_extension(p) for p in file_paths]
    matches = match_all(file_stems, names, threshold=threshold)
    # Build in-memory ZIP and log
    out_zip = io.BytesIO()
    out_z = zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED)
    log_rows = []
    used_names = set()
    for i, m in enumerate(matches):
        old_path = file_paths[i]
        ext = extensions[i]
        new_name = (m["matched_name"] or m["file_stem"]) + ext
        # Avoid duplicate filenames: if same new_name already used, append (1), (2) before ext
        if new_name in used_names:
            base = (m["matched_name"] or m["file_stem"])
            c = 1
            while new_name in used_names:
                new_name = f"{base}_{c}{ext}"
                c += 1
        used_names.add(new_name)
        try:
            data = z.read(old_path)
            out_z.writestr(new_name, data)
        except Exception:
            continue
        log_rows.append({
            "old_name": old_path,
            "new_name": new_name,
            "match_pct": m["score"],
        })
    out_z.close()
    out_zip.seek(0)
    # Return ZIP
    return StreamingResponse(
        out_zip,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=renamed-creatives.zip"},
    )


@app.post("/api/log")
async def get_log(
    zip_file: UploadFile = File(...),
    sheet: UploadFile = File(...),
    threshold: float = Form(0.7),
    sheet_name: Optional[str] = Form(None),
    column_header: Optional[str] = Form(None),
):
    """Same as preview but return CSV log content (so frontend can download as CSV)."""
    r = await preview(zip_file=zip_file, sheet=sheet, threshold=threshold, sheet_name=sheet_name, column_header=column_header)
    body = r.body
    import json
    data = json.loads(body)
    preview_list = data.get("preview", [])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Old Name", "New Name", "Match %"])
    for row in preview_list:
        new_name = (row.get("matched_name") or row.get("file_stem", "")) + (row.get("extension") or "")
        w.writerow([row.get("file_path", ""), new_name, row.get("score", "")])
    return JSONResponse({"csv": buf.getvalue()})


def _zip_name_to_hash(z: zipfile.ZipFile) -> dict[str, tuple[str, str]]:
    """Return dict: basename -> (path_in_zip, md5_hex). Skips directories."""
    out = {}
    for name in z.namelist():
        if name.endswith("/"):
            continue
        base = Path(name).name
        try:
            data = z.read(name)
        except Exception:
            continue
        h = hashlib.md5(data).hexdigest()
        out[base] = (name, h)
    return out


@app.post("/api/compare")
async def compare_zips(
    zip1: UploadFile = File(..., description="First ZIP (e.g. your updated ZIP)"),
    zip2: UploadFile = File(..., description="Second ZIP (e.g. tool output renamed ZIP)"),
):
    """
    Compare two ZIPs by filename (basename) and file content (MD5).
    Returns: only_in_1, only_in_2, same_content, different_content.
    """
    if not zip1.filename or not zip1.filename.lower().endswith(".zip"):
        raise HTTPException(400, "First file must be a ZIP.")
    if not zip2.filename or not zip2.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Second file must be a ZIP.")
    try:
        c1 = await zip1.read()
        c2 = await zip2.read()
        z1 = zipfile.ZipFile(io.BytesIO(c1), "r")
        z2 = zipfile.ZipFile(io.BytesIO(c2), "r")
    except Exception as e:
        raise HTTPException(400, f"Invalid ZIP: {e}")
    m1 = _zip_name_to_hash(z1)
    m2 = _zip_name_to_hash(z2)
    names1 = set(m1.keys())
    names2 = set(m2.keys())
    only_in_1 = sorted(names1 - names2)
    only_in_2 = sorted(names2 - names1)
    same_content = []
    different_content = []
    for n in sorted(names1 & names2):
        if m1[n][1] == m2[n][1]:
            same_content.append(n)
        else:
            different_content.append(n)
    return JSONResponse({
        "only_in_1": only_in_1,
        "only_in_2": only_in_2,
        "same_content": same_content,
        "different_content": different_content,
        "summary": {
            "only_in_1_count": len(only_in_1),
            "only_in_2_count": len(only_in_2),
            "same_content_count": len(same_content),
            "different_content_count": len(different_content),
        },
    })


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Ad Tag Tester ---
_ad_tag_cache: dict[str, str] = {}
MAX_CACHED_TAGS = 100


def _trim_cache():
    if len(_ad_tag_cache) > MAX_CACHED_TAGS:
        for _ in range(MAX_CACHED_TAGS // 4):
            k = next(iter(_ad_tag_cache), None)
            if k:
                del _ad_tag_cache[k]


@app.post("/api/ad-tag/preview")
async def ad_tag_preview(html: str = Form(...)):
    """Store HTML ad tag and return preview ID + test page URL."""
    html = (html or "").strip()
    if not html:
        raise HTTPException(400, "Please paste an HTML ad tag.")
    preview_id = str(uuid.uuid4()).replace("-", "")[:16]
    _ad_tag_cache[preview_id] = html
    _trim_cache()
    base = os.environ.get("BASE_URL", "").rstrip("/")
    test_url = f"{base}/test/{preview_id}" if base else f"/test/{preview_id}"
    return JSONResponse({"preview_id": preview_id, "test_page_url": test_url, "script": html})


@app.get("/test/{preview_id}", response_class=HTMLResponse)
def ad_tag_test_page(preview_id: str):
    """Serve HTML page that renders the ad tag in an iframe (sandboxed)."""
    html = _ad_tag_cache.get(preview_id)
    if not html:
        raise HTTPException(404, "Preview not found or expired.")
    wrapped = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><base target="_blank"></head>
<body style="margin:0;padding:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#1e293b;">
<div style="min-width:300px;min-height:250px;background:#fff;">
{html}
</div>
</body></html>"""
    return HTMLResponse(content=wrapped)


# --- HTML5 Ad Validator ---
IAB_MAX_INITIAL_LOAD_KB = 200
HTML5_ENTRY_POINTS = ("index.html", "index.htm")


@app.post("/api/html5/validate")
async def html5_validate(zip_file: UploadFile = File(...)):
    """Validate HTML5 ad creative ZIP structure."""
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Please upload an HTML5 creative ZIP.")
    content = await zip_file.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(content), "r")
    except Exception as e:
        raise HTTPException(400, f"Invalid ZIP: {e}")
    names = [n for n in z.namelist() if not n.endswith("/")]
    errors = []
    warnings = []
    # Check for index.html
    index_path = None
    for p in HTML5_ENTRY_POINTS:
        for n in names:
            if n.lower().endswith(p) or n.lower().rstrip("/").endswith(p):
                index_path = n
                break
        if index_path:
            break
    if not index_path:
        errors.append("Missing index.html or index.htm")
    # Check initial load size (index + critical assets - simplified: index + first 5 files)
    total_initial = 0
    for n in names[:20]:
        try:
            total_initial += len(z.read(n))
        except Exception:
            pass
    total_kb = total_initial / 1024
    if total_kb > IAB_MAX_INITIAL_LOAD_KB:
        warnings.append(f"Initial load ~{total_kb:.1f} KB exceeds IAB guideline (~{IAB_MAX_INITIAL_LOAD_KB} KB)")
    # File count
    file_count = len(names)
    # Build report
    return JSONResponse({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "file_count": file_count,
        "index_path": index_path,
        "initial_load_kb": round(total_kb, 1),
    })


# --- VAST Tag Tester ---
def _local_name(elem) -> str:
    """Get local tag name without namespace."""
    tag = elem.tag or ""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_vast(xml_text: str) -> dict:
    """Parse VAST XML and extract media URLs, impressions, etc."""
    root = ET.fromstring(xml_text)
    media_files = []
    impressions = []
    click_through = None
    for elem in root.iter():
        name = _local_name(elem)
        url = (elem.text or "").strip() if elem.text else ""
        if name == "MediaFile" and url.startswith("http"):
            attrs = elem.attrib if hasattr(elem, "attrib") else {}
            if not any(x["url"] == url for x in media_files):
                media_files.append({
                    "url": url,
                    "type": attrs.get("type", ""),
                    "width": attrs.get("width"),
                    "height": attrs.get("height"),
                })
        elif name == "Impression" and url.startswith("http"):
            if url not in impressions:
                impressions.append(url)
        elif name == "ClickThrough" and url.startswith("http"):
            click_through = click_through or url
    return {"media_files": media_files, "impressions": impressions, "click_through": click_through}


@app.post("/api/vast/preview")
async def vast_preview(vast_url: str = Form(...)):
    """Fetch VAST URL, parse XML, return structure for preview."""
    vast_url = (vast_url or "").strip()
    if not vast_url:
        raise HTTPException(400, "Please paste a VAST tag URL.")
    if not re.match(r"^https?://", vast_url, re.I):
        raise HTTPException(400, "VAST URL must start with http:// or https://")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            r = await client.get(vast_url)
            r.raise_for_status()
            xml_text = r.text
    except httpx.HTTPError as e:
        raise HTTPException(400, f"Failed to fetch VAST URL: {e}")
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch VAST URL: {e}")
    try:
        data = _parse_vast(xml_text)
    except ET.ParseError as e:
        raise HTTPException(400, f"Invalid VAST XML: {e}")
    return JSONResponse(data)
