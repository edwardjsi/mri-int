# Feature Request — Embedded Bear vs Bull Debate (always-visible report section)

**Date:** 2026-06-19
**Status:** DRAFT — awaiting user approval before execution
**Author:** Lead AI Engineer (Kimchi)
**Predecessor:** `docs/FEATURE_REQUEST_BEAR_BULL_DEBATE_2026-06-19.md` (modal-based debate engine)
**Closes:** The "debate as modal" UX gap from the first FeatureRequest

---

## Problem

The bear vs bull debate is currently a **modal that pops up on a button click**. The user's feedback is direct:

> "when we see the debate, then only the whole document makes better sense"
> "I want that to be part of the report itself"
> "I tried in Expansion lens and would like to see that it Conviction engine too"
> "when I email, I want that to be also in the email"

The modal pattern forces the user to:
1. Read 8 sections of the report (Bottom Line, Manager Track Record, Cross-Check, Category Breakdown, etc.)
2. THEN click a button and read the synthesis
3. THEN mentally integrate the synthesis with what they just read

This is backwards. The debate is the **synthesis of all the evidence above it** — it belongs *in the flow of the document*, not bolted on as a popup.

## Goal

Make the bear vs bull debate a **permanent, always-visible section** of:

1. **Expansion Lens per-symbol report** — between Bottom Line and Manager Track Record (synthesis before evidence details)
2. **Conviction Engine per-stock detail** — the StockDetailsModal opened when clicking a row in ConvictionEngine.tsx
3. **Expansion Lens + GuidanceCheck emails** — embedded in the HTML body, not just on the dashboard

Plus keep the **existing modal as a "regenerate / adjudicator" affordance** for users who want to force a fresh debate or include the adjudicator.

---

## Scope

### IN

1. **Auto-loaded debate section** in Expansion Lens report:
   - On report load, fetch the cached debate (instant if hit)
   - On cache miss, show skeleton for ~8s, then render the fresh debate
   - Rendered as a styled card stack (bear red, bull green) inline in the report
   - Modal button stays as "🔄 Regenerate / ⚖️ Include adjudicator"
2. **Auto-loaded debate section** in StockDetailsModal (Conviction Engine path):
   - Same lazy-load + cache pattern
   - Only renders when the modal is opened from ConvictionEngine context
3. **Debate section in email templates**:
   - `api/pe_expansion.py:_render_pe_expansion_email` — new "🗣️ Bear vs Bull" section before the disclaimer footer
   - `engine_core/email_service.py:_build_guidance_report_email_html` (or equivalent) — same for GuidanceCheck emails
   - Cache-aware: if cached, embed. If not cached, embed a small "Open in app to see live bear vs bull synthesis" placeholder (no auto-generation in email path — see cost rationale below)
4. **Shared `EmbeddedDebateSection` component** for both UI surfaces — same bear/bull card styling, same cached/lazy logic
5. **New API endpoint** `GET /api/guidance/{symbol}/debate` and `GET /api/pe-expansion/{symbol}/debate` (already exist as POST — add GET variant or refactor to accept both). The current endpoints are POST which is awkward for an auto-loaded section.
6. **Tests** for the auto-load logic + cache hit/miss + email rendering

### OUT

- **No real-time / streaming debates** — same on-demand + cache pattern
- **No auto-generation in emails on cache miss** — see Cost section below
- **No changes to the AAE V3 forensic debate** in `engine_fundamental/forensic_debate.py` — that's a separate lane
- **No new schema** — `conviction_debates` table is reused

---

## Design

### Auto-load UX (the key behavior)

```
Report loads
   ↓
GET /api/{kind}/{symbol}/debate (read-only, cached-first)
   ↓
Cache HIT (~500ms) → render immediately
   ↓
Cache MISS → show skeleton "Generating bear vs bull synthesis..."
            ↓
         background POST /api/{kind}/{symbol}/debate
            ↓
         ~8s later → render real bear/bull cards
```

The skeleton is a low-fidelity version (gray rectangles, "Loading..." text). The transition from skeleton to real content is smooth (no layout shift because cards have fixed dimensions).

### Where each section goes

**Expansion Lens report order (after this change):**
1. Sticky top nav (existing)
2. Universe list panel (existing)
3. Bottom Line (existing)
4. **🆕 Bear vs Bull section** (synthesis — right before evidence details)
5. Manager Track Record (existing)
6. What Other Checks Say (existing)
7. Header + PE Score (existing)
8. Top Drivers (existing)
9. Category Breakdown (existing)
10. Where the Signals Agree (existing)
11. Financial Quality 7-agent breakdown (existing)
12. Price Action 7-step (existing)
13. Primary Source — Promise Tracker (existing)
14. Secondary Source — Transcript Keyword Scan (existing)
15. Footer disclaimer (existing)

**Conviction Engine per-stock detail:**
- Inherits the same `<EmbeddedDebateSection>` component
- Appears at the top of the StockDetailsModal content, below the AAE summary block (the modal already calls `/api/aae/scan` — would also call `/api/guidance/{symbol}/debate`)

**Email body (both kinds):**
- 🆕 "🗣️ Bear vs Bull Debate" section, placed before the disclaimer footer
- Cache-aware: if cached, full bear/bull text + verdict (if adjudicator was included)
- Cache miss: shows "Open in app for live debate →" link to the dashboard

### Cost & Latency

| Path | Cost | Wall time | Notes |
|---|---|---|---|
| UI: cache hit | $0 | ~500ms | Instant |
| UI: cache miss (background) | ~$0.002 | ~8s | Skeleton shows during fetch |
| Email: cache hit | $0 | +50ms | Negligible |
| Email: cache miss | $0 (no auto-fetch) | 0ms | Shows "open in app" placeholder |
| One-time priming (149 symbols × 2 contexts) | ~$0.30 | ~3 min | Optional CLI backfill |

**Email cost rationale:** auto-generating a debate on every email-send to a new symbol would cost $0.002 per email × N emails × M new symbols. For a test-phase single user that's still cheap, but the principle is: emails should be a static snapshot of what's already in the system, not a side effect that triggers new LLM calls. The "open in app" placeholder handles this gracefully.

### API change

Current: `POST /api/{kind}/{symbol}/debate` (POST because it could mutate cache).

Proposed: `GET /api/{kind}/{symbol}/debate` for read-only cached retrieval (no LLM if cached, instant). `POST` stays for force-regenerate.

Implementation: same endpoint handler, accept both methods. The handler:
- If `cached_only=true` (or method=GET) → return cached if available, 204 No Content if miss
- If method=POST → run cache lookup; on miss, fire LLM; on hit, return cached

Actually simpler: just accept GET and have it return cached or 204. POST stays for force-regenerate.

### Shared component design

```tsx
// frontend/src/EmbeddedDebateSection.tsx
interface Props {
  symbol: string;
  contextKind: 'guidance' | 'pe_expansion';
  apiEndpoint: string;  // /api/guidance/{symbol}/debate or /api/pe-expansion/{symbol}/debate
}

export default function EmbeddedDebateSection({ symbol, contextKind, apiEndpoint }: Props) {
  const [data, setData] = useState<DebateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount: fetch cached. If miss, fire background fetch.
  useEffect(() => {
    // GET first (cached only, fast)
    apiFetch(apiEndpoint, { method: 'GET' })
      .then(setData)
      .catch(() => {
        // Cache miss → background POST to generate
        apiFetch(apiEndpoint, { method: 'POST' })
          .then(setData)
          .catch(setError)
          .finally(() => setLoading(false));
      })
      .finally(() => setLoading(false));
  }, [symbol, contextKind]);

  if (loading) return <DebateSkeleton />;
  if (error) return null; // silent fail — don't block the report
  if (!data) return null;
  return <DebateCards bear={data.bear} bull={data.bull} adjudicator={data.adjudicator} />;
}
```

The modal `DebateModal.tsx` becomes a *thicker* wrapper around the same data — uses POST to force-regenerate.

---

## Rollout Plan

### Phase 1 — GET endpoint + embedded section in Expansion Lens (smallest first slice)
- Add `GET /api/pe-expansion/{symbol}/debate` (read-only, cached or 204)
- Create `frontend/src/EmbeddedDebateSection.tsx`
- Wire into `frontend/src/PeExpansionReport.tsx` between Bottom Line and Manager Track Record
- Verify: cache-hit instant render + cache-miss background fetch + skeleton transition

### Phase 2 — Embedded section in StockDetailsModal (Conviction Engine path)
- Wire `EmbeddedDebateSection` into the modal opened from ConvictionEngine rows
- Verify: clicking a ConvictionEngine row shows the debate at the top of the modal

### Phase 3 — Email integration
- Add "Bear vs Bull" section to `_render_pe_expansion_email` in `api/pe_expansion.py`
- Add the same section to GuidanceCheck email template (wherever it lives — likely `engine_core/email_service.py`)
- Cache-aware: full content if cached, "open in app" placeholder if not
- Verify: email sent for POLYCAB (debate cached) shows bear/bull; email sent for fresh symbol shows placeholder

### Phase 4 — Tests + commit + push
- Unit tests for the auto-load logic (cached vs miss vs error)
- Verify email rendering with mocked debate data
- Full regression: existing 109 tests still pass
- 4 commits on `feature/embedded-debate`, single PR

---

## Open Questions for User

1. **Adjudicator in auto-load?** The auto-load uses the cached debate (which only has adjudicator if user previously opted in). Default proposal: **NO** — auto-load shows bear/bull only. Adjudicator requires explicit click on the modal.

2. **Email cost policy on cache miss?** Default proposal: **skip with "open in app" placeholder** (no auto-generation). Saves $0.002 per email for new symbols.

3. **Skeleton's visual style?** Default proposal: same dark theme with frosted gray rectangles + "Generating bear vs bull synthesis…" caption + a subtle progress shimmer.

4. **Embed depth — full verdict summary or just bear/bull?** Default proposal: **bear + bull cards only**. The action chip from Bottom Line ("Strong setup / Watch / Caution / Avoid") already serves as the verdict at the top of the report — duplicating it in the debate section would be noise.

---

**END OF FEATURE REQUEST — Awaiting user approval before Phase 1 execution.**
