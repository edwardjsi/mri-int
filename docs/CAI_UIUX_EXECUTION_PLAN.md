# CAI UI/UX Execution Plan (v1.1)

This execution plan operationalizes the **CAI UX Specification v1.1** to build the frontend interface for the deterministic decision engine.

## Core Directives
* **Strict Adherence:** Build exactly what is in the UX spec. No feature invention.
* **Deterministic UI:** Remove probabilistic language (e.g., "Confidence").
* **Design System:** Use the strict 5-color semantic palette (Green, Blue, Amber, Orange, Red) and 8px baseline grid with Tailwind CSS.
* **Presentation Only (State Management):** Continue using the application's existing state management solution. The frontend must consume a single normalized Decision ViewModel supplied by the API and perform zero business logic.
* **Reuse Infrastructure:** Use the platform's existing charting library for Fractal Analytics. Only the Decision Overlay is built by the CAI team.

---

## Sprint 1: Core OS (The Foundation)
*Focus on the primary workflows and data structures.*

1. **Routing & Layout Scaffold:**
   - Establish `/dashboard`, `/holdings`, and `/stock/:symbol` routes.
   - Implement the global Navigation (Dashboard, Holdings, Notifications).
2. **Portfolio Dashboard (Command Center):**
   - **Hero Section:** "Actions Today" KPI and Priority Card.
   - **Widgets:** Decision Distribution horizontal bar, Cash Available, and Market Regime pill.
3. **Holdings Table (The Ledger):**
   - Data Grid with strict default sorting: `QUIT -> STRUCTURE -> ALERT -> ADD -> MAINTAIN`.
   - Columns: Symbol, Decision Badge, Current Price, Next Add, Alert, Structure, Quit.
4. **Stock Detail & Decision Ladder:**
   - **Left Pane:** Header (with timestamp), Narrative Block (Why/Why Now/What Next), and Capital Allocation target.
   - **Right Pane (Decision Ladder):** Build the vertical timeline component with a dynamic floating "Current Price" marker.

---

## Sprint 2: Context & Validation
*Enhance the data visualization and ensure responsiveness.*

1. **Fractal Analytics (UI Overlay):**
   - Use the existing charting library. Do not build a custom chart.
   - Render horizontal threshold lines mapping to Add, Alert, Structure, and Quit levels over the existing data.
2. **Notifications View:**
   - Surface actionable deltas and historical state changes.
3. **Mobile Layout Adaptation:**
   - Convert Desktop split-panes and 3-column grids into single-column flexbox layouts for mobile touch optimization.

---

## Sprint 3: Polish & Resilience
*Finalize the user experience, accessibility, and edge cases.*

1. **State Management:**
   - **Empty States:** Build the "No actions required" success view.
   - **Loading States:** Implement skeleton loaders mimicking the exact data shape (no generic spinners).
   - **Error States:** Implement stale-data banners and reconnect logic.
2. **Accessibility (WCAG):**
   - Ensure color independence (badges must include text).
   - Add comprehensive `aria-labels`, specifically narrating the Decision Ladder sequence for screen readers.
3. **Micro-Interactions:**
   - Ensure all transitions are crisp and fast (150ms - 200ms). Absolutely no pulsing animations on the data grid.
