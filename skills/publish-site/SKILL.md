---
name: publish-site
description: Create and manage a personal Vantage site for publishing research reports. On first use, initializes a new Vantage project and starts the dev server. On subsequent uses, accepts already-prepared content (a Markdown file, URL, or article text) and turns it into a dual-theme editorial HTML report added to the local site. Does NOT do research itself — if the user only gives a bare topic with no content, direct them to run /search-information (report mode) first. Use when the user says "publish-site", "Vantage", "新建报告", "发布到站点", or wants to publish prepared content/reports to their Vantage site.
---

# Publish Site (Vantage)

One skill, two modes: **Initialize** a local Vantage site from a built-in template, or **Publish** already-prepared content as a dual-theme editorial report added to the running site.

This skill does not perform research. It turns existing content (Markdown/URL/article/file) into a site report. If the user gives only a bare topic with nothing to work from, tell them to run `/search-information`（报告模式）first to produce a Markdown report, then bring the result back here.

## Mode Detection

1. Look for a project directory containing `package.json` with `"name": "vantage"`.
   - Search order: user's selected workspace folder → common paths like `~/vantage`, `~/Desktop/vantage`
2. **Project NOT found** → run **Mode A: Initialize**
3. **Project found** → run **Mode B: Publish Report**

---

# Mode A: Initialize Project

Run this when no existing Vantage project is detected.

## Step A.1: Copy Template

Copy the entire `template/` directory (bundled with this skill) to the target location:
- If user has a selected workspace folder → copy into it as `vantage/`
- Otherwise → copy to `~/vantage/`

```bash
cp -r <skill-dir>/template/ <target-path>/
```

## Step A.2: Install Dependencies

```bash
cd <target-path> && npm install
```

If `npm install` fails, show the error and stop. Common fix: ensure Node.js >= 18 is installed.

## Step A.3: Start Dev Server

Start the Vite dev server in the background:

```bash
npm run dev
```

Use `run_in_background: true` so the conversation continues while the server runs.

## Step A.4: Report to User

Tell the user:
- Project initialized at `<target-path>`
- Dev server running at `http://localhost:5173` (or whatever port Vite reports)
- They can now bring a Markdown file, URL, or article to publish as their first report — or run `/search-information`（报告模式）first if they only have a topic

---

# Mode B: Publish Report

Run this when an existing Vantage project is found.

## Step B.0: Check Input

| User Input | Action |
|------------|--------|
| A Markdown file path, URL, article text, or other prepared content | Proceed to **Step B.1: Content Analysis** |
| Only a bare topic/keyword with nothing else to work from (e.g., "MCP 协议", "对比主流 AI 编程工具") | **Stop.** Tell the user this skill doesn't do research — ask them to run `/search-information`（报告模式）on the topic first, then bring the resulting Markdown back here to publish. |

If unclear which case applies, ask the user.

## Step B.1: Content Analysis

1. If URL: fetch content via `WebFetch` and extract the article text
2. If file path: read the file
3. If inline text: use directly
4. Analyze the content and restructure into a report Markdown:
   - Identify key themes, entities, data points
   - Organize into logical sections
   - Add analysis and structured comparisons where appropriate
5. Proceed to **Step B.Common**

---

## Step B.Common: Generate HTML & Integrate

### B.C.1: Read Style Reference

**You MUST read [style-reference.md](style-reference.md) before generating HTML.** It contains the complete CSS design system: variables, component patterns, typography, responsive breakpoints, and entity color palette.

### B.C.2: Analyze Structure

From the Markdown content, identify:

1. **Structure**: headings hierarchy, sections, tables, lists
2. **Entities**: main subjects being compared or discussed
3. **Data types**: comparison tables, pros/cons, workflows/steps, scores/ratings, summaries

### B.C.3: Assign Entity Colors

Each primary entity gets a unique theme color. Use the primary palette (slots 1–5):

| Slot | Light | Dark | Name |
|------|-------|------|------|
| 1 | `#4f46e5` | `#6366f1` | Indigo |
| 2 | `#059669` | `#10b981` | Emerald |
| 3 | `#d97706` | `#f59e0b` | Amber |
| 4 | `#db2777` | `#ec4899` | Pink |
| 5 | `#0891b2` | `#06b6d4` | Cyan |

For 6+ entities, see style-reference.md Section 7.

### B.C.4: Map Content to Components

| Markdown Pattern | HTML Component |
|-----------------|----------------|
| `# Title` + intro paragraph | Hero section (70vh, gradient text dark / solid light, pill badges) |
| `## Section` heading | Section block (Part N label + centered title, 80px padding) |
| Descriptive paragraphs per entity | Overview cards (top gradient bar, colored position text) |
| Comparison tables | Themed tables (rounded container, colored column headers) |
| Step-by-step / workflows | Workflow cards (numbered step capsules with arrows) |
| Scoring / multi-dimension comparison | Score bar charts (horizontal gradient bars with values) |
| Recommendation mapping | Scenario rows (3-column grid: need / pill / reason) |
| Short summary per entity | Summary rows (2-column grid: colored name / text) |
| Final conclusion | Final note (centered, dim text, max-width 700px) |

### B.C.5: Build HTML

Generate a single `.html` file following all rules from style-reference.md:

1. **Single file**: all CSS in `<style>`, no `<script>`, no external images
2. **Dual-theme CSS variables**: `:root` (light) + `[data-theme="dark"]` overrides
3. **Entity consistency**: every entity uses its assigned color everywhere
4. **Font stacks**: Display: `'Playfair Display', 'Noto Serif SC', Georgia, serif`; Body: `'Inter', 'Noto Sans SC', -apple-system, sans-serif`
5. **Import Google Fonts**: `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;700;900&family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&display=swap')`
6. **Responsive**: `clamp()` for titles, `auto-fit` + `minmax` grids, `overflow-x: auto` for tables
7. **Default dark**: `<html data-theme="dark">` — the parent app overrides at render time
8. **Hero title**: gradient text only in `[data-theme="dark"]` via `background-clip: text`
9. **Site accent**: non-entity decorative elements use `--site-accent` (gold)
10. **Noise texture**: include `body::before` overlay (see style-reference.md Section 2)
11. **No** JavaScript, external images, `backdrop-filter`, emoji/icons, `border-radius > 20px` (except `999px` for pills)
12. Max container width: `1200px`

### B.C.6: Generate Slug

Create a URL-friendly slug from the title:
- Lowercase, English words only
- Replace spaces with hyphens
- Remove special characters
- Keep concise (3–5 words max)
- Example: "AI Agent 框架深度对比" → `ai-agent-frameworks-comparison`

### B.C.7: Save HTML Report

Create the report directory and save the HTML:

```
<project>/public/reports/<slug>/index.html
```

### B.C.8: Demote Existing Featured Report

Scan all JSON files in `<project>/src/content/reports/`. For any file with `"featured": true`, change it to `"featured": false`.

### B.C.9: Create Metadata JSON

Create `<project>/src/content/reports/<slug>.json`:

```json
{
  "slug": "<slug>",
  "title": "<report title>",
  "date": "<YYYY-MM-DD>",
  "summary": "<one-paragraph summary>",
  "tags": ["tag1", "tag2", "tag3"],
  "featured": true,
  "htmlPath": "/reports/<slug>/index.html"
}
```

Rules:
- `featured` is always `true` for the new report
- `tags` should be 3–5 relevant tags
- `date` format must be `YYYY-MM-DD`

### B.C.10: Verify & Report

1. Confirm HTML exists at `public/reports/<slug>/index.html`
2. Confirm JSON exists at `src/content/reports/<slug>.json`
3. Confirm no other report has `"featured": true`
4. Tell the user: report added, visible at `http://localhost:5173/reports/<slug>`

Vite HMR will pick up the new files automatically — the user can see the report in their browser immediately.

---

# Dev Server Management

If the dev server is not running when generating a report:

```bash
cd <project-path> && npm run dev
```

Start it in the background before telling the user to view the report.

---

# Constraints

- No JavaScript in generated HTML reports
- No external images or assets (pure CSS visuals)
- No `backdrop-filter` / blur effects
- No emoji or decorative icons in HTML
- No `border-radius > 20px` (except `999px` for pills)
- Max container width: 1200px
- Must include both `:root` and `[data-theme="dark"]` CSS variable blocks
- Default `data-theme="dark"` on `<html>` tag
- Hero title uses `background-clip: text` gradient **only in dark mode**
- Display font (`Playfair Display`) for hero and section titles only; body uses `Inter`
- Build must use the style-reference.md CSS design system

---

# Quick Reference

| Item | Value |
|------|-------|
| Template location | `<skill-dir>/template/` |
| Report HTML | `<project>/public/reports/<slug>/index.html` |
| Report metadata | `<project>/src/content/reports/<slug>.json` |
| Report data loader | `<project>/src/lib/reports.ts` |
| Dev command | `npm run dev` |
| Build command | `npm run build` |
| Style reference | [style-reference.md](style-reference.md) |
