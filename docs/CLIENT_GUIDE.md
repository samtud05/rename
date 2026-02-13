# CM360 Creative Renamer — User Guide for Clients

**Purpose:** This tool renames your creative files to match the exact CM360 creative names from your T-sheet (trafficking sheet), using smart matching so you don’t have to rename hundreds of files by hand.

---

## How to Access

- **Link:** [https://rename-vm3h.onrender.com](https://rename-vm3h.onrender.com)
- **No login required** — open the link and use the tool.
- **First visit:** On the free hosting plan, the first load can take 30–60 seconds. Please wait for the page to appear; later visits are faster.

---

## How the Page Looks

The screen is divided into clear sections:

1. **Header**  
   - Title: **CM360 Creative Renamer**  
   - Short line explaining: upload ZIP + T-sheet → preview → download.

2. **Section 1 — Upload files**  
   - Two upload areas side by side:
     - **Creatives (ZIP)** — choose your ZIP containing all creative assets (images, videos, HTML, etc.).
     - **T-sheet (Excel / CSV)** — choose your trafficking sheet (Excel `.xlsx` or CSV) that has the final CM360 creative names.
   - After selecting, the name of each chosen file is shown under its area.

3. **Section 2 — Confidence threshold**  
   - A slider (e.g. 50% to 95%), default **70%**.  
   - Short note: matches below this % are still suggested but flagged for review in the preview.

4. **Section 3 — Preview & download**  
   - Three buttons:
     - **Preview mapping** — see how each file will be renamed before downloading.
     - **Download renamed ZIP** — get a new ZIP with all creatives renamed to the CM360 names (file type, e.g. .jpg, is kept).
     - **Download CSV log** — get a spreadsheet log: Original filename → New filename → Match %.

5. **Preview table (after you click “Preview mapping”)**  
   - A table with columns: **Original file**, **New name**, **Match %**.  
   - Rows with match % below your threshold are highlighted (e.g. in red) so you can quickly spot items to review.  
   - A short summary line shows: number of files, number of names in the sheet, how many are above/below the threshold.

6. **Messages**  
   - If something goes wrong (e.g. missing file, invalid sheet), a short error message appears in red under the buttons.

---

## How to Use It (Step by Step)

| Step | What you do |
|------|-------------|
| 1 | Open the link and wait for the page to load. |
| 2 | Click **Creatives (ZIP)** and select the ZIP that contains all your creative files. |
| 3 | Click **T-sheet (Excel / CSV)** and select your trafficking sheet (Excel or CSV with the CM360 creative names). |
| 4 | (Optional) Move the **Confidence threshold** slider if you want to be stricter (e.g. 80%) or more relaxed (e.g. 60%). |
| 5 | Click **Preview mapping** to see, for each file, the suggested new name and match %. Check the table; low-% rows are highlighted for review. |
| 6 | When satisfied, click **Download renamed ZIP** to get the ZIP with renamed creatives, or **Download CSV log** to get the mapping report (Original name, New name, Match %). You can use both. |

**Notes:**

- The tool finds the “CM360 Creative Name” column in your sheet automatically when possible (e.g. by header text or a column that looks like those names).  
- File extensions (e.g. .jpg, .mp4) are always preserved.  
- You can run the tool as many times as you need for different packs or sheets.

---

## What You Get

- **Renamed creatives ZIP**  
  Same files as in your upload, but filenames replaced with the matched CM360 names from the T-sheet. Ready to use in CM360.

- **CSV log**  
  One row per file: **Old name**, **New name**, **Match %**. Useful for records and checking low-confidence matches.

---

## Quick Reference

| Item | Detail |
|------|--------|
| **Tool name** | CM360 Creative Renamer |
| **URL** | https://rename-vm3h.onrender.com |
| **Input** | One ZIP (creatives) + one T-sheet (Excel or CSV) |
| **Output** | Renamed creatives ZIP + optional CSV log |
| **Login** | Not required |
| **Support** | Contact your account team for questions or issues |

---

*This guide describes the current UI and workflow. If the link or layout changes slightly, your team will be notified.*
