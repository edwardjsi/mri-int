# GuidanceCheck Email Enhancement — Mirror Screen Content
**Date:** 2026-06-17
**Owner:** Kimchi (executing on Immanuel's request)
**Trigger:** "in the conviction engine when a user selects the company, lot of details are shown in the screen but not sent to the email. I especially like the tone monitor and all the subsequent listings you made. can you send everything to the email?"

## Goal

Make the **GuidanceCheck email** mirror what's visible on the **GuidanceCheck screen**, so when a user clicks "📧 Send Report" they receive a faithful copy of what they were just looking at. Three screen sections are currently missing from the email:

1. 🎙️ **Management Tone (Intonation)** — 9-dimension tone monitor, headwinds named, tone shift chip, quarter-over-quarter deltas, tone trajectory over time
2. **Header metadata band** — transcript count + date range + promises extracted + numerical guidance % + dominant guidance type + DIRECTIONAL ONLY chip
3. **"No verified promises yet"** fallback warning — rendered when `total_verified == 0`

## Non-Goals

- **Do NOT touch the AAE forensic audit email** (`build_aae_report_email_html`). That is a separate flow from the StockDetailsModal "Run AAE Audit" button, with different content (master score, layers, bear/bull case). It is not what the user is describing.
- **Do NOT touch the AAE orchestrator / CredibilityEngine / GuidanceCheck React UI.** Only the email builder changes.
- **Do NOT change the payload** built by `api/guidance.py::_build_report_payload`. It already contains `intonation`, `transcript_count`, `numerical_guidance_pct`, `guidance_quality_signal`, `dominant_guidance_type`, `deadline_guidance_pct`, `all_future_promises`, `total_unable`, `directional_style`, `transcript_date_range`, `total_promises_extracted`. Confirmed at `api/guidance.py:469-528`.
- **Do NOT add any new dependencies.** Pure HTML string concatenation matching existing email conventions.

## Background — what's in the payload but not in the email

`_build_report_payload` (api/guidance.py) returns:
- `intonation` → `{ quarters_observed, latest{...9 dims, summary, headwinds_named}, previous{...}, quarter_over_quarter_delta, tone_shift_detected, tone_shift_dimensions[], timeline[{quarter_label, fy, fq, ...9 dims, headwind_acknowledged}] }`
- `transcript_count`, `transcript_date_range{earliest, latest}`
- `total_promises_extracted`, `numerical_guidance_pct`, `deadline_guidance_pct`, `dominant_guidance_type`
- `guidance_quality_signal` (DIRECTIONAL ONLY | MIXED | NUMERICAL)
- `all_future_promises`, `directional_style`, `total_unable`

`build_guidance_report_email_html` (engine_core/email_service.py:1428) currently reads only: `symbol`, `achieved`, `missed`, `partial`, `upcoming`, `total_verified`, `integrity_signal`, `quarter_comparison`, `integrity_timeline`, `report_date`, plus the narrative credibility override. None of the intonation or metadata-band fields are touched.

## Design — section ordering matches screen

The GuidanceCheck screen renders in this order (GuidanceCheck.tsx):
1. Verdict ring + counts + trend
2. **Header metadata band** (transcript count, date range, promises extracted, numerical %, dominant, DIRECTIONAL ONLY) — line 644
3. **Intonation** (quarter label + summary + headwinds + tone shift chip + 9-dim grid + delta arrows + tone trajectory sparkline) — line 675
4. Promise sections (✅ Kept, ❌ Broken, ⚠️ Partial, ⏳ Upcoming) — line 743-747
5. Conviction Timeline — line 749

The email will mirror this:
1. Header card (symbol + verdict chip + report date) — already in email
2. **NEW: header metadata band** (chips)
3. **NEW: intonation card** (full tone monitor + trajectory table)
4. ConvictionEngine credibility summary bar — already in email
5. Promise lists — already in email
6. Integrity signal — already in email
7. Quarter Comparison — already in email
8. Integrity Timeline — already in email
9. Footer — already in email

## Implementation

**File:** `engine_core/email_service.py`

**Three new helpers** (placed immediately before `build_guidance_report_email_html`, ~line 1427):

### 1. `_build_header_metadata_band(payload)` → str

Renders the chip strip matching `GuidanceCheck.tsx:644-672`. Conditional rendering — chips only show when their data is present.

```python
def _build_header_metadata_band(payload: dict) -> str:
    """Header chips strip: transcripts, promises extracted, numerical %, dominant, DIRECTIONAL ONLY."""
    chips = []
    tc = payload.get("transcript_count", 0)
    if tc > 0:
        rng = payload.get("transcript_date_range", {}) or {}
        earliest = rng.get("earliest")
        latest = rng.get("latest")
        date_span = ""
        if earliest and latest:
            date_span = ' <span style="color:#64748b;font-weight:400;margin-left:6px">· ' + str(earliest) + ' → ' + str(latest) + '</span>'
        chips.append(
            '<span style="background:#1e293b;color:#cbd5e1;padding:4px 10px;border-radius:14px;font-weight:600;font-size:0.72rem">'
            '📊 ' + str(tc) + ' transcript' + ('s' if tc != 1 else '') + ' analyzed' + date_span + '</span>'
        )

    tpe = payload.get("total_promises_extracted", 0)
    if tpe > 0:
        chips.append(
            '<span style="background:#1e293b;color:#cbd5e1;padding:4px 10px;border-radius:14px;font-weight:600;font-size:0.72rem">'
            + str(tpe) + ' promises extracted</span>'
        )

    num_pct = payload.get("numerical_guidance_pct", 0)
    if num_pct:
        bg = '#7f1d1d' if num_pct < 30 else '#451a03' if num_pct < 70 else '#14532d'
        fg = '#fca5a5' if num_pct < 30 else '#fbbf24' if num_pct < 70 else '#4ade80'
        chips.append(
            '<span style="background:' + bg + ';color:' + fg + ';padding:4px 10px;border-radius:14px;font-weight:600;font-size:0.72rem">'
            + str(round(num_pct, 1)) + '% numerical guidance</span>'
        )

    dom = payload.get("dominant_guidance_type")
    if dom:
        chips.append(
            '<span style="background:#1e293b;color:#94a3b8;padding:4px 10px;border-radius:14px;font-weight:600;font-size:0.72rem">'
            '🎯 Dominant: ' + str(dom) + '</span>'
        )

    if payload.get("guidance_quality_signal") == "DIRECTIONAL ONLY":
        chips.append(
            '<span style="background:#1e3a8a;color:#60a5fa;padding:4px 10px;border-radius:14px;font-weight:700;font-size:0.72rem;letter-spacing:0.04em">'
            '📐 DIRECTIONAL ONLY</span>'
        )

    if not chips:
        return ""
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px 0;font-size:0.72rem;align-items:center">'
        + ''.join(chips) +
        '</div>'
    )
```

### 2. `_build_intonation_email_section(intonation)` → str

Renders the tone monitor card. Mirrors `GuidanceCheck.tsx:675-742`.

**Latest-quarter card** (header row): quarter label + summary + headwinds named + tone-shift chip.

**9-dimension grid** — confidence / hedging / aggression / transparency / optimism / pessimism / accountability / numerical_density. Each row: label · value · Q-o-Q delta arrow (↑/↓) · thin progress bar colored per dimension.

**Tone trajectory table** — last 8 quarters as rows, confidence + hedging as columns. Renders as HTML table (email-safe; sparklines are React-only and won't render in plain-HTML email).

```python
def _build_intonation_email_section(intonation: dict) -> str:
    """Tone monitor card: latest-quarter summary + 9-dim grid + Q-o-Q deltas + 8-quarter trajectory."""
    if not intonation or intonation.get("quarters_observed", 0) < 1:
        return ""
    latest = intonation.get("latest") or {}
    if not latest:
        return ""
    previous = intonation.get("previous") or {}

    DIMS = [
        ("Confidence",         "confidence",        "#4ade80"),
        ("Hedging",            "hedging",           "#fbbf24"),
        ("Aggression",         "aggression",        "#f87171"),
        ("Transparency",       "transparency",      "#60a5fa"),
        ("Optimism",           "optimism",          "#4ade80"),
        ("Pessimism",          "pessimism",         "#94a3b8"),
        ("Accountability",     "accountability",    "#a78bfa"),
        ("Numerical density",  "numerical_density", "#22d3ee"),
    ]

    # ── Latest-quarter header row ────────────────────────────────
    q_label = latest.get("quarter_label", "")
    summary = latest.get("summary", "") or "—"
    headwinds = latest.get("headwinds_named") or []
    tone_shift = intonation.get("tone_shift_detected", False)

    headwinds_html = ""
    if headwinds:
        headwinds_html = (
            '<div style="font-size:0.72rem;color:#94a3b8;margin-top:6px">'
            '<b style="color:#fbbf24">Headwinds named:</b> '
            + ' · '.join(str(h) for h in headwinds) +
            '</div>'
        )

    shift_chip = ""
    if tone_shift:
        shift_chip = (
            '<div style="background:#1e3a8a;color:#60a5fa;padding:4px 10px;border-radius:12px;'
            'font-size:0.7rem;font-weight:700;letter-spacing:0.04em;white-space:nowrap;margin-left:auto">'
            '🚨 TONE SHIFT</div>'
        )

    # ── 9-dimension bar grid ─────────────────────────────────────
    dim_rows = ""
    for label, key, color in DIMS:
        v = float(latest.get(key, 0) or 0)
        pct = max(0, min(100, round(v * 100)))
        pv = float(previous.get(key, 0) or 0)
        delta = v - pv
        arrow = ""
        if delta > 0.01:
            arrow = ' <span style="color:' + color + '">↑</span>'
        elif delta < -0.01:
            arrow = ' <span style="color:' + color + '">↓</span>'
        dim_rows += (
            '<tr><td style="padding:3px 0;font-size:0.72rem;color:#94a3b8;width:42%">' + label + '</td>'
            '<td style="padding:3px 8px;width:18%"><div style="height:5px;background:#1f2937;border-radius:2px;overflow:hidden">'
            '<div style="height:100%;width:' + str(pct) + '%;background:' + color + '"></div></div></td>'
            '<td style="padding:3px 0;font-size:0.72rem;color:' + color + ';font-weight:700;text-align:right;width:40%">'
            + str(pct) + '%' + arrow + '</td></tr>'
        )

    dim_grid = (
        '<table style="width:100%;border-collapse:collapse;margin-top:12px">' + dim_rows + '</table>'
    )

    # ── Tone trajectory table (last 8 quarters, confidence + hedging) ──
    timeline = intonation.get("timeline", []) or []
    trajectory_html = ""
    if len(timeline) >= 2:
        rows = ""
        max_t = max((float(t.get("confidence", 0) or 0) for t in timeline), default=1) or 1
        for t in timeline[-8:]:
            ql = t.get("quarter_label", "")
            conf = float(t.get("confidence", 0) or 0)
            hedge = float(t.get("hedging", 0) or 0)
            conf_pct = round(conf * 100)
            hedge_pct = round(hedge * 100)
            bar_pct = round((conf / max_t) * 100) if max_t > 0 else 0
            bar_color = "#22c55e" if conf >= 0.7 else "#f59e0b" if conf >= 0.4 else "#ef4444"
            rows += (
                '<tr>'
                '<td style="padding:5px 8px;font-size:0.72rem;color:#94a3b8;font-weight:600;min-width:50px">' + str(ql) + '</td>'
                '<td style="padding:5px 8px"><div style="background:#1f2937;border-radius:3px;height:5px;width:100%">'
                '<div style="height:5px;border-radius:3px;background:' + bar_color + ';width:' + str(bar_pct) + '%"></div></div></td>'
                '<td style="padding:5px 8px;font-size:0.72rem;text-align:right;white-space:nowrap;color:#4ade80">'
                + str(conf_pct) + '%</td>'
                '<td style="padding:5px 8px;font-size:0.72rem;text-align:right;white-space:nowrap;color:#fbbf24">'
                + str(hedge_pct) + '%</td>'
                '</tr>'
            )
        trajectory_html = (
            '<div style="margin-top:14px;border-top:1px solid #1a2236;padding-top:10px">'
            '<div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;font-weight:700">'
            'Tone trajectory — confidence over time</div>'
            '<table style="width:100%;border-collapse:collapse"><thead>'
            '<tr style="color:#475569;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.06em">'
            '<th style="padding:2px 8px;text-align:left">Quarter</th>'
            '<th style="padding:2px 8px;text-align:left">Confidence</th>'
            '<th style="padding:2px 8px;text-align:right">Conf%</th>'
            '<th style="padding:2px 8px;text-align:right">Hedge%</th>'
            '</tr></thead><tbody>' + rows + '</tbody></table></div>'
        )

    return (
        '<div style="background:#0d1421;border:1px solid #1a2236;border-radius:10px;padding:16px 18px;margin:0 0 16px 0">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap">'
        '<div style="flex:1;min-width:200px">'
        '<div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:#94a3b8">'
        '🎙️ Management Tone — ' + str(q_label) + '</div>'
        '<div style="font-size:0.85rem;color:#cbd5e1;margin-top:4px;line-height:1.5">' + summary + '</div>'
        + headwinds_html +
        '</div>'
        + shift_chip +
        '</div>'
        + dim_grid
        + trajectory_html +
        '</div>'
    )
```

### 3. `_build_no_verified_promises_warning(payload)` → str

Renders the fallback panel from `GuidanceCheck.tsx:625-642`. Shown only when `total_verified == 0`.

```python
def _build_no_verified_promises_warning(payload: dict) -> str:
    """Fallback panel: when no promises are verified yet, explain the guidance-quality signal."""
    if payload.get("total_verified", 0) > 0:
        return ""
    total_unable = payload.get("total_unable", 0)
    upcoming_len = len(payload.get("upcoming", []) or [])
    if upcoming_len == 0 and total_unable == 0:
        return ""
    parts = []
    if total_unable > 0 or upcoming_len > 0:
        parts.append(
            '⏳ No verified promises yet — ' + str(total_unable) + ' of ' + str(upcoming_len)
            + " pending couldn't be matched to financials."
        )
    if payload.get("guidance_quality_signal") == "DIRECTIONAL ONLY":
        parts.append(
            '<div style="font-size:0.78rem;color:#fbbf24;margin-top:6px">'
            '⚠️ This management team gives directional / qualitative guidance only — they don\'t typically '
            'commit to numbers. Verification requires numeric targets.</div>'
        )
    if payload.get("all_future_promises") and payload.get("dominant_guidance_type"):
        parts.append(
            '<div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">'
            'Most-frequent topic: <b style="color:#cbd5e1">' + str(payload["dominant_guidance_type"])
            + '</b>. Future quarters will verify as results land.</div>'
        )
    if not parts:
        return ""
    return (
        '<div style="background:#0d1421;border:1px solid #1a2236;border-radius:10px;padding:14px 18px;margin:0 0 16px 0;color:#94a3b8;font-size:0.85rem">'
        '<div style="font-weight:600;color:#cbd5e1;margin-bottom:6px">' + parts[0] + '</div>'
        + ''.join(parts[1:]) +
        '</div>'
    )
```

### Wire the new helpers into `build_guidance_report_email_html`

In the `html_body` string assembly (~line 1654), insert the three new sections between the existing `<div ...></div>` (header card close) and the existing `summary_bar` (credibility summary bar).

Before:
```python
+ summary_bar  # ConvictionEngine credibility section
+ achieved_section + missed_section + partial_section + upcoming_section
```

After:
```python
+ _build_header_metadata_band(payload)  # NEW: chips strip
+ _build_intonation_email_section(payload.get("intonation", {}))  # NEW: tone monitor
+ _build_no_verified_promises_warning(payload)  # NEW: fallback panel (no-op when verified>0)
+ summary_bar  # ConvictionEngine credibility section
+ achieved_section + missed_section + partial_section + upcoming_section
```

The three new helpers return empty strings when their data is absent, so the email is unchanged for symbols that have no intonation / transcripts / verified promises. Fully backward-compatible.

## Verification

### Step 1: Offline render to HTML files
A one-off script `scripts/render_guidance_email.py` that:
1. Calls `api.guidance._build_report_payload(conn, symbol)` for CGCL, ASHOKA, and one fresh symbol (e.g. INFY or RELIANCE — known to have intonation data).
2. Calls `build_guidance_report_email_html(payload)`.
3. Writes the HTML to `outputs/guidance_email_<SYMBOL>.html` for inspection.

### Step 2: Structural assertions (no DB needed for the assertions themselves)
A unit test in `engine_core/test_guidance_email_sections.py` that:
1. Mocks a minimal payload with intonation, transcript_count, numerical_guidance_pct=20 (DIRECTIONAL).
2. Calls `build_guidance_report_email_html(payload)`.
3. Asserts the output contains:
   - `'🎙️ Management Tone'` (tone monitor rendered)
   - `'Confidence'` AND `'Hedging'` AND `'Accountability'` (all 9 dims, at least 3 spot-checked)
   - `'20.0% numerical guidance'` (metadata band chip)
   - `'📐 DIRECTIONAL ONLY'` (chip)
   - `'🚨 TONE SHIFT'` (when `tone_shift_detected=True`)
   - `'Tone trajectory'` (table rendered when timeline length ≥ 2)
4. Calls with `total_verified=0` payload → asserts `'No verified promises yet'` string is present.
5. Calls with empty `intonation={}` → asserts no tone monitor section (`'' in '🎙️ Management Tone'` is False).

### Step 3: Visual spot-check
Open `outputs/guidance_email_CGCL.html` in a browser and confirm:
- Header chips render with transcript count + promises extracted + numerical % + dominant + (if applicable) DIRECTIONAL ONLY
- Tone monitor card shows quarter label + summary + 8 dim bars + trajectory table
- Promise lists still render correctly
- No regressions in the credibility summary bar, quarter comparison, or integrity timeline

### Step 4: Regression check
- Existing `engine_guidance` tests (27) still pass.
- AAE orchestrator tests (24 across narrative + graveyard + debate) unaffected (different functions).

### Step 5: Sessions.md / Progress.md update + commit
- Append session entry to Sessions.md describing the work.
- Append progress entry to Progress.md.
- `git add` the modified files explicitly (per AGENTS.md) — `engine_core/email_service.py`, `engine_core/test_guidance_email_sections.py`, `scripts/render_guidance_email.py`, `Sessions.md`, `Progress.md`.
- Commit with descriptive message.
- Do NOT push (user said "i will check when you're done").

## Files Touched

| Path | Change |
|---|---|
| `engine_core/email_service.py` | Add 3 helpers + wire them into `build_guidance_report_email_html` |
| `engine_core/test_guidance_email_sections.py` | NEW: structural assertions for the new sections |
| `scripts/render_guidance_email.py` | NEW: offline renderer for visual spot-check |
| `Sessions.md` | Append session entry |
| `Progress.md` | Append progress entry |

## Risk

- **Low.** Pure HTML rendering. All helpers are pure functions of the payload. Empty data ⇒ empty output (no template noise). The existing email structure and styling are preserved.
- **Cost:** $0 LLM. No DB writes. No API changes. The `/api/guidance/{symbol}/email` route already passes the full payload.
- **Email size:** For symbols with rich intonation (8 quarters × 8 dims + promises), the HTML may grow ~3–5 KB. Acceptable — current emails are already 15–25 KB.

## Out of Scope

- AAE forensic audit email enrichment (`build_aae_report_email_html`) — separate flow, separate content.
- StockDetailsModal UI changes — not part of email flow.
- AAE Phase 4 master-score weighting (already uncommitted in working tree) — orthogonal.
- Frontend ConvictionEngine polish (Phase 6 of AAE plan) — orthogonal.
