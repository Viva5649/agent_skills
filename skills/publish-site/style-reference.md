# Style Reference — Dual-Theme Editorial Dashboard

Complete CSS patterns and component specifications. The agent MUST read this file when building the HTML to ensure pixel-accurate implementation.

Aligned with the AI-Insight site aesthetic. Supports both light (default) and dark modes via `data-theme` attribute on `<html>`.

---

## 1. CSS Variables Template

The `<html>` tag must include `data-theme="dark"` as the default. The parent React app overrides this attribute at render time. Light mode (`:root`) is the base; dark activates via `[data-theme="dark"]`.

```css
/* ===== BASE TOKENS (Light Mode - Default) ===== */
:root {
  /* Backgrounds (3-layer depth: page > card > elevated) */
  --bg: #faf7f2;
  --bg-card: #ffffff;
  --bg-card-hover: #f5f0e8;
  --border: rgba(0, 0, 0, 0.10);
  --border-strong: rgba(0, 0, 0, 0.18);

  /* Text (3-level hierarchy) */
  --text: #555;
  --text-dim: #888;
  --text-bright: #111;

  /* Site accent (gold) -- used for non-entity decorative elements */
  --site-accent: #8b6914;
  --site-accent-dim: #a07d2e;

  /* Fonts */
  --font-display: 'Playfair Display', 'Noto Serif SC', Georgia, serif;
  --font-body: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', monospace;

  /* Utility */
  --shadow-hover: 0 20px 60px rgba(0, 0, 0, 0.08);
  --table-stripe: rgba(0, 0, 0, 0.02);
  --score-track: rgba(0, 0, 0, 0.06);
  --code-bg: rgba(0, 0, 0, 0.04);
  --code-border: rgba(0, 0, 0, 0.06);
  --scrollbar-thumb: rgba(0, 0, 0, 0.12);
  --scrollbar-hover: rgba(0, 0, 0, 0.20);
  --noise-opacity: 0.018;

  /* Entity colors — replace per project (light-mode: deeper shades) */
  --accent-1: #4f46e5;
  --accent-2: #059669;
  --accent-3: #d97706;
  --accent-4: #db2777;
  --accent-5: #0891b2;
  --gradient-1: linear-gradient(135deg, #4f46e5, #7c3aed);
  --gradient-2: linear-gradient(135deg, #059669, #10b981);
  --gradient-3: linear-gradient(135deg, #d97706, #f59e0b);
  --gradient-4: linear-gradient(135deg, #db2777, #ec4899);
  --gradient-5: linear-gradient(135deg, #0891b2, #06b6d4);

  /* Entity soft colors (for text labels / soft backgrounds on light bg) */
  --soft-1: #4338ca;  --softbg-1: rgba(79, 70, 229, 0.08);
  --soft-2: #047857;  --softbg-2: rgba(5, 150, 105, 0.08);
  --soft-3: #b45309;  --softbg-3: rgba(217, 119, 6, 0.08);
  --soft-4: #be185d;  --softbg-4: rgba(219, 39, 119, 0.08);
  --soft-5: #0e7490;  --softbg-5: rgba(8, 145, 178, 0.08);
}

/* ===== DARK MODE ===== */
[data-theme="dark"] {
  --bg: #0c0c0c;
  --bg-card: #141414;
  --bg-card-hover: #1a1a1a;
  --border: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.12);

  --text: #e8e8e8;
  --text-dim: #666;
  --text-bright: #fff;

  --site-accent: #c8a97e;
  --site-accent-dim: #a08560;

  --shadow-hover: 0 20px 60px rgba(0, 0, 0, 0.4);
  --table-stripe: rgba(255, 255, 255, 0.02);
  --score-track: rgba(255, 255, 255, 0.05);
  --code-bg: rgba(255, 255, 255, 0.04);
  --code-border: rgba(255, 255, 255, 0.06);
  --scrollbar-thumb: rgba(255, 255, 255, 0.08);
  --scrollbar-hover: rgba(255, 255, 255, 0.15);
  --noise-opacity: 0.028;

  /* Entity colors revert to vivid originals for dark */
  --accent-1: #6366f1;
  --accent-2: #10b981;
  --accent-3: #f59e0b;
  --accent-4: #ec4899;
  --accent-5: #06b6d4;
  --gradient-1: linear-gradient(135deg, #6366f1, #8b5cf6);
  --gradient-2: linear-gradient(135deg, #10b981, #34d399);
  --gradient-3: linear-gradient(135deg, #f59e0b, #fbbf24);
  --gradient-4: linear-gradient(135deg, #ec4899, #f472b6);
  --gradient-5: linear-gradient(135deg, #06b6d4, #22d3ee);

  --soft-1: #a5b4fc;  --softbg-1: rgba(99, 102, 241, 0.10);
  --soft-2: #6ee7b7;  --softbg-2: rgba(16, 185, 129, 0.10);
  --soft-3: #fcd34d;  --softbg-3: rgba(245, 158, 11, 0.10);
  --soft-4: #f9a8d4;  --softbg-4: rgba(236, 72, 153, 0.10);
  --soft-5: #67e8f9;  --softbg-5: rgba(6, 182, 212, 0.10);
}
```

---

## 2. Global Styles

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;700;900&family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}

/* Noise texture overlay (matches site) */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: var(--noise-opacity);
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 256px 256px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-hover); }

/* Selection */
::selection { background: rgba(139, 105, 20, 0.15); color: #111; }
[data-theme="dark"] ::selection { background: rgba(200, 169, 126, 0.3); color: #fff; }
```

---

## 3. Typography Scale

| Usage | Size | Weight | Font | Color | Extras |
|-------|------|--------|------|-------|--------|
| Hero title | `clamp(2.2rem, 5vw, 3.8rem)` | 900 | `--font-display` | solid `--text-bright` (light) / gradient text (dark) | `letter-spacing: -0.02em` |
| Section title | `clamp(1.6rem, 3.5vw, 2.4rem)` | 700 | `--font-display` | `--text-bright` | `letter-spacing: -0.01em` |
| Card title | `1.15rem ~ 1.4rem` | 700 | `--font-body` | `--text-bright` | -- |
| Card subtitle / position | `0.85rem ~ 0.92rem` | 600 | `--font-body` | entity soft color (`--soft-N`) | -- |
| Body / description | `0.85rem ~ 0.92rem` | 400 | `--font-body` | `--text-dim` | `line-height: 1.8` |
| Section label | `0.75rem` | 700 | `--font-body` | `--site-accent` | `letter-spacing: 0.12em; text-transform: uppercase` |
| Table header | `0.78rem` | 700 | `--font-body` | `--text-dim` | `letter-spacing: 0.06em; text-transform: uppercase` |
| Tags / badges | `0.78rem ~ 0.82rem` | 600 | `--font-body` | entity soft color (`--soft-N`) | -- |
| Code / monospace | `0.78rem` | 400 | `--font-mono` | `--text-dim` | -- |

---

## 4. Component Patterns

### 4.1 Hero Section

```css
.hero {
  position: relative;
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
  padding: 60px 20px;
}

/* Layered radial glow using entity colors — lower opacity in light mode */
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 50% 40%, rgba(ENTITY_1_RGB, 0.06), transparent),
    radial-gradient(ellipse 60% 50% at 20% 80%, rgba(ENTITY_5_RGB, 0.04), transparent),
    radial-gradient(ellipse 60% 50% at 80% 80%, rgba(ENTITY_4_RGB, 0.03), transparent);
}
[data-theme="dark"] .hero::before {
  background:
    radial-gradient(ellipse 80% 60% at 50% 40%, rgba(ENTITY_1_RGB, 0.15), transparent),
    radial-gradient(ellipse 60% 50% at 20% 80%, rgba(ENTITY_5_RGB, 0.10), transparent),
    radial-gradient(ellipse 60% 50% at 80% 80%, rgba(ENTITY_4_RGB, 0.08), transparent);
}

/* Hero title: solid color in light, gradient text in dark */
.hero h1 {
  font-family: var(--font-display);
  font-size: clamp(2.2rem, 5vw, 3.8rem);
  font-weight: 900;
  letter-spacing: -0.02em;
  color: var(--text-bright);
  margin-bottom: 20px;
}
[data-theme="dark"] .hero h1 {
  background: linear-gradient(135deg, #fff 0%, var(--soft-1) 50%, var(--soft-5) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Date badge — uses site accent, not entity color */
.date-badge {
  display: inline-block;
  padding: 6px 20px;
  border-radius: 999px;
  background: rgba(139, 105, 20, 0.08);
  border: 1px solid rgba(139, 105, 20, 0.20);
  color: var(--site-accent);
  font-size: 0.85rem;
  font-weight: 500;
}
[data-theme="dark"] .date-badge {
  background: rgba(200, 169, 126, 0.10);
  border-color: rgba(200, 169, 126, 0.25);
}

/* Entity tag pills — use entity soft colors */
.tag {
  padding: 8px 18px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  /* Per entity, using --soft-N and --softbg-N: */
  background: var(--softbg-N);
  border: 1px solid var(--accent-N);
  color: var(--soft-N);
}
```

### 4.2 Section Header

```css
.section {
  padding: 80px 0;
  border-top: 1px solid var(--border);
}

.section-header {
  text-align: center;
  margin-bottom: 60px;
}

.section-label {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--site-accent);
  margin-bottom: 12px;
}

.section-title {
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3.5vw, 2.4rem);
  font-weight: 700;
  color: var(--text-bright);
}
```

### 4.3 Content Card

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 36px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

/* Top gradient bar -- entity color */
.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--gradient-N); /* entity gradient */
}

.card:hover {
  background: var(--bg-card-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}
```

**Card inner structure:**
- `.card-name`: 1.4rem, weight 700, `--text-bright`
- `.card-repo` (optional): `var(--font-mono)`, 0.78rem, `var(--code-bg)` bg, rounded 6px
- `.card-position`: 0.92rem, weight 600, entity soft color (`--soft-N`)
- `.card-desc`: 0.9rem, `--text-dim`, line-height 1.8
- `.problem-item`: flex row with 5px dot (entity pure color `--accent-N`) + 0.85rem text
- `.card-highlight`: inline pill, `var(--softbg-N)` + `var(--soft-N)` text, border-radius 8px

### 4.4 Data Table

```css
/* Wrapper */
.table-wrap {
  overflow-x: auto;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--bg-card);
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
  font-size: 0.85rem;
}

thead { background: var(--table-stripe); }

th {
  padding: 16px 18px;
  text-align: left;
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-dim);
  border-bottom: 1px solid var(--border);
}

/* Entity column header indicator */
th.col-N { border-top: 2px solid var(--accent-N); }

td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--table-stripe);
  vertical-align: top;
  line-height: 1.6;
}

tbody tr:hover { background: var(--table-stripe); }

/* First column (dimension label) */
td.dim-label {
  font-weight: 600;
  color: var(--text-bright);
  white-space: nowrap;
}
```

### 4.5 Architecture / Detail Card

```css
.detail-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px;
  border-left: 3px solid var(--accent-N); /* entity color */
}
```

Grid layout: `repeat(auto-fit, minmax(340px, 1fr))`, gap 20px.

### 4.6 Workflow Card

```css
.workflow-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 36px;
  position: relative;
  overflow: hidden;
}

/* Bottom gradient bar */
.workflow-card::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: var(--gradient-N);
}
```

**Step capsules:**

```css
.step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  background: var(--code-bg);
  border: 1px solid var(--code-border);
}

.step-num {
  width: 22px; height: 22px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 800;
  background: var(--softbg-N); /* entity soft bg */
  color: var(--soft-N);
}

.step-arrow { color: var(--text-dim); font-size: 0.7rem; } /* -> character */
```

**Command tags:**

```css
.cmd-tag {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  padding: 5px 12px;
  border-radius: 6px;
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  color: var(--text-dim);
}
```

### 4.7 Score Bar Chart

```css
.score-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.score-label {
  font-size: 0.82rem;
  font-weight: 600;
  width: 120px;
  flex-shrink: 0;
}

.score-bar-bg {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--score-track);
  overflow: hidden;
}

.score-bar {
  height: 100%;
  border-radius: 4px;
  background: var(--gradient-N); /* entity gradient */
  /* width set via inline style: style="width:85%" */
}

.score-val {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-dim);
  width: 30px;
  text-align: right;
}
```

Score cards use grid: `repeat(auto-fit, minmax(340px, 1fr))`, gap 20px.
Each card has a title (uppercase, letter-spaced) + multiple score rows.

### 4.8 Scenario / Selection Row

```css
.scenario-row {
  display: grid;
  grid-template-columns: 1fr 160px 1fr;
  gap: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px 24px;
  align-items: center;
  transition: background 0.2s;
}

.scenario-row:hover { background: var(--bg-card-hover); }

/* Center pill */
.framework-pill {
  text-align: center;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  background: var(--softbg-N); /* entity soft bg */
  color: var(--soft-N);
}
```

### 4.9 Summary Row

```css
.summary-card {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px 28px;
  align-items: center;
  transition: background 0.2s;
}

.summary-name {
  font-size: 1rem;
  font-weight: 800;
  color: var(--soft-N); /* per entity */
}

.summary-text {
  font-size: 0.92rem;
  color: var(--text);
  font-weight: 500;
}
```

### 4.10 Combination / Suggestion Card

```css
.combo-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px;
  transition: background 0.2s;
}

.combo-card:hover { background: var(--bg-card-hover); }
```

Grid layout: `repeat(auto-fit, minmax(280px, 1fr))`, gap 16px.

### 4.11 Final Note

```css
.final-note {
  text-align: center;
  padding: 60px 20px;
  border-top: 1px solid var(--border);
}

.final-note p {
  font-size: 1.05rem;
  color: var(--text-dim);
  max-width: 700px;
  margin: 0 auto;
  line-height: 1.9;
}

.final-note strong {
  color: var(--text-bright);
}
```

### 4.12 Strength / Analysis Card

```css
.strength-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px;
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 24px;
  align-items: start;
  transition: background 0.2s;
}

.strength-name {
  font-size: 1rem;
  font-weight: 800;
  color: var(--soft-N); /* per entity */
}

.strength-text {
  font-size: 0.88rem;
  color: var(--text-dim);
  line-height: 1.8;
}

.strength-text strong { color: var(--text); }
```

---

## 5. Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
```

---

## 6. Responsive Breakpoints

```css
@media (max-width: 768px) {
  /* Multi-column grids -> single column */
  .scenario-row { grid-template-columns: 1fr; text-align: center; }
  .summary-card { grid-template-columns: 1fr; text-align: center; }
  .strength-card { grid-template-columns: 1fr; }
  .detail-cards { grid-template-columns: 1fr; }
}
```

---

## 7. Entity Color Palette (Both Modes)

Entity colors have two variants: **light-mode** (deeper, for contrast on cream backgrounds) and **dark-mode** (vivid, for glow on dark backgrounds). The CSS variables template in Section 1 handles this automatically via `[data-theme="dark"]`.

When assigning entity colors, use these values:

| Slot | Light Accent | Dark Accent | Light Gradient (135deg) | Dark Gradient (135deg) | Light Soft Text | Dark Soft Text | Light Soft BG | Dark Soft BG |
|------|-------------|-------------|------------------------|----------------------|-----------------|----------------|---------------|--------------|
| 1 | `#4f46e5` | `#6366f1` | `#4f46e5, #7c3aed` | `#6366f1, #8b5cf6` | `#4338ca` | `#a5b4fc` | `rgba(79,70,229,0.08)` | `rgba(99,102,241,0.10)` |
| 2 | `#059669` | `#10b981` | `#059669, #10b981` | `#10b981, #34d399` | `#047857` | `#6ee7b7` | `rgba(5,150,105,0.08)` | `rgba(16,185,129,0.10)` |
| 3 | `#d97706` | `#f59e0b` | `#d97706, #f59e0b` | `#f59e0b, #fbbf24` | `#b45309` | `#fcd34d` | `rgba(217,119,6,0.08)` | `rgba(245,158,11,0.10)` |
| 4 | `#db2777` | `#ec4899` | `#db2777, #ec4899` | `#ec4899, #f472b6` | `#be185d` | `#f9a8d4` | `rgba(219,39,119,0.08)` | `rgba(236,72,153,0.10)` |
| 5 | `#0891b2` | `#06b6d4` | `#0891b2, #06b6d4` | `#06b6d4, #22d3ee` | `#0e7490` | `#67e8f9` | `rgba(8,145,178,0.08)` | `rgba(6,182,212,0.10)` |

**Extended palette** (for 6+ entities):

| Slot | Light Accent | Dark Accent | Light Gradient (135deg) | Dark Gradient (135deg) | Light Soft Text | Dark Soft Text | Light Soft BG | Dark Soft BG |
|------|-------------|-------------|------------------------|----------------------|-----------------|----------------|---------------|--------------|
| 6 | `#e11d48` | `#f43f5e` | `#e11d48, #f43f5e` | `#f43f5e, #fb7185` | `#be123c` | `#fda4af` | `rgba(225,29,72,0.08)` | `rgba(244,63,94,0.10)` |
| 7 | `#7c3aed` | `#8b5cf6` | `#7c3aed, #8b5cf6` | `#8b5cf6, #a78bfa` | `#6d28d9` | `#c4b5fd` | `rgba(124,58,237,0.08)` | `rgba(139,92,246,0.10)` |
| 8 | `#65a30d` | `#84cc16` | `#65a30d, #84cc16` | `#84cc16, #a3e635` | `#4d7c0f` | `#bef264` | `rgba(101,163,13,0.08)` | `rgba(132,204,22,0.10)` |
| 9 | `#ea580c` | `#f97316` | `#ea580c, #f97316` | `#f97316, #fb923c` | `#c2410c` | `#fdba74` | `rgba(234,88,12,0.08)` | `rgba(249,115,22,0.10)` |
| 10 | `#0d9488` | `#14b8a6` | `#0d9488, #14b8a6` | `#14b8a6, #2dd4bf` | `#0f766e` | `#5eead4` | `rgba(13,148,136,0.08)` | `rgba(20,184,166,0.10)` |
