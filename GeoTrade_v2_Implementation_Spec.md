# GeoTrade v2.0 — Full Frontend Implementation Specification

> **Revised Edition.** Incorporates all structural changes: Portfolio removed, Monte Carlo
> folded into Markets, 3D globe moved to Dashboard center, Supply Chain rebuilt on 2D
> Leaflet world map, Auth pages added. This document is the single source of truth for
> frontend implementation.

---

## 0. Design System Tokens

These tokens are defined once in `src/styles/tokens.css` and imported globally.
Every component references only these variables — no hardcoded hex values anywhere
in component files.

```css
:root {
  /* Backgrounds */
  --bg-base:        #0a0b0d;
  --bg-surface:     #111318;
  --bg-elevated:    #1a1d24;
  --bg-hover:       #22262f;

  /* Borders */
  --border:         #1f2330;
  --border-bright:  #2d3344;

  /* Text */
  --text-primary:   #e8ecf0;
  --text-secondary: #7d8799;
  --text-muted:     #4a5265;

  /* Accents */
  --accent-green:   #00ff88;
  --accent-cyan:    #06b6d4;
  --accent-amber:   #f59e0b;
  --accent-red:     #ef4444;
  --accent-purple:  #a78bfa;

  /* Risk tiers */
  --risk-critical:  #ef4444;   /* score >= 80 */
  --risk-high:      #f59e0b;   /* score >= 60 */
  --risk-medium:    #06b6d4;   /* score >= 35 */
  --risk-low:       #22c55e;   /* score < 35  */

  /* Typography */
  --font-display:  'Space Grotesk', sans-serif;
  --font-mono:     'JetBrains Mono', monospace;

  /* Type scale */
  --text-xs:    10px;   /* uppercase labels, eyebrows — letter-spacing 0.08em */
  --text-sm:    12px;   /* timestamps, meta */
  --text-base:  14px;   /* body, table rows */
  --text-md:    16px;   /* card titles */
  --text-lg:    20px;   /* section headers */
  --text-xl:    28px;   /* GTI score, asset price */
  --text-2xl:   42px;   /* hero headline */

  /* Spacing */
  --gap-xs:  4px;
  --gap-sm:  8px;
  --gap-md:  16px;
  --gap-lg:  24px;
  --gap-xl:  40px;

  /* Radius */
  --radius-sm:  4px;
  --radius-md:  6px;
  --radius-lg:  10px;

  /* Motion */
  --ease-snap:      cubic-bezier(0.16, 1, 0.3, 1);
  --transition-fast: 150ms;
  --transition-panel: 300ms;
}
```

**Font loading** — in `index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
```

**Risk color helper** — `src/utils/risk.ts`:
```ts
export function riskColor(score: number): string {
  if (score >= 80) return 'var(--risk-critical)';
  if (score >= 60) return 'var(--risk-high)';
  if (score >= 35) return 'var(--risk-medium)';
  return 'var(--risk-low)';
}

export function riskLabel(score: number): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 35) return 'MEDIUM';
  return 'LOW';
}
```

---

## 1. Project Structure

```
src/
  components/
    shell/
      Navigation.tsx        ← top bar, always rendered
      StatusBar.tsx         ← bottom ticker, always rendered
    ui/
      SignalPill.tsx         ← BUY/SELL/HOLD pill
      SeverityBadge.tsx     ← CRITICAL/HIGH/MEDIUM/LOW badge
      ConfidenceBar.tsx     ← label + progress bar + %
      LiveDot.tsx           ← pulsing green dot
      StatCard.tsx          ← dark surface metric card
      CandlestickChart.tsx  ← recharts ComposedChart wrapper
      RiskGauge.tsx         ← SVG arc gauge for GTI
      Sparkline.tsx         ← inline mini recharts AreaChart
  pages/
    auth/
      Login.tsx
      ForgotPassword.tsx
      ResetPassword.tsx
      RequestAccess.tsx
    Website.tsx
    Dashboard.tsx
    Map.tsx
    Markets.tsx
    Signals.tsx
    SupplyChain.tsx
    AiChat.tsx
  context/
    AuthContext.tsx          ← session state, login/logout
    WebSocketContext.tsx     ← single WSS connection, dispatch
  hooks/
    useGTI.ts               ← subscribes to gti_update messages
    useSignals.ts           ← subscribes to signal_update messages
    useAlerts.ts            ← subscribes to event_alert messages
  utils/
    risk.ts                 ← riskColor, riskLabel helpers
    format.ts               ← mono number formatting helpers
  styles/
    tokens.css
    global.css
  router/
    index.tsx               ← route definitions + auth guard
  App.tsx
  main.tsx
```

---

## 2. Router & Auth Guard

**File:** `src/router/index.tsx`

```tsx
const publicRoutes = ['/', '/auth/login', '/auth/forgot-password',
                      '/auth/reset-password', '/auth/request-access'];

function AuthGuard({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) {
    return <Navigate to={`/auth/login?redirect=${location.pathname}`} replace />;
  }
  return <>{children}</>;
}

// Route tree
<Routes>
  <Route path="/"                        element={<Website />} />
  <Route path="/auth/login"              element={<Login />} />
  <Route path="/auth/forgot-password"    element={<ForgotPassword />} />
  <Route path="/auth/reset-password"     element={<ResetPassword />} />
  <Route path="/auth/request-access"     element={<RequestAccess />} />

  <Route element={<AuthGuard><AppShell /></AuthGuard>}>
    <Route path="/dashboard"     element={<Dashboard />} />
    <Route path="/map"           element={<Map />} />
    <Route path="/markets"       element={<Markets />} />
    <Route path="/signals"       element={<Signals />} />
    <Route path="/supply-chain"  element={<SupplyChain />} />
    <Route path="/chat"          element={<AiChat />} />
  </Route>
</Routes>
```

`AppShell` renders `<Navigation />` + `<Outlet />` + `<StatusBar />`.
Auth pages render standalone — no shell.

---

## 3. WebSocket Context

**File:** `src/context/WebSocketContext.tsx`

Single persistent connection. All pages subscribe via hooks — nothing polls REST
when WebSocket data is sufficient.

```ts
type LiveRiskMessage =
  | { type: 'gti_update';    gti: number; delta: number; trend: number[] }
  | { type: 'risk_update';   country_id: string; risk_score: number }
  | { type: 'event_alert';   event: GeopoliticalEvent }
  | { type: 'signal_update'; signal: TradingSignal }

// Connection lifecycle
// 1. Open on mount of WebSocketContext provider (wraps AuthGuard children)
// 2. Exponential backoff reconnect: 1s → 2s → 4s → 8s → 16s → cap 30s
// 3. Dispatch all messages to a Map of listeners keyed by message type
// 4. Expose: { status: 'connected'|'reconnecting'|'disconnected', feedCount, subscribe, unsubscribe }

// Per-message throttle: each listener is called at most once per 250ms.
// Buffer the latest message of each type; flush on interval.
// This prevents UI thrash during high-frequency crisis events.
```

**Hook pattern used by pages:**
```ts
// src/hooks/useGTI.ts
export function useGTI() {
  const [gti, setGTI] = useState<GTIState | null>(null);
  const { subscribe, unsubscribe } = useWebSocket();
  useEffect(() => {
    const id = subscribe('gti_update', (msg) => setGTI(msg));
    return () => unsubscribe(id);
  }, []);
  return gti;
}
```

---

## 4. Shell Components

### 4.1 Navigation.tsx

**Height:** 56px fixed top. `background: var(--bg-base)`, `border-bottom: 1px solid var(--border)`.

**Responsive breakpoint behavior:**
- `>= 1280px` — full single-row layout as described below
- `960–1279px` — GTI readout collapses to score only (no label, no delta text, badge remains)
- `< 960px` — GTI readout hidden; nav tabs collapse to icon-only; clock hidden

**Left cluster (flex row, gap 24px):**

1. **Logo lockup**
   - Waveform SVG icon, 15×15px, `var(--accent-green)`
   - "GEOTRADE" — Space Grotesk 700, 13px, `var(--text-primary)`
   - "TRADER V2.0" — 10px, `var(--text-muted)`, below the wordmark

2. **GTI readout** (fed by `useGTI()` hook)
   - Label: "GLOBAL TENSION INDEX" — 10px uppercase, `var(--text-muted)`, letter-spacing 0.08em
   - Score: JetBrains Mono, 28px, color = `riskColor(gti.score)` — animates on change with
     800ms count-up transition
   - Delta: "+2.1 ↗" — 12px, green if positive, red if negative
   - Badge pill: `riskLabel(gti.score)` — `var(--accent-amber)` background at 20% opacity,
     `var(--accent-amber)` text, 10px uppercase, 4px 8px padding, `var(--radius-sm)`

**Center cluster — nav tabs:**

```
DASHBOARD  ·  MAP  ·  MARKETS  ·  SIGNALS  ·  SUPPLY CHAIN  ·  CHAT
```

Each tab: Space Grotesk 13px, `var(--text-secondary)` default.
Active state: `var(--text-primary)` + 2px bottom border `var(--accent-cyan)`.
Prefix icon (Lucide, 14px): LayoutDashboard · Globe · BarChart2 · Zap · Network · MessageSquare.
Keyboard shortcut suffix in `var(--text-muted)`: `D` · `M` · `K` · `S` · `L` · `C`
(activated with `Alt+letter`; handled in a global `keydown` listener in `Navigation.tsx`).

**Right cluster (flex row, gap 16px):**

1. **Live indicator** (from WebSocket status)
   - `<LiveDot />` (pulsing green) + "LIVE · {feedCount} FEEDS" when connected
   - Amber static dot + "RECONNECTING..." when dropped
   - Red static dot + "OFFLINE" when disconnected > 10s

2. **UTC clock** — JetBrains Mono 13px, `var(--text-secondary)`, updates every second via
   `setInterval`. Format: `HH:MM:SS UTC`

3. **User avatar pill** — circular initials badge (first+last initial), `var(--bg-elevated)` bg,
   `var(--border-bright)` border, `var(--accent-cyan)` text. Click opens dropdown:
   - Account settings
   - API keys
   - Sign out (calls `DELETE /auth/session` + clears context)

**API calls:** `GET /auth/me` on mount. GTI via `useGTI()` hook.

---

### 4.2 StatusBar.tsx

**Height:** 48px fixed bottom. `background: var(--bg-elevated)`, `border-top: 1px solid var(--border)`.

Three zones in a flex row:

**Left zone (200px fixed):**
- "GTI TREND" label — 10px uppercase, `var(--text-muted)`
- Current score — JetBrains Mono 13px, `riskColor(score)`
- 12 small squares (8×8px each, 4px gap) representing the last 12 hours of GTI readings.
  Each square filled with `riskColor(hourlyScore)`. Tooltip on hover shows "HH:00 — score X".

**Center zone (flex 1):**
- Horizontally scrolling strip of alert cards. Auto-scroll at 40px/s. Pauses on hover.
- Each alert card (inline-flex, 280px wide, `var(--bg-surface)`, `var(--radius-sm)`, margin-right 12px):
  - 3px left border colored by severity (red=CRITICAL, amber=HIGH)
  - Event title — 13px, `var(--text-primary)`, max 30 chars truncated with ellipsis
  - Region tag — 11px, `var(--text-muted)`
  - Severity badge — `<SeverityBadge />`
  - Timestamp — JetBrains Mono 11px, `var(--text-muted)`, right-aligned
- Clicking an alert card navigates to `/map?country={country_id}` and opens the event detail.

**Right zone (120px fixed):**
- "▲ {N} ACTIVE" button — 11px, `var(--accent-amber)`, opens full alert drawer overlay.

**API:** `WSS /ws/live-risk` (gti_update, event_alert). `GET /events/high-severity?min_severity=7`
on mount to seed the ticker before WebSocket events start flowing.

---

## 5. Auth Pages

### 5.1 Login.tsx

**Route:** `/auth/login`
**Layout:** Two-panel, full viewport height, no shell.

```
┌─────────────────────┬──────────────────────────────┐
│   LEFT PANEL        │   RIGHT PANEL                │
│   (440px fixed)     │   (flex 1)                   │
│                     │                              │
│   Auth form         │   Live platform preview      │
│                     │   (read-only, blurred 20%)   │
└─────────────────────┴──────────────────────────────┘
```

**Left panel** — `background: var(--bg-surface)`, `border-right: 1px solid var(--border)`, padding 48px:

1. Logo lockup (same as nav, but 16px wordmark)
2. Heading: "Sign in to your account" — Space Grotesk 700, 24px, `var(--text-primary)`, margin-top 48px
3. Subhead: "Access live geopolitical signals and market intelligence." — 14px, `var(--text-secondary)`

4. **Form** (margin-top 32px, flex column, gap 16px):
   - Email field — full width, label "EMAIL" (10px uppercase), input with placeholder "analyst@firm.com"
   - Password field — label "PASSWORD", input type=password, right-slotted eye toggle icon
   - "Forgot password?" — 12px link, `var(--accent-cyan)`, right-aligned, links to `/auth/forgot-password`
   - "SIGN IN" button — full width, 48px height, `var(--bg-hover)` background,
     `var(--accent-green)` border + text, Space Grotesk 700 13px uppercase.
     Loading state: spinner replaces text, button disabled.
   - Error state: red 1px border on offending field + 12px red error message below field.

5. Divider line with "OR" centered — `var(--border)` color

6. "Don't have access? →" link to `/auth/request-access` — 13px, `var(--text-secondary)`,
   hover underline

**Right panel** — `background: var(--bg-base)`, overflow hidden, position relative:
- Full-height blurred Dashboard screenshot or live iframe at 20% opacity (use `filter: blur(2px) brightness(0.6)`)
- Overlaid glass card (centered, 320px wide, `var(--bg-elevated)` at 90% opacity,
  `var(--border-bright)` border, `var(--radius-lg)`, padding 24px):
  - "LIVE PLATFORM PREVIEW" eyebrow — 10px uppercase, `var(--accent-cyan)`
  - Current GTI score (real API call, `GET /risk/gti` — no auth required for this endpoint)
  - 3 most recent signal cards in compact format (symbol + direction pill + confidence %)
  - `<LiveDot />` + "Updated live" — 12px, `var(--text-muted)`

**API:** `POST /auth/login` → `{ email, password }` → `{ token, user }`. Store token in
`httpOnly` cookie (server-side) or `localStorage` as fallback. On success, redirect to
`?redirect` param or `/dashboard`.

---

### 5.2 ForgotPassword.tsx

**Route:** `/auth/forgot-password`
**Layout:** Centered single card on `var(--bg-base)`, 440px wide, no right panel.

- Logo at top
- Heading: "Reset your password"
- Body: "Enter your email and we'll send a reset link if an account exists."
- Email field + "SEND RESET LINK" button
- Success state: green checkmark icon + "Check your inbox" message — email field hidden
- "Back to sign in" link below

**API:** `POST /auth/forgot-password` → `{ email }`. Always returns 200 (security — no user enumeration).

---

### 5.3 ResetPassword.tsx

**Route:** `/auth/reset-password?token=...`

On mount: validate token via `GET /auth/validate-reset-token?token=...`.
If invalid/expired: show error card with "Request a new link" button.
If valid: show form.

- New password field with strength indicator (4-segment bar: weak/fair/strong/very strong)
- Confirm password field
- "SET NEW PASSWORD" button
- On success: redirect to `/auth/login` with success toast

**API:** `POST /auth/reset-password` → `{ token, password }`.

---

### 5.4 RequestAccess.tsx

**Route:** `/auth/request-access`
**Layout:** Same centered card pattern as ForgotPassword, but taller.

- Heading: "Request platform access"
- Subhead: "GeoTrade is currently invite-only. We review applications within 48 hours."
- Form fields:
  - Full name
  - Work email
  - Firm / organization
  - Role (dropdown: Trader · Analyst · Portfolio Manager · Researcher · Other)
  - "How did you hear about us?" (optional textarea, 2 rows)
- "SUBMIT REQUEST" button
- Success state: confirmation message + expected timeline

**API:** `POST /auth/request-access` → `{ name, email, firm, role, referral? }`.

---

## 6. Page A — Website.tsx (Public Landing)

**Route:** `/` — no auth required, no shell rendered.

### Section 1: Hero (100vh)

**Background:** CSS-only animated SVG globe (not Three.js — too heavy for unauthenticated users).
Build a simplified SVG globe with animated longitude/latitude grid lines in `var(--accent-cyan)` at
5% opacity. Add 3–4 arc paths animated with `stroke-dashoffset` to simulate signal arcs.
Overlay a gradient from transparent to `var(--bg-base)` at the bottom 40% of the section.

**Floating annotation chips** (absolute positioned, glass panel style):
- Top-left: "● LIVE SYSTEM ACTIVE" — green dot + text
- Top-right: last 3 real signal outcomes pulled from `GET /signals/recent-outcomes?limit=3`:
  format "GOLD +4.2% · 48h" — proves real performance, not decorative

**Headline** (centered, max-width 800px):
```
Trade the
Geopolitical Edge
```
"Geopolitical" on its own line in `var(--accent-cyan)`, weight 800, 72px.
"Trade the" and "Edge" in `var(--text-primary)`, weight 700, 64px.

**Subhead:** "GeoTrade v2.0 monitors live global events, computes the Global Tension Index,
and generates AI trading signals before the market reacts." — 16px, `var(--text-secondary)`,
max-width 520px, centered.

**CTA row** (gap 16px, centered):
- "LAUNCH PLATFORM →" — `var(--text-primary)` background (white), `var(--bg-base)` text,
  Space Grotesk 700 14px uppercase, 48px height, links to `/auth/login`
- "HOW IT WORKS" — `var(--bg-elevated)` background, `var(--border-bright)` border,
  `var(--text-primary)` text, links to `#how-it-works` anchor

### Section 2: Live Signal Ticker (conversion hook)

Full-width strip, `var(--bg-surface)`, 64px height. No auth required.
`GET /signals/public-preview?limit=5` — returns 5 recent signals (direction, asset, outcome, elapsed).

Horizontal scrolling row of signal cards:
- Symbol bold + `<SignalPill />` + "→ +3.8% in 36h" outcome chip in green
- "LIVE SIGNALS" eyebrow left + "Updated 23s ago" right
- This is the primary trust signal on the page.

### Section 3: Feature Highlights (3 columns, `#how-it-works`)

Each column: 40px Lucide icon in `var(--accent-cyan)`, 16px bold title, 14px `var(--text-secondary)` body.

1. **Know before the market does**
   - "Monitors Reuters, GDELT, BBC, NewsAPI, Finnhub, Al Jazeera in real time. Events are
     scored, clustered, and ranked by market impact within seconds."

2. **Direction, entry, and exit — not just signals**
   - "Every signal includes entry price, stop loss, target, risk:reward ratio, and position
     sizing — generated by a CNN-BiGRU-Attention ensemble trained on 8 years of event-market data."

3. **Understand why, not just what**
   - "Each signal links back to the exact events that triggered it. Ask the AI Analyst to
     explain any signal in natural language, explore scenarios, and model alternatives."

### Section 4: GTI Live Widget (narrow banner)

Full-width, `var(--bg-surface)`, padding 24px. Real data.
- Left: "GLOBAL TENSION INDEX" label + current score in 48px mono colored by risk
- Center: 30-point sparkline (recharts AreaChart, 200×48px, `var(--accent-amber)` fill)
- Right: Risk level badge + "Updated live via WebSocket" in 12px `var(--text-muted)`

**API:** `GET /risk/gti`, `GET /risk/gti/history?limit=30` — both must be public (no auth).

### Section 5: CTA footer strip

Dark strip, centered: "Ready to trade the geopolitical edge?" + "REQUEST ACCESS" button.

---

## 7. Page B — Dashboard.tsx (War Room)

**Route:** `/dashboard`

### Layout: 3-column grid

```
┌─────────────┬──────────────────────────────┬──────────────┐
│ LEFT        │ CENTER                       │ RIGHT        │
│ 240px       │ flex 1                       │ 320px        │
│             │                              │              │
│ GTI Deep    │ [Tickers strip — 64px]       │ Live Signals │
│ Dive        │ [3D Globe — ~520px]          │ Rail         │
│             │ [Alert panel — remainder]    │              │
└─────────────┴──────────────────────────────┴──────────────┘
```

At `< 1440px`: right rail collapses to a slide-over drawer, toggled by a "SIGNALS →" button
that appears at the top-right of the center column.

### Left Column — GTI Deep Dive

**GTI Circle Gauge** (`<RiskGauge />`)
- SVG arc, 200px diameter, stroke-width 12
- Background track: `var(--border)`
- Filled arc: `riskColor(gti.score)`, sweeps from 7 o'clock to score position (270° total arc)
- Center: score in 48px JetBrains Mono, `riskColor(gti.score)`, below it risk label in 12px uppercase
- On GTI update: arc animates over 600ms using `stroke-dashoffset` transition

**Risk Level Breakdown** (below gauge, margin-top 24px)
```
CRITICAL    ██ 12 countries    [red]
HIGH        ████ 28 countries  [amber]
MEDIUM      ███ 19 countries   [cyan]
LOW         █████ 43 countries [green]
```
Each row: color dot (8px) + label (10px uppercase `var(--text-muted)`) + count (13px mono `var(--text-primary)`) + thin bar.

**30-day GTI Sparkline**
- "GTI TREND" eyebrow — 10px uppercase `var(--text-muted)`
- recharts `AreaChart`, 200×80px, no axes, no tooltip
- `var(--accent-amber)` stroke, `var(--accent-amber)` fill at 0.15 opacity
- Fed by `GET /risk/gti/history?limit=30`

**Time since last update** — "Updated 12s ago" in 11px `var(--text-muted)`, count-up timer,
resets to 0 on each `gti_update` WebSocket event.

### Center Column — War Room

**Market Tickers Strip** (64px height, `var(--bg-surface)`, `border-bottom: 1px solid var(--border)`)

Horizontally scrollable row of asset ticker cards. Default shows 4 pinned assets.
Each card (140px wide, padding 8px 12px):
- Symbol: 13px mono bold, `var(--text-primary)`
- Price: 18px mono, `var(--text-primary)`
- Delta %: 12px, green if positive / red if negative
- Mini sparkline: 60×20px inline recharts LineChart

"✎ CUSTOMIZE" button at far right — opens a small dropdown picker (checkboxes for all 38
assets, max 6 pinned at once).

**3D Globe** (Three.js, WebGL)

Full width of center column, approximately 520px tall.
- Background: `#0a0e1a` (dark ocean)
- Country mesh: colored by `riskColor(country.risk_score)` from `GET /risk/globe`
- Country borders: `var(--accent-cyan)` at 8% opacity
- Arc lines between countries with `risk_score >= 70`: animated arcs, `var(--risk-critical)`
  at 60% opacity, 2px width, traveling dot animation along arc
- Globe auto-rotates at 0.2°/s when idle. Rotation stops on first mouse interaction,
  resumes 8s after last interaction.
- **Hover**: country mesh brightens by 30%, tooltip appears (country name + risk score +
  top event title snippet). Tooltip: `var(--bg-elevated)` panel, `var(--border-bright)` border,
  `var(--radius-md)`, 12px text.
- **Click**: does NOT open a panel. Navigates to `/map?country={iso3}&view=2d`.
  Before navigating, show a 200ms "flash" highlight on the clicked country (glow effect).

**Performance notes for Three.js:**
- Use `requestAnimationFrame` with delta-time for rotation to decouple from frame rate
- Dispose all geometries and materials on component unmount
- Cap renderer pixel ratio at `Math.min(window.devicePixelRatio, 2)`
- Check `navigator.hardwareConcurrency < 4` → fall back to 2D `<MapContainer>` (Leaflet)
  with same country coloring. Show "3D globe unavailable on this device" notice.

**Critical Alerts Panel** (below globe)

Header row: "⚠ CRITICAL ALERTS" — 10px uppercase `var(--text-primary)` + count badge
+ "LAST UPDATED {time}" right-aligned.

Alert cards (stacked, gap 8px):
- `var(--bg-surface)` background, `var(--radius-md)`, overflow hidden
- 3px left border: red for CRITICAL, amber for HIGH
- **Row 1:** Event title — 14px bold `var(--text-primary)` (max 2 lines, line-clamp)
- **Row 2:** Region pill + `<SeverityBadge />` + timestamp JetBrains Mono 11px right-aligned
- **Row 3:** Description — 12px `var(--text-secondary)`, max 2 lines
- **Row 4:** Affected asset chips (e.g. "XAUUSD", "BRENT") — 10px uppercase, `var(--bg-elevated)`,
  `var(--border)` border, `var(--radius-sm)`, 4px 8px padding

Empty state: shield icon (Lucide `ShieldCheck`) + "No critical events in current window" +
"All monitored regions within normal parameters" — centered, `var(--text-muted)`.

**API:** `GET /events/high-severity?min_severity=7` on mount. `event_alert` WebSocket messages
prepend new cards with a subtle slide-in animation.

### Right Column — Live Signals Rail

Header: "LIVE SIGNALS" — 13px bold `var(--text-primary)` + `<LiveDot />`.
"← HIDE" button collapses rail below 1440px.

**Featured Signal Card** (top, `var(--bg-surface)`, `var(--radius-lg)`, padding 16px,
`border: 1px solid var(--border-bright)`):
- Asset symbol — 16px mono bold + `<SignalPill />` (large, 13px)
- Current price — 20px mono `var(--text-primary)`
- `<ConfidenceBar label="Confidence" />` — green progress bar
- `<ConfidenceBar label="Uncertainty" color="amber" />` — amber progress bar
- "AI ANALYSIS" eyebrow + 3–4 line text summary — 12px `var(--text-secondary)`, line-height 1.6
- "VIEW DETAILS →" link to `/markets?asset={symbol}` — 11px `var(--accent-cyan)`

**Signal List** (below featured, scrollable):
- "ALL SIGNALS ({N})" header — 10px uppercase `var(--text-muted)`
- Compact rows (44px height each, `border-bottom: 1px solid var(--border)`):
  - Symbol 13px mono bold (80px) + `<SignalPill />` small + delta 12px colored + price mono +
    thin confidence bar (flex 1)
  - Hover: `var(--bg-hover)` + cursor pointer → click navigates to `/markets?asset={symbol}`

**API:** `signal_update` WebSocket messages update both featured card and list.
On mount: `GET /signals/with-market?limit=10` to seed.

---

## 8. Page C — Map.tsx (2D Geopolitical Map)

**Route:** `/map` (accepts `?country={iso3}&view=2d` from Dashboard globe clicks)

### Layout: Full viewport minus shell (fixed left panel + map fills remainder + slide-in right panel)

```
┌──────────────┬────────────────────────────────────────┬──────────────────┐
│ FILTERS      │ LEAFLET 2D MAP                         │ DETAIL PANEL     │
│ (collapsed:  │                                        │ (hidden until    │
│  40px)       │                                        │ country clicked) │
│ (expanded:   │                                        │ 380px            │
│  200px)      │                                        │                  │
└──────────────┴────────────────────────────────────────┴──────────────────┘
```

### Map Setup (Leaflet)

```ts
// Tile layer: CartoDB Dark Matter — matches aesthetic perfectly
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© CartoDB',
  maxZoom: 8,
  minZoom: 2
})

// Initial view: world
map.setView([20, 0], 2)

// Countries: GeoJSON layer from GET /risk/countries
// Each feature styled by riskColor(feature.properties.risk_score)
// fillOpacity: 0.65, weight: 0.5, color: 'rgba(255,255,255,0.1)'

// Hover state: fillOpacity → 0.85, weight → 1.5
// Click: open right detail panel for that country
```

**Search-to-fly input** (absolute positioned top-right of map, above zoom controls):
- 200px wide input, `var(--bg-elevated)`, `var(--border-bright)` border, `var(--radius-md)`
- Placeholder: "Search country..."
- Filters GeoJSON features by name as user types, shows dropdown of matches
- On select: `map.flyTo(country.centroid, 5, { duration: 1.2 })` + opens detail panel

**Timeline scrubber** (absolute positioned bottom of map, above StatusBar):
- Full-width horizontal slider, 48px tall, `var(--bg-elevated)`, `border-top: 1px solid var(--border)`
- Range input: last 30 days. Default position: rightmost (today).
- Dragging scrubber calls `GET /risk/countries/history?date={date}` and re-colors the map.
- "30 DAY HISTORY" label left + selected date right in mono
- "LIVE" pill button far right: snaps back to real-time and re-subscribes WebSocket updates.
  Disabled/grayed when scrubber is not at rightmost position.

### Left Filter Panel

**Collapsed state** (40px wide): single "⊞ FILTERS" vertical label button.
**Expanded state** (200px): slides out with 300ms ease-snap transition.

Contents:
- "FILTERS" header + "✕" close button
- **Risk Level** section: checkboxes with color swatches
  - ● CRITICAL ≥80 (red)
  - ● HIGH ≥60 (amber)
  - ● MEDIUM ≥35 (cyan)
  - ● LOW <35 (green)
- **Active Themes** section (populated from `GET /events/themes`):
  - Tag-cloud of current event clusters: "Iran Tensions", "Red Sea Disruption", "Taiwan Strait"
  - Clicking a tag filters map to highlight only countries affected by that event cluster
  - Active tag: `var(--accent-cyan)` border, `var(--accent-cyan)` at 10% bg
- "RESET FILTERS" text button at bottom

### Right Detail Panel (slides in from right, 380px, `var(--bg-surface)`)

Triggered by country click or `?country=` URL param.
`border-left: 1px solid var(--border)`, z-index above map.

**Header:**
- Country flag emoji (if available) + country name — 20px bold `var(--text-primary)`
- Risk score badge + risk label — colored by `riskColor`
- `<LiveDot />` + "Live risk data" — 11px `var(--text-muted)`
- "✕" close button top-right

**Top events list** (from `GET /events/top-risks/{country_id}?limit=5`):
- "TOP EVENTS" eyebrow
- 3 compact event rows: severity dot + title + timestamp

**Asset tabs** (from `GET /market/local/{country_id}?limit=3`):
- Tab row showing linked assets: "NIFTY50 · INR · SILVER"
- Each tab is a pill: symbol + price + delta colored green/red
- Selected tab shows the full asset detail below

**Selected asset detail:**
- Symbol (large, 24px mono) + delta % (colored) + exchange tag
- `<CandlestickChart />` — recharts ComposedChart, 340×200px
  - OHLC bars: green fill for up candles (`#22c55e`), red for down (`var(--risk-critical)`)
  - Volume bars at bottom, dim teal
  - X-axis: dates, JetBrains Mono 10px
  - Y-axis: price, JetBrains Mono 10px
  - Tooltip: dark glass panel, OHLCV in mono
- OPEN / HIGH / LOW / CLOSE stat row (4 equal columns, JetBrains Mono 13px)
- "SECTOR EXPOSURE" section: horizontal bars per sector, `var(--accent-cyan)` fill

**"VIEW FULL SIGNAL →"** link at bottom: navigates to `/markets?asset={symbol}`.

**API on mount (when `?country=` param present):**
Simultaneously fetch `GET /events/top-risks/{country_id}?limit=5` and
`GET /market/local/{country_id}?limit=3` before rendering the panel.

---

## 9. Page D — Markets.tsx (Asset Browser)

**Route:** `/markets` (accepts `?asset={symbol}` to pre-open detail panel)

### Layout: Left sidebar + Center list + Right detail panel

```
┌──────────────┬──────────────────────┬───────────────────────────┐
│ SIDEBAR      │ ASSET LIST           │ ASSET DETAIL PANEL        │
│ 180px        │ 320px                │ flex 1 (~560px at 1440px) │
└──────────────┴──────────────────────┴───────────────────────────┘
```

Below 1200px: sidebar collapses to icon strip (32px). Detail panel becomes a slide-over.

### Left Sidebar

**ASSET CLASS** section:
- Stacked pill buttons: All · Commodities · Equity Indices · Forex · Crypto · Stocks · ETFs · Bonds
- Active: `var(--bg-hover)` + 2px left border `var(--accent-cyan)`
- Each pill: 13px `var(--text-secondary)`, 36px height, full width

**SIGNAL DIRECTION** section:
- All · BUY (↑ green icon) · SELL (↓ red icon) · HOLD (— gray icon)
- Same pill style as above

**ACTIVE THEMES** section (same as Map page):
- Event cluster tags from `GET /events/themes`
- Multi-select: multiple themes can be active at once, ANDs the filter

**"GENERATE ALL SIGNALS" button** at bottom:
- Full width, `var(--bg-hover)`, `var(--accent-amber)` border + text
- Click calls `POST /signals/generate-all` → shows progress:
  "Generating... 12/38 assets" with a count-up
- Disabled + spinner while in progress

### Center Panel — Asset List

**Search bar** (sticky top, `var(--bg-base)` background):
- "Search asset..." input with Lucide `Search` icon — full width, `var(--bg-elevated)`,
  `var(--border)`, `var(--radius-md)`

**Sort controls** (below search, flex row):
- "Sort by:" dropdown — Confidence · Signal Date · Asset Name · Volatility
- Ascending/descending toggle icon

**Signal Cards** (scrollable list, gap 4px):

Each card (`var(--bg-surface)`, `var(--radius-md)`, padding 12px 16px, `var(--border)` border):

```
[  BUY  ]  XAUUSD              87%
           Gold Spot                ← 12px text-secondary

████████████████████░░  Bull  82%
████░░░░░░░░░░░░░░░░░░  Bear  18%

[VOL: HIGH]  [short-term]  [metals]  [global]

⚡ Iran sanctions escalation in Strait of Hormuz region
```

- `<SignalPill />` is 40px wide, dominant element in the top-left
- Confidence % in 20px mono right-aligned, `riskColor`-ish (green for BUY, red for SELL)
- Bull bar: `var(--accent-green)` fill; Bear bar: `var(--risk-critical)` fill
- Tag chips: 10px uppercase, `var(--bg-elevated)`, `var(--radius-sm)`, 4px 8px padding
- Triggering event: 12px `var(--accent-amber)`, truncated 60 chars, prefix ⚡
- Hover: card `background → var(--bg-hover)`, right chevron `›` appears, cursor pointer
- Click: opens detail panel (or navigates to `?asset={symbol}`)

**Empty state** (when filters return nothing):
Funnel icon (Lucide `FilterX`) + "No assets match the current filters" + "Clear filters" button.

### Right Detail Panel — Single Asset View

**Sticky header** (`var(--bg-surface)`, `border-bottom: 1px solid var(--border)`, padding 20px):
- Row 1: Symbol (22px mono bold) + `<SignalPill large />` + category tag + description tag
- Row 2: Confidence: 32px mono `var(--accent-green)` right-aligned; "Uncertainty: XX%" 13px
  `var(--accent-amber)` below it
- "`<ConfidenceBar label="Bullish Strength" />`" — wide green bar
- "`<ConfidenceBar label="Bearish Strength" color="red" />`" — red bar (shorter)
- Tag chips row: MEDIUM VOLATILITY · short-term · metals · global

**Triggering Event block** (padding 0 20px):
- `var(--bg-elevated)`, `border: 1px solid var(--risk-critical)` at 30% opacity, `var(--radius-md)`, padding 12px
- "TRIGGERING EVENT" eyebrow — 10px uppercase `var(--accent-amber)`
- Event title — 16px bold `var(--text-primary)`
- Meta row: type tag · "Severity {N}" · timestamp mono

**Tab bar** (5 tabs, `border-bottom: 1px solid var(--border)`):
`TRADE SETUP` · `FORECAST` · `AI REASONING` · `TIMELINE` · `RELIABILITY`
- Active: `var(--text-primary)` + 2px bottom `var(--accent-cyan)`
- Default inactive: `var(--text-muted)` 13px

---

#### Tab 1: TRADE SETUP

"TRADE STRUCTURE" eyebrow — 10px uppercase, margin-bottom 16px.

**2×3 stat card grid** (`<StatCard />` components, gap 12px):

| Card | Value color |
|------|-------------|
| CURRENT PRICE | `var(--text-primary)` |
| ENTRY | `var(--text-primary)` |
| STOP LOSS | `var(--risk-critical)` |
| TARGET | `var(--accent-green)` |
| RISK:REWARD | `var(--text-primary)` |
| ATR (DAILY) | `var(--accent-amber)` |
| MAX POSITION | `var(--accent-purple)` |

Each `<StatCard />`: `var(--bg-elevated)` background, `var(--radius-md)`, padding 12px.
- Label: 10px uppercase `var(--text-muted)` top
- Value: 20px JetBrains Mono below

**Risk vs Reward bar** (full-width, 48px height, `var(--radius-md)`, margin-top 16px):
- Left segment (risk portion): `var(--risk-critical)` fill, "RISK X%" label inside
- Right segment (reward portion): `var(--accent-green)` fill, "REWARD X%" label inside
- Width ratio = risk:reward values

**Action buttons** (flex row, gap 12px, margin-top 20px):
- "REGENERATE SIGNAL" — `var(--bg-hover)`, `var(--accent-cyan)` border + text, loading spinner state
- "VIEW FORECAST →" — text button `var(--accent-cyan)`, switches to FORECAST tab (no navigation)

---

#### Tab 2: FORECAST (Monte Carlo, formerly standalone page)

**Header controls** (flex row, gap 16px, padding 16px 20px):
- Horizon pills: [30D] [60D] [90D] — pill toggle, active = `var(--accent-cyan)` bg
- "REGENERATE" button with circular progress ring (animation fills 360° over 60s auto-refresh)
- "Generated {N}m ago" — 11px `var(--text-muted)`
- View toggle right-aligned: [MONTE CARLO] [LINEAR] — pill toggle

**Main chart** (full width, 280px height, recharts `ComposedChart`):

Default layers (3):
1. Historical price line — `var(--accent-cyan)`, 1.5px, solid
2. P25–P75 probability cone — `Area` with `var(--accent-purple)` fill, 30% opacity
3. Current price reference — white dashed horizontal `ReferenceLine`

Optional overlay (toggled by "P5–P95" checkbox below chart):
4. P5–P95 outer cone — `var(--accent-purple)` fill, 10% opacity

When LINEAR view active:
- Replace cone with point estimate line — `var(--accent-amber)` dashed, 1.5px
- Add "MONTE CARLO" vs "LINEAR" legend

Vertical "TODAY" `ReferenceLine`: `var(--border-bright)`, dashed, with label "Today" in 10px mono.

X-axis: JetBrains Mono 10px dates. Y-axis: JetBrains Mono 10px prices.
Tooltip: dark glass panel (`var(--bg-elevated)`, `var(--border-bright)` border), date + price + CI range.

**Stats cards row** (5 cards, `repeat(5, 1fr)` grid, gap 8px, margin-top 12px):
- Expected Price — `var(--text-primary)`
- VaR (95%) — `var(--risk-critical)`
- CVaR — `var(--risk-critical)` (darker)
- Sharpe Ratio — `var(--accent-green)` if > 1, else `var(--accent-amber)`
- P(Loss) — `var(--risk-critical)`

**API:** `GET /forecast/mc/compare/{symbol}?horizon_days={30|60|90}`

---

#### Tab 3: AI REASONING

- Free-text AI analysis (from signal data) — 14px `var(--text-secondary)`, line-height 1.7
- "SOURCE EVENTS" section (collapsible, open by default):
  - 3–5 event cards (same compact format as Dashboard alerts)
- "CONFIDENCE BREAKDOWN" — horizontal bar chart (recharts `BarChart`):
  - Factors: Event Severity · Recency · Correlation · Trend Alignment · Volume Spike
  - Each bar in `var(--accent-cyan)` with % label

---

#### Tab 4: TIMELINE

Vertical timeline (`border-left: 2px solid var(--border)`, margin-left 8px):
Each node:
- Circle dot (10px, `riskColor(event.severity * 10)`) on the timeline line
- Timestamp — JetBrains Mono 11px `var(--text-muted)`, right of dot
- Event title — 13px bold `var(--text-primary)`
- `<SeverityBadge />` inline after title
- Description — 12px `var(--text-secondary)`, 2 lines max

Newest event at top.

---

#### Tab 5: RELIABILITY

"HISTORICAL ACCURACY — {ASSET CLASS}" eyebrow.

4 stat cards in a row:
- Win Rate — XX% in `var(--accent-green)`
- Avg Return — XX% per signal
- Avg Holding Period — X days
- Total Signals — N

Below: mini table of last 10 signals for this asset:
Date · Direction · Entry · Exit · Return · Outcome (WIN/LOSS badge in green/red).
Table: `var(--text-base)` rows, alternating `var(--bg-surface)` / `var(--bg-elevated)`.

---

## 10. Page E — Signals.tsx (AI Signals)

**Route:** `/signals`

**Purpose:** Full signal board across all assets with real-time updates.
This is the Markets center panel promoted to its own page — a master signal table
for power users who want everything at once.

### Layout: Full-width table view with filter bar

**Filter bar** (sticky, 56px, `var(--bg-surface)`, `border-bottom: 1px solid var(--border)`):
- Asset class pills (same as Markets sidebar) — horizontal, scrollable
- Direction pills — BUY / SELL / HOLD / ALL
- Min confidence slider: 0–100%, default 50%
- "REFRESH ALL" button
- "Last refreshed: {time}" — 12px `var(--text-muted)`

**Signal Table** (full width, `var(--bg-surface)`):

Column headers (10px uppercase `var(--text-muted)`, sortable with ↕ icon):
`ASSET` · `DIRECTION` · `CONFIDENCE` · `BULL` · `BEAR` · `ENTRY` · `TARGET` · `STOP` · `R:R` · `UPDATED`

Each row (44px height, `border-bottom: 1px solid var(--border)`, hover: `var(--bg-hover)`):
- ASSET: symbol mono bold + asset name 12px muted
- DIRECTION: `<SignalPill />`
- CONFIDENCE: colored % + thin bar (inline, 60px wide)
- BULL / BEAR: colored % values
- ENTRY / TARGET / STOP: JetBrains Mono, stop in red
- R:R: mono, e.g. "1:2.4"
- UPDATED: relative time ("2m ago") + absolute on hover tooltip

Click row → slide-in right panel (same as Markets detail panel, starting on TRADE SETUP tab).

**Empty/loading state:** skeleton rows with shimmer animation (CSS `background-size: 200%` animation).

**WebSocket:** `signal_update` messages update individual rows in-place with a brief
`var(--accent-cyan)` row flash (150ms) to indicate the update.

---

## 11. Page F — SupplyChain.tsx (Logistics Network)

**Route:** `/supply-chain`

### Layout: Full viewport

```
┌──────────────┬────────────────────────────────────────┐
│ LEFT PANEL   │ LEAFLET WORLD MAP                      │
│ 260px        │ (nodes + edges overlaid as markers)    │
└──────────────┴────────────────────────────────────────┘
                         ▲
              [SIMULATION LOG — slides up from bottom]
```

### Leaflet Map Setup

```ts
// Same dark basemap as Map.tsx
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  maxZoom: 10, minZoom: 1
})
map.setView([20, 0], 2)
```

**Node rendering** (from `GET /supply-chain/graph`):

Each node has `lat`, `lon`, `type`, `name`, `risk_level`, `id`.

| Node Type | Marker | Size | Color |
|-----------|--------|------|-------|
| production | Circle | 14px | `var(--accent-cyan)` |
| port | Hexagon (SVG custom icon) | 18px | `var(--text-primary)` |
| choke_point | Diamond (rotated square SVG) | 20px | risk-colored |

Choke points with risk >= 60: pulsing ring animation (CSS keyframe, 2s infinite,
`box-shadow` expanding from 0 to 16px at 0 opacity — same principle as `<LiveDot />`).

Node hover: Leaflet `bindTooltip` showing name + risk level + dependent count.
Node click: highlight all connected edges + fetch `GET /supply-chain/nodes/{node_id}/dependencies`
→ highlight dependency nodes in `var(--accent-amber)`.

**Edge rendering** (polylines):
- Shipping lanes: `L.polyline`, solid, 1.5px width, color = `riskColor(edge.risk_level)` at 60% opacity
- Pipelines: `L.polyline` with `dashArray: '8 4'`, same coloring
- No additional edge color encoding — width only encodes flow volume (thin 1px = low, 2.5px = high)

**Critical node highlight:** edges connected to a CRITICAL choke point
pulse in opacity (0.4 → 0.9 → 0.4, 1.5s infinite).

### Left Controls Panel (260px, `var(--bg-surface)`, `border-right: 1px solid var(--border)`)

**Node Legend** (padding 20px):
```
● Production Nodes    [cyan dot]
⬡ Port Nodes         [white hexagon]
◆ Choke Points       [risk-colored diamond]

── Shipping Lane
╌╌ Pipeline
```

**Critical Nodes list** — "TOP RISK NODES" eyebrow:
- Ranked list of top 5 choke points by threat score
- Each: rank number (mono, `var(--text-muted)`) + name + threat score bar (red fill) +
  risk badge
- Click: map flies to node (`map.flyTo([lat, lon], 6)`) + node click behavior fires

**"SIMULATE DISRUPTION" button** (full width, margin-top 24px):
- `var(--risk-critical)` border + text, `var(--bg-elevated)` background
- Opens simulation modal

### Simulation Modal

Not a `position: fixed` modal (breaks iframe layout). Use a centered overlay div
with `min-height: 400px` wrapper pattern:

```tsx
<div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
  <div style={{ width: 420px, background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)',
                borderRadius: 'var(--radius-lg)', padding: 28px }}>
    ...
  </div>
</div>
```

Modal contents:
1. "SIMULATE DISRUPTION" heading + "✕" close
2. **Target dropdown** — searchable, lists all supply chain nodes by name
3. **Disruption type** — 3-button toggle: [Blockade] [Strike] [Natural Disaster]
4. **Severity slider** (1–10):
   - `<input type="range" min="1" max="10" step="1" />`
   - Current value shown as large number (`var(--accent-red)`) that updates live
5. **Impact preview** — appears immediately when target is selected (before running):
   - `GET /supply-chain/nodes/{id}/dependencies` on target select
   - Shows: "Directly affects: N nodes" + first 3 node names
   - "Estimated impact radius: {N} secondary nodes"
6. "RUN SIMULATION" button — `var(--risk-critical)` bg, white text, full width
7. "Cancel" text button below

### Simulation Log Panel (slides up from bottom on simulation start)

48px collapsed handle: "SIMULATION LOGS ● RUNNING" + "STOP" button + "▲ EXPAND".
Expanded: 240px height, `var(--bg-elevated)`, `border-top: 1px solid var(--border)`.

Log content: monospaced scrollable list, newest entries appended at bottom, auto-scroll.
Each line (13px JetBrains Mono):
- `[HH:MM:SS]` timestamp in `var(--text-muted)`
- Message text colored: green for info, `var(--accent-amber)` for warning, `var(--risk-critical)` for critical

Streamed from `GET /supply-chain/simulation/{simulation_id}/logs` (SSE or long-poll).

Map updates in real-time during simulation: affected nodes switch to red pulsing state,
affected edges thicken and turn red.

"STOP" button: `DELETE /supply-chain/simulation/{id}` → log shows "Simulation terminated."
After completion: "EXPORT REPORT" button appears → `GET /supply-chain/simulation/{id}/report`.

**API:** `GET /supply-chain/graph`, `GET /supply-chain/critical-nodes`,
`GET /supply-chain/nodes/{id}/dependencies`, `POST /supply-chain/simulate`,
`GET /supply-chain/simulation/{id}/logs`

---

## 12. Page G — AiChat.tsx (AI Analyst)

**Route:** `/chat`

### Layout: Left sidebar + Right chat window

```
┌──────────────┬──────────────────────────────────────────┐
│ SESSIONS     │ CHAT WINDOW                              │
│ 240px        │ flex 1                                   │
│              │ ┌──────────────────────────────────────┐ │
│              │ │ TOP BAR (session title + NEW)        │ │
│              │ ├──────────────────────────────────────┤ │
│              │ │ MESSAGE FEED (scrollable)            │ │
│              │ │                                      │ │
│              │ ├──────────────────────────────────────┤ │
│              │ │ CONTEXT CHIPS                        │ │
│              │ │ INPUT BAR                            │ │
│              │ └──────────────────────────────────────┘ │
└──────────────┴──────────────────────────────────────────┘
```

### Left Sidebar (240px, `var(--bg-surface)`, `border-right: 1px solid var(--border)`)

**Header:** "ANALYST SESSIONS" — 10px uppercase `var(--text-muted)` + "+" new session button
(Lucide `Plus`, 16px, `var(--accent-cyan)`)

**Session list** (scrollable):
Each row (48px height, padding 12px, hover: `var(--bg-hover)`, cursor pointer):
- Session title — 13px `var(--text-primary)`, max 26 chars, ellipsis (editable on double-click)
- Meta row: message count + relative timestamp — 11px `var(--text-muted)`
- Active: `var(--bg-hover)` + 2px left border `var(--accent-cyan)`
- Hover reveals: trash icon right-aligned → `DELETE /chat/sessions/{id}` + confirm inline
  (replace icon with [✓ CONFIRM] [✗ CANCEL] — no modal needed for destructive actions in sidebars)

**Empty state:** Lucide `MessageSquare` icon + "No sessions yet" + "Start a conversation →" button.

**API:** `GET /chat/sessions` on mount. `POST /chat/sessions` on new session click.

### Right Chat Window

**Top bar** (`var(--bg-surface)`, `border-bottom: 1px solid var(--border)`, 48px):
- Session title (editable — click → inline input) — 15px bold `var(--text-primary)`
- `<LiveDot />` + "LIVE CONTEXT" — 11px `var(--text-muted)` (indicates RAG is pulling live events)
- "NEW SESSION" button right-aligned

**Message feed** (flex column, padding 20px, gap 20px, overflow-y scroll):

*User messages (right-aligned):*
```
                        ┌─────────────────────────────┐
                        │ What impact does the Strait  │
                        │ of Hormuz situation have on │
                        │ gold?                        │
                        └─────────────────────────────┘
```
- `var(--bg-elevated)`, `var(--border-bright)` border, `var(--radius-lg)` (12px) with
  bottom-right corner squared (`border-bottom-right-radius: 2px`)
- max-width 70%, float right, 14px `var(--text-primary)`

*Assistant messages (left-aligned, no bubble):*
```
⬡ GEOTRADE ANALYST                              14:32:07
The Strait of Hormuz situation is creating ...
[1] [2]

▼ SOURCES (2 events)
  ┌──────────────────────────────────────────┐
  │ ● Iran Navy Intercepts Tanker     SEV 8.2 │
  │   2h ago                                  │
  └──────────────────────────────────────────┘
```
- Eyebrow: "⬡ GEOTRADE ANALYST" — 10px uppercase `var(--accent-cyan)` + timestamp right
- Body: 14px `var(--text-secondary)`, line-height 1.65, no bubble background
- Citation markers `[1]`, `[2]`: 10px mono, `var(--bg-elevated)`, `var(--accent-cyan)` border,
  `var(--radius-sm)`, cursor pointer. Hover highlights corresponding source card.
- Sources section: `<details>` element. First message in session: open by default.
  Subsequent: closed by default with "▼ SOURCES ({N} events)" summary.
  Source cards: compact event card with title + severity + date.
- "ADD TO WATCHLIST" micro-action: appears at bottom-right of assistant messages that mention
  a specific asset (detected by regex against known asset symbols). Click → `POST /portfolio/watchlist`
  (deferred to when portfolio is built; for now, toast "Added to watchlist — coming soon").

*Loading / typing state:*
- Three dots, each cycling opacity (0.3 → 1.0 → 0.3) with 200ms stagger
- Color: `var(--accent-cyan)`

**Context chips** (above input, when present):
- "CONTEXT:" label — 10px `var(--text-muted)`
- Up to 3 chips from the 3 most recent high-severity events: event title truncated 24 chars
- Chip style: `var(--bg-elevated)`, `var(--border)`, `var(--radius-sm)`, 4px 8px
- "×" on each chip to dismiss
- Chips refresh every 60s from `GET /events/high-severity?min_severity=7&limit=3`
- Clicking a chip injects event title as context prefix into input:
  "Re: [Iran Sanctions — Strait of Hormuz] " prepended to next message

**Input bar** (`var(--bg-elevated)`, `border: 1px solid var(--border-bright)`,
`var(--radius-md)`, padding 12px 16px, flex row):
- Textarea — auto-expands up to 4 rows, then scrolls. Placeholder:
  "Ask about market impact, geopolitical risks, trading scenarios..."
- Enter to submit (Shift+Enter for newline)
- Send button: Lucide `Send`, 18px, `var(--accent-cyan)`, right-aligned
- While response is streaming: send button becomes "■ STOP" — aborts the SSE stream

**API:** `GET /chat/sessions/{id}/messages` on session select.
`POST /chat/sessions/{id}/ask` — request body `{ message: string, context_event_ids?: string[] }`.
Response: streaming (SSE) — stream tokens to message as they arrive, show typing indicator
until first token arrives.

---

## 13. Shared UI Components

### `<SignalPill direction="BUY|SELL|HOLD" size="sm|md|lg" />`

```
BUY  → background: rgba(0,255,136,0.12)  border: var(--accent-green)  text: var(--accent-green)
SELL → background: rgba(239,68,68,0.12)  border: var(--risk-critical)  text: var(--risk-critical)
HOLD → background: rgba(125,135,153,0.12) border: var(--text-muted)   text: var(--text-muted)
```
Font: Space Grotesk 700, uppercase.
- `sm`: 10px, 3px 6px padding
- `md`: 11px, 4px 8px padding (default)
- `lg`: 13px, 6px 12px padding

---

### `<SeverityBadge level="CRITICAL|HIGH|MEDIUM|LOW" score={9.2} />`

```
CRITICAL → text: var(--accent-amber)  bg: rgba(239,68,68,0.15)
HIGH     → text: var(--accent-amber)  bg: rgba(245,158,11,0.12)
MEDIUM   → text: var(--accent-cyan)   bg: rgba(6,182,212,0.12)
LOW      → text: var(--risk-low)      bg: rgba(34,197,94,0.12)
```
Shows "SEVERITY {score}" or just level label depending on `showScore` prop.

---

### `<ConfidenceBar label="" value={82} color="green|red|amber" />`

```tsx
<div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
  <span style={{ fontSize: 11, color: 'var(--text-secondary)', minWidth: 80 }}>{label}</span>
  <div style={{ flex: 1, height: 4, background: 'var(--bg-elevated)', borderRadius: 2 }}>
    <div style={{ width: `${value}%`, height: '100%', background: barColor, borderRadius: 2,
                  transition: 'width 600ms var(--ease-snap)' }} />
  </div>
  <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', minWidth: 36,
                 textAlign: 'right', color: barColor }}>{value}%</span>
</div>
```

---

### `<LiveDot status="live|degraded|offline" />`

```css
@keyframes ping {
  0%   { box-shadow: 0 0 0 0   rgba(0,255,136,0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(0,255,136,0); }
  100% { box-shadow: 0 0 0 0   rgba(0,255,136,0); }
}
.live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent-green);
  animation: ping 2s infinite;
}
```
`status="degraded"` → `var(--accent-amber)`, slower 3s animation.
`status="offline"` → `var(--risk-critical)`, no animation.

`prefers-reduced-motion`: animation disabled; static dot only.

---

### `<StatCard label="" value="" sub="" delta="" />`

```tsx
<div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', padding: '12px 16px' }}>
  <p style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-muted)', margin: 0 }}>{label}</p>
  <p style={{ fontSize: 20, fontFamily: 'var(--font-mono)', color: valueColor,
              margin: '4px 0 0', transition: 'all 800ms var(--ease-snap)' }}>
    {animatedValue}
  </p>
  {delta && <span style={{ fontSize: 11, color: delta > 0 ? 'var(--accent-green)' : 'var(--risk-critical)' }}>
    {delta > 0 ? '▲' : '▼'} {Math.abs(delta)}
  </span>}
</div>
```
Number animates from 0 to value over 800ms on mount (requestAnimationFrame counter).

---

### `<RiskGauge score={72} size={200} />`

SVG arc gauge. Key measurements:
- `cx = cy = size/2`
- `r = (size/2) - 20`
- `strokeWidth = 12`
- Arc sweep: 270° (from 135° to 45°, going clockwise)
- Conversion: `strokeDasharray = 2πr * (270/360)`, `strokeDashoffset = dasharray * (1 - score/100)`
- Animate `strokeDashoffset` on score change: 600ms ease-snap

---

### `<Sparkline data={number[]} color="amber|cyan|green" height={48} />`

recharts `AreaChart`:
```tsx
<AreaChart width={200} height={height} data={data.map((v, i) => ({ i, v }))}>
  <Area type="monotone" dataKey="v" stroke={strokeColor} fill={strokeColor}
        fillOpacity={0.15} strokeWidth={1.5} dot={false} />
</AreaChart>
```
No axes, no tooltip, no legend. Pure trend indicator.

---

## 14. Error, Empty & Loading States

Every data-driven section must handle all three states. No silent failures.

### Loading
- Stat cards: `var(--bg-elevated)` skeleton block with shimmer animation (CSS `background-position` shift)
- Tables: 5 skeleton rows, same height as real rows
- Charts: gray placeholder rectangle with "Loading chart..." centered in `var(--text-muted)`
- Globe/Map: spinner (Lucide `Loader2` rotating) centered on dark background

### Empty
Each component defines its empty state:
- Alerts: ShieldCheck icon + "No critical events in current window"
- Signal list: Zap icon + "No signals match the current filters" + Clear filters button
- Chat sessions: MessageSquare icon + "No sessions yet. Start a conversation."
- Map with no countries matching filter: Globe icon + "No countries match the selected risk filters"
- Supply chain with no data: Network icon + "Supply chain data unavailable" + Retry button

### Error
- Any `fetch` failure: red banner at top of affected section:
  `var(--risk-critical)` left border + "Failed to load {section name}. Retry →"
- WebSocket disconnect > 10s: amber toast (bottom-right, 300px wide, auto-dismiss 8s):
  "Live data connection lost. Signals and GTI may be stale."
- 401 from any API call: clear session + redirect to `/auth/login?redirect={current}`
- 503/500: generic error with support link. Never expose stack traces.

---

## 15. Responsive Behavior

| Breakpoint | Layout changes |
|------------|---------------|
| ≥ 1440px | All 3-column layouts at full width |
| 1200–1439px | Dashboard right rail becomes slide-over; Markets detail panel overlays |
| 960–1199px | Left sidebars collapse to icon-only; Nav GTI abbreviated |
| 768–959px | 2-column max; map panels become bottom sheets |
| < 768px | Single column; bottom tab nav replaces top nav (6 icons); map views scrollable; globe disabled |

**Mobile bottom tab nav** (when `< 768px`):
Icons: LayoutDashboard · Globe · BarChart2 · Zap · Network · MessageSquare
48px height, `var(--bg-elevated)`, `border-top: 1px solid var(--border)`

---

## 16. Accessibility

- All color distinctions also conveyed by icon or label — never color alone
- Focus rings: `outline: 2px solid var(--accent-cyan); outline-offset: 2px` on all interactive elements
- `prefers-reduced-motion`: all ambient animations (globe rotation, arc animations, ping dots,
  sparkline transitions, counter animations) disabled. Functional transitions (panel slides,
  tab switches) remain at 150ms.
- ARIA live regions: `aria-live="polite"` on GTI value, alert count, signal list. `aria-live="assertive"` on WebSocket disconnect banner.
- All charts: accessible `<table>` behind a `<details>` "Show data table" disclosure.
- Screen reader labels on all icon-only buttons: `aria-label="Close panel"` etc.
- Keyboard navigation: all interactive elements reachable via Tab. Modal traps focus while open.

---

## 17. API Base URL & Environment

All API calls use a base URL from environment variable:
```ts
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const WS_BASE  = import.meta.env.VITE_WS_URL  ?? 'ws://localhost:8000'
```

All authenticated calls include `Authorization: Bearer {token}` header.
Token stored in memory (AuthContext) after login. On page refresh: re-validate via
`GET /auth/me` on app mount before rendering the app shell.

---

*Document version: 2.0 — Portfolio removed. Monte Carlo integrated into Markets (Tab 2).
3D Globe moved to Dashboard center panel. Supply Chain uses Leaflet 2D world map.
Auth pages (Login, ForgotPassword, ResetPassword, RequestAccess) added.
All structural discussion from v1.0 review incorporated.*
