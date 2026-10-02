---
name: create-blueprint
description: 生成工程蓝图风格的技术图表，支持箭头、连线、关系标注等实体间关系表达。适用于架构图、系统图、流程图、技术规格说明等场景。
---

# Flat Engineering Blueprint Diagram Generator v2

Generate precise, objective diagrams with high data-ink ratio. Output should resemble technical specification sheets or architectural diagrams, NOT marketing landing pages. All entity relationships MUST be explicitly expressed through typed SVG connectors — never rely on spatial proximity alone.

## Core Philosophy

Precise, Objective, High Data-Ink Ratio, Relationships Made Visible.

## Visual Rules

### 1. No Decorations

- NO drop shadows
- NO gradients
- NO glassmorphism/blur
- NO rounded buttons

### 2. Flat & Outlined

- Use 1px or 2px solid borders for structure
- Use white backgrounds for content blocks

### 3. Monochrome Base (Apple System Palette)

```css
:root {
  --c-bg: #f5f5f7;
  --c-canvas: #ffffff;
  --c-border: #d2d2d7;
  --c-hairline: #e8e8ed;
  --c-text-main: #1d1d1f;
  --c-text-sub: #6e6e73;
  --c-tint: #0071e3;      /* Key color — the ONE path or node the reader should look at first */
  --c-warn: #ff9500;      /* Semantic orange — warnings, degraded / fallback / retry paths */
  --c-warn-text: #b25000; /* Orange for text on white (#ff9500 is too light for text) */
  --c-accent: #d70015;    /* Semantic red — errors, critical paths only */
  --font-ui: system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono: 'SF Mono', Monaco, Consolas, monospace;
}
```

The palette follows Apple's neutral system grays: an off-white page, pure white surfaces, near-black label text instead of pure `#000`, and quiet separators.

| Token           | Hex       | Role                                                       |
| --------------- | --------- | ---------------------------------------------------------- |
| `--c-bg`        | `#f5f5f7` | Page background (Apple light gray)                         |
| `--c-canvas`    | `#ffffff` | Diagram canvas, nodes, label masks                         |
| `--c-border`    | `#d2d2d7` | Node and canvas borders                                    |
| `--c-hairline`  | `#e8e8ed` | Layer dividers and other low-priority separators           |
| `--c-text-main` | `#1d1d1f` | Titles, primary connectors and arrowheads                  |
| `--c-text-sub`  | `#6e6e73` | Descriptions, connector labels, secondary connectors       |
| `--c-tint`      | `#0071e3` | Key color: one highlighted path, node or badge per diagram |
| `--c-warn`      | `#ff9500` | Warning lines, markers and borders (Apple system orange)   |
| `--c-warn-text` | `#b25000` | Warning text and labels on white                           |
| `--c-accent`    | `#d70015` | Errors and critical paths only                             |

- Everything structural stays in grays. Color carries meaning, never decoration.
- Each color has exactly one meaning: blue = "look here first", orange = warning (still works, but degraded, retried, rate-limited or deprecated), red = error. Pick the meaning first; never pick orange because the diagram "needs warmth". If every path is colored, none stands out.
- Orange and red sit close in hue, so the warning style also differs in shape: warning connectors are dashed, error connectors are solid.
- Orange uses two values: `#ff9500` for strokes, markers and borders, `#b25000` for text. `#ff9500` text on white is only 2.2:1, and Apple's own accessible orange (`#c93400`) is too close to the red to tell apart at 10px.
- `--c-text-sub` (#6e6e73) is the lightest gray allowed for text; lighter grays such as `#86868b` fall below readable contrast at 10–11px.
- The red is Apple's accessible system red (`#d70015`), not the brighter `#ff3b30`, so small red labels stay legible on white.

### 4. Typography

- Headings/Labels: Sans-serif (`var(--font-ui)`)
- Data/Paths/Code/Connector Labels: Monospace (`var(--font-mono)`)

### 5. Layout Structure

- Diagram must be contained within a `diagram-canvas` (bordered box with padding)
- Header: Title + Uppercase Subtitle, separated by solid bottom border
- Grid/Flexbox alignment: Everything must be strictly aligned
- The `diagram-canvas` MUST use `position: relative` to serve as the coordinate system for the SVG connector layer

### 6. Elements

- Connectors: SVG-based arrows and lines drawn in a dedicated overlay layer (see §Connector System)
- Icons: Simple stroke SVG icons (no fill or complex details)
- Badges: Outlined or solid black/gray blocks. Small font size

---

## Layer Arrow System (Primary Connector Method)

For layered architecture diagrams (the most common case), use **pure CSS arrows** between layers. This approach is robust, requires no JavaScript, no SVG coordinate calculations, and automatically adapts to layout changes.

### Basic Vertical Arrow

Insert a `.layer-arrow` div between two layers to draw a downward arrow:

```html
<div class="layer-arrow">
  <span class="layer-arrow__label">REST API</span>
</div>
```

```css
.layer-arrow {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 32px;
  position: relative;
}

.layer-arrow::before {
  content: '';
  display: block;
  width: 1.5px;
  height: 100%;
  background: #1d1d1f;
}

.layer-arrow::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #1d1d1f;
}

.layer-arrow__label {
  position: absolute;
  left: calc(50% + 10px);
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  font-family: var(--font-mono);
  color: #6e6e73;
  white-space: nowrap;
  background: #ffffff;
  padding: 0 4px;
}
```

### Variant Modifiers

```css
/* Dashed arrow (dependency / async) */
.layer-arrow--dashed::before {
  background: repeating-linear-gradient(to bottom, #6e6e73 0, #6e6e73 4px, transparent 4px, transparent 8px);
}
.layer-arrow--dashed::after {
  border-top-color: #6e6e73;
}

/* Dotted arrow (event / lazy load) */
.layer-arrow--dotted::before {
  background: repeating-linear-gradient(to bottom, #6e6e73 0, #6e6e73 2px, transparent 2px, transparent 6px);
}
.layer-arrow--dotted::after {
  border-top-color: #6e6e73;
}

/* Warning arrow (degraded / fallback / retry between layers) */
.layer-arrow--warn::before {
  width: 2px;
  background: repeating-linear-gradient(to bottom, #ff9500 0, #ff9500 4px, transparent 4px, transparent 8px);
}
.layer-arrow--warn::after {
  border-top-color: #ff9500;
}
.layer-arrow--warn .layer-arrow__label {
  color: #b25000;
}
```

### Branching Arrow (1-to-N Split)

For routing from one layer to multiple targets below (e.g., Router → multiple view groups), use an inline SVG that draws a T-shape. This is the **only** place SVG is used, and coordinates are relative to the SVG's own viewport — no external element measurement needed:

```html
<div class="layer-split">
  <svg width="100%" height="36" viewBox="0 0 700 36" preserveAspectRatio="xMidYMid meet">
    <defs>
      <!-- Drawn pointing right (+x); orient="auto" rotates it to follow the line downward -->
      <marker id="split-arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#1d1d1f" stroke-width="1.5" />
      </marker>
    </defs>
    <!-- Trunk -->
    <line x1="350" y1="0" x2="350" y2="10" stroke="#1d1d1f" stroke-width="1.5" />
    <!-- Horizontal bar -->
    <line x1="150" y1="10" x2="550" y2="10" stroke="#1d1d1f" stroke-width="1.5" />
    <!-- Left branch -->
    <line x1="150" y1="10" x2="150" y2="36" stroke="#1d1d1f" stroke-width="1.5" marker-end="url(#split-arr)" />
    <!-- Right branch -->
    <line x1="550" y1="10" x2="550" y2="36" stroke="#1d1d1f" stroke-width="1.5" marker-end="url(#split-arr)" />
  </svg>
</div>
```

```css
.layer-split {
  display: flex;
  justify-content: center;
  height: 36px;
}
.layer-split svg {
  overflow: visible;
  max-width: 700px;
}
```

> **Key point:** The SVG uses `viewBox` with fixed internal coordinates and `preserveAspectRatio="xMidYMid meet"`, so branch positions are proportional and self-contained. No external JS or DOM measurement is needed.

### Layer Dividers

For visual separation between architectural layers without arrows (e.g., between sibling sections):

```css
.layer-divider {
  margin: 18px 0;
  border: none;
  border-top: 1px solid var(--c-hairline);
}
```

### When to Use What

| Scenario                               | Method                                                 |
| -------------------------------------- | ------------------------------------------------------ |
| Vertical flow between adjacent layers  | **CSS `.layer-arrow`**                                 |
| One source splits to 2-3 targets below | **Inline SVG `.layer-split`** (self-contained viewBox) |
| Dashed/dotted variant arrows           | **CSS `.layer-arrow--dashed` / `--dotted`**            |
| Degraded / fallback between layers     | **CSS `.layer-arrow--warn`**                           |
| Visual separation without arrow        | **CSS `.layer-divider`** (simple `<hr>`)               |

---

## SVG Connector System (Advanced — Absolute Positioning Only)

> **⚠ Use this ONLY when nodes are positioned with `position: absolute` and known pixel values.** Do NOT combine SVG connectors with Flexbox/Grid layouts — use the CSS Layer Arrow System above instead.

For diagrams requiring complex cross-cutting connections (non-layered relationships, diagonal links, etc.), use a static SVG overlay with absolute-positioned nodes. Since both nodes and SVG coordinates share the same pixel-based coordinate system, alignment is guaranteed without JavaScript.

### Marker Definitions

Place these in the `<defs>` block of every diagram SVG. They define reusable arrowheads and endpoint shapes.

> **⚠ Critical: Do NOT use CSS custom properties (e.g. `var(--c-text-main)`) inside SVG `<marker>` elements.** CSS variables are NOT resolved inside `<marker>` in most browsers (Chrome, Safari, Firefox all affected). Always use hardcoded hex color values in marker `fill` and `stroke` attributes. This is the #1 cause of "invisible arrows".

```html
<defs>
  <!-- Standard arrow (for data flow, calls, dependencies) -->
  <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d1d1f" />
  </marker>

  <!-- Subtle arrow (secondary relationships) -->
  <marker id="arrow-sub" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="#6e6e73" />
  </marker>

  <!-- Open arrow (interface / abstract dependency) -->
  <marker id="arrow-open" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9" fill="none" stroke="#1d1d1f" stroke-width="1.5" />
  </marker>

  <!-- Diamond (composition / ownership) -->
  <marker id="diamond" viewBox="0 0 14 10" refX="13" refY="5" markerWidth="10" markerHeight="8" orient="auto">
    <path d="M 0 5 L 7 0 L 14 5 L 7 10 z" fill="#1d1d1f" />
  </marker>

  <!-- Empty diamond (aggregation) -->
  <marker id="diamond-open" viewBox="0 0 14 10" refX="13" refY="5" markerWidth="10" markerHeight="8" orient="auto">
    <path d="M 0 5 L 7 0 L 14 5 L 7 10 z" fill="#ffffff" stroke="#1d1d1f" stroke-width="1.5" />
  </marker>

  <!-- Circle dot (association endpoint) -->
  <marker id="dot" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
    <circle cx="5" cy="5" r="3.5" fill="#1d1d1f" />
  </marker>

  <!-- Tint arrow (highlighted key path) -->
  <marker id="arrow-tint" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="#0071e3" />
  </marker>

  <!-- Warning arrow (degraded / fallback / retry path) -->
  <marker id="arrow-warn" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="#ff9500" />
  </marker>

  <!-- Accent arrow (error / critical path) -->
  <marker id="arrow-accent" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="#d70015" />
  </marker>
</defs>
```

### Relationship Types

Use the following semantic classes to express different types of relationships:

| Class              | Line Style   | Start Marker    | End Marker      | Semantic Meaning                  |
| ------------------ | ------------ | --------------- | --------------- | --------------------------------- |
| `.conn--flow`      | Solid 1.5px  | —               | `#arrow`        | Data flow, method call, request   |
| `.conn--dep`       | Dashed 1.5px | —               | `#arrow`        | Dependency, import                |
| `.conn--bidi`      | Solid 1.5px  | `#arrow`        | `#arrow`        | Bidirectional communication       |
| `.conn--compose`   | Solid 1.5px  | `#diamond`      | `#arrow`        | Composition (A owns B)            |
| `.conn--aggregate` | Solid 1.5px  | `#diamond-open` | `#arrow`        | Aggregation (A contains ref to B) |
| `.conn--impl`      | Dashed 1.5px | —               | `#arrow-open`   | Implements / Realizes             |
| `.conn--assoc`     | Solid 1px    | `#dot`          | `#arrow-sub`    | Weak association                  |
| `.conn--event`     | Dotted 1.5px | —               | `#arrow`        | Event / async message             |
| `.conn--warn`      | Dashed 2px   | —               | `#arrow-warn`   | Degraded / fallback / retry path  |
| `.conn--critical`  | Solid 2px    | —               | `#arrow-accent` | Error path / critical flow        |
| `.conn--highlight` | Solid 2px    | —               | `#arrow-tint`   | Key path (tint, one per diagram)  |

```css
/* Base connector */
.conn {
  fill: none;
  stroke: #d2d2d7;
  stroke-width: 1.5;
}

/* Relationship modifiers — MUST set both stroke color and marker-end explicitly */
.conn--flow {
  stroke: #1d1d1f;
  marker-end: url(#arrow);
}
.conn--dep {
  stroke: #1d1d1f;
  stroke-dasharray: 6 4;
  marker-end: url(#arrow);
}
.conn--bidi {
  stroke: #1d1d1f;
  marker-start: url(#arrow);
  marker-end: url(#arrow);
}
.conn--compose {
  stroke: #1d1d1f;
  marker-start: url(#diamond);
  marker-end: url(#arrow);
}
.conn--aggregate {
  stroke: #1d1d1f;
  marker-start: url(#diamond-open);
  marker-end: url(#arrow);
}
.conn--impl {
  stroke: #1d1d1f;
  stroke-dasharray: 6 4;
  marker-end: url(#arrow-open);
}
.conn--assoc {
  stroke: #6e6e73;
  stroke-width: 1;
  marker-start: url(#dot);
  marker-end: url(#arrow-sub);
}
.conn--event {
  stroke: #6e6e73;
  stroke-dasharray: 2 4;
  marker-end: url(#arrow-sub);
}
.conn--warn {
  stroke: #ff9500;
  stroke-width: 2;
  stroke-dasharray: 6 4;
  marker-end: url(#arrow-warn);
}
.conn--critical {
  stroke: #d70015;
  stroke-width: 2;
  marker-end: url(#arrow-accent);
}

/* Emphasis — the key path, in the tint color (one per diagram) */
.conn--highlight {
  stroke: #0071e3;
  stroke-width: 2;
  marker-end: url(#arrow-tint);
}
```

### Connector Routing Rules

1. **Prefer orthogonal (right-angle) polylines** — straight horizontal and vertical segments joined at 90° turns. This is the default for all connections.
2. **Use `<polyline>`** for L-shaped or Z-shaped routes between nodes.
3. **Use `<line>`** only for perfectly horizontal or vertical direct connections.
4. **Use `<path>` with cubic Bezier (`C`) or quadratic (`Q`) curves** ONLY when orthogonal routes would cause excessive line crossings.
5. **Minimum clearance**: connectors must maintain at least 8px distance from any node border they are not connected to.
6. **Terminate at node edge midpoints**: connectors should start/end at the center of a node's top, bottom, left, or right edge — never at corners.

```html
<!-- Straight horizontal -->
<line class="conn conn--flow" x1="200" y1="100" x2="450" y2="100" />

<!-- L-shaped orthogonal route: exits bottom, turns right -->
<polyline class="conn conn--flow" points="200,150 200,220 450,220" />

<!-- Z-shaped orthogonal route: exits right, goes down, turns right -->
<polyline class="conn conn--dep" points="300,100 370,100 370,220 450,220" />

<!-- Curved (only when avoiding crossings) -->
<path class="conn conn--flow" d="M 200,150 C 200,250 450,150 450,250" />
```

### Connector Labels

Labels on connectors describe the relationship (protocol, method name, event type, etc.). Since SVG `<text>` has no background, use a `<rect>` + `<text>` pair for legibility. Background rect MUST use hardcoded fill color (`#ffffff`), not CSS variables.

```html
<!-- Label with background mask -->
<rect x="295" y="90" width="60" height="16" rx="0" fill="#ffffff" />
<text class="conn-label" x="325" y="102" text-anchor="middle">HTTP/REST</text>
```

```css
.conn-label {
  font-family: var(--font-mono);
  font-size: 10px;
  fill: #6e6e73;
  pointer-events: none;
}
```

Labels on colored connectors take the matching text color: `#0071e3` on a highlight path, `#b25000` on a warning path, `#d70015` on an error path.

Place labels at the visual midpoint of the connector. For polylines, place labels on the longest segment. For vertical connectors, place labels to the right of the line (`text-anchor: start`) to avoid overlapping. For Z-shaped connectors, place labels centered on the horizontal segment.

### Minimal Working Example (3 nodes + 2 orthogonal polylines)

Copy-paste-runnable template for **non-layered** diagrams. Use this as your starting point whenever you need SVG connectors between absolute-positioned nodes.

**Coordinate system contract (memorize this):**

- The `.canvas` container is `position: relative` with an explicit `width` and `height` in `px`. This is the coordinate origin.
- Every node uses `position: absolute` with `left/top` in `px`. `left/top` refer to the node's **top-left corner**.
- The overlay `<svg>` is `position: absolute; left: 0; top: 0` and covers the entire canvas. Its internal coordinate system (in `px`, no `viewBox` needed) is identical to the canvas coordinate system.
- Connector endpoints are computed as: `(node.left + edgeOffsetX, node.top + edgeOffsetY)` where `edgeOffset` is the midpoint of the node's top/bottom/left/right edge. So for a 160×60 node at `(40, 40)`: right-edge midpoint = `(40+160, 40+30) = (200, 70)`.
- Turn points on orthogonal polylines are chosen at a shared X (for horizontal-then-vertical) or shared Y (vertical-then-horizontal) between source and target.

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <style>
      :root {
        --c-bg: #f5f5f7;
        --c-canvas: #ffffff;
        --c-border: #d2d2d7;
        --c-text-main: #1d1d1f;
        --c-text-sub: #6e6e73;
        --font-ui: system-ui, -apple-system, sans-serif;
        --font-mono: 'SF Mono', Monaco, Consolas, monospace;
      }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { background: var(--c-bg); font-family: var(--font-ui); padding: 40px; }

      /* Absolute-positioned coordinate system */
      .canvas {
        position: relative;
        width: 720px;
        height: 320px;
        background: var(--c-canvas);
        border: 1px solid var(--c-border);
        margin: 0 auto;
      }

      /* Node: fixed size for predictable edge coordinates */
      .node {
        position: absolute;
        width: 160px;
        height: 60px;
        background: #ffffff;
        border: 1px solid var(--c-border);
        padding: 10px 14px;
      }
      .node__title { font-size: 13px; font-weight: 600; color: var(--c-text-main); }
      .node__desc { font-size: 11px; color: var(--c-text-sub); margin-top: 2px; }

      /* Overlay: shares canvas coordinate system */
      .connectors {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        overflow: visible;
      }

      .conn { fill: none; stroke-width: 1.5; }
      .conn--flow { stroke: #1d1d1f; marker-end: url(#mwe-arrow); }
      .conn--dep  { stroke: #1d1d1f; stroke-dasharray: 6 4; marker-end: url(#mwe-arrow); }
      .conn-label { font-family: var(--font-mono); font-size: 10px; fill: #6e6e73; }
    </style>
  </head>
  <body>
    <div class="canvas">
      <!--
        Node layout (all in canvas coordinates):
          Client   at (40, 130) → right edge midpoint  = (200, 160)
          Gateway  at (280, 130) → left edge midpoint  = (280, 160)
                                   right edge midpoint = (440, 160)
          Service  at (520, 40)  → left edge midpoint  = (520, 70)
      -->
      <div class="node" style="left: 40px; top: 130px;">
        <div class="node__title">Client</div>
        <div class="node__desc">Browser / App</div>
      </div>
      <div class="node" style="left: 280px; top: 130px;">
        <div class="node__title">Gateway</div>
        <div class="node__desc">Auth + Routing</div>
      </div>
      <div class="node" style="left: 520px; top: 40px;">
        <div class="node__title">Service</div>
        <div class="node__desc">Business Logic</div>
      </div>

      <svg class="connectors">
        <defs>
          <marker id="mwe-arrow" viewBox="0 0 10 10" refX="10" refY="5"
                  markerWidth="8" markerHeight="8" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d1d1f" />
          </marker>
        </defs>

        <!-- Client → Gateway: straight horizontal (both at y=160) -->
        <polyline class="conn conn--flow" points="200,160 280,160" />
        <rect x="220" y="150" width="40" height="14" fill="#ffffff" />
        <text class="conn-label" x="240" y="161" text-anchor="middle">HTTP</text>

        <!-- Gateway → Service: L-shape (exit right at y=160, turn up at x=480, enter left at y=70) -->
        <polyline class="conn conn--dep" points="440,160 480,160 480,70 520,70" />
        <rect x="484" y="107" width="44" height="14" fill="#ffffff" />
        <text class="conn-label" x="506" y="118" text-anchor="middle">gRPC</text>
      </svg>
    </div>
  </body>
</html>
```

**Checklist before submitting a non-layered diagram:**

1. Container has `position: relative` and explicit `width` + `height` in `px`.
2. Every node has `position: absolute` with `left/top` in `px` **including the `px` unit** (see Pitfall §2).
3. Overlay SVG has `position: absolute; left: 0; top: 0; width: 100%; height: 100%; overflow: visible`. No `viewBox` — internal units already equal container pixels.
4. Marker `fill`/`stroke` are hardcoded hex, not `var(...)` (see Pitfall §1).
5. Each polyline turn is exactly 90° (only horizontal + vertical segments).
6. Each endpoint sits on an edge midpoint of its source/target node, not a corner.
7. Label `<rect>` background uses `fill="#ffffff"` (not `var(--c-canvas)`, see Pitfall §5).

---

## Node System

### Basic Node

Nodes are HTML elements positioned via CSS Grid, Flexbox, or `position: absolute`.

```css
.node {
  background: var(--c-canvas);
  border: 1px solid var(--c-border);
  padding: 12px 16px;
}

.node__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-main);
  margin-bottom: 4px;
}

.node__desc {
  font-size: 11px;
  color: var(--c-text-sub);
}

.node__badge {
  margin-top: 8px;
}
```

### Node Positioning

Use Flexbox or CSS Grid for node layout (see §Layout Structure). Nodes should flow naturally in rows/layers without `position: absolute`.

For diagrams that require SVG connectors (see §SVG Connector System), use `position: absolute` with explicit `px` values on nodes. In that case, the SVG connector coordinates must match the node positions directly.

### Group / Container Node

For logical grouping (e.g., "Backend Services", "AWS Region"):

```css
.group {
  border: 1px dashed var(--c-border);
  padding: 24px 16px 16px;
  position: relative;
}

.group__label {
  position: absolute;
  top: -10px;
  left: 12px;
  background: var(--c-canvas);
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--c-text-sub);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
```

---

## Common Components

### Badge

```css
.badge {
  display: inline-block;
  font-size: 10px;
  font-family: var(--font-mono);
  padding: 2px 6px;
  border: 1px solid var(--c-text-main);
  text-transform: uppercase;
}

.badge--filled {
  background: var(--c-text-main);
  color: var(--c-canvas);
}

.badge--tint {
  border-color: var(--c-tint);
  color: var(--c-tint);
}

.badge--warn {
  border-color: var(--c-warn);
  color: var(--c-warn-text);
}

.badge--accent {
  border-color: var(--c-accent);
  color: var(--c-accent);
}
```

### Monospace Text

```css
.mono {
  font-family: var(--font-mono);
  font-size: 13px;
}
```

### Legend

Every diagram with 2+ relationship types MUST include a legend:

> **⚠ Important:** Each legend item uses a small independent `<svg>` element. SVG `<marker>` definitions are scoped to the `<svg>` they belong to — a `<line>` inside one `<svg>` **cannot** reference a `<marker>` defined in another `<svg>`. Therefore, every legend `<svg>` MUST include its own `<defs>` with the marker it uses, using a unique marker `id` to avoid conflicts.

```html
<div class="legend">
  <div class="legend__title">LEGEND</div>
  <div class="legend__items">
    <div class="legend__item">
      <svg width="40" height="12">
        <defs>
          <marker id="lg-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d1d1f" />
          </marker>
        </defs>
        <line x1="0" y1="6" x2="32" y2="6" stroke="#1d1d1f" stroke-width="1.5" marker-end="url(#lg-arrow)" />
      </svg>
      <span>Data Flow</span>
    </div>
    <div class="legend__item">
      <svg width="40" height="12">
        <defs>
          <marker id="lg-arrow-sub" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#6e6e73" />
          </marker>
        </defs>
        <line x1="0" y1="6" x2="32" y2="6" stroke="#6e6e73" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#lg-arrow-sub)" />
      </svg>
      <span>Dependency</span>
    </div>
    <!-- more items — each with its own <defs> -->
  </div>
</div>
```

```css
.legend {
  border-top: 1px solid var(--c-border);
  margin-top: 24px;
  padding-top: 16px;
}

.legend__title {
  font-size: 10px;
  font-weight: 600;
  color: var(--c-text-sub);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.legend__items {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.legend__item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--c-text-sub);
}

.legend__item svg {
  overflow: visible;
}
```

---

## Common Pitfalls

These are validated through real-world diagram generation failures. **Treat every item below as a hard rule.**

### 1. CSS Variables Inside SVG `<marker>` Are Invisible

`fill="var(--c-text-main)"` inside `<marker>` `<path>` will NOT render in most browsers. The arrowhead becomes transparent/invisible. **Always use hardcoded hex values** (e.g. `fill="#1d1d1f"`).

This also applies to: `stroke`, `fill` on `<circle>`, `<rect>`, and any attribute inside `<marker>`, `<pattern>`, `<clipPath>`, etc.

CSS variables work fine on regular SVG elements (`<line>`, `<polyline>`, `<rect>`, `<text>`) that are direct children of `<svg>` — the restriction is specific to elements inside `<defs>`.

### 2. CSS `position: absolute` Requires `px` Units

When positioning nodes with `style="left:330; top:0;"`, the missing `px` unit makes the value invalid in CSS. Always write `left: 330px; top: 0px;`. This is easy to overlook and causes all absolute-positioned nodes to stack at (0,0).

### 3. Do NOT Use JavaScript to Draw SVG Connectors Over Flexbox/Grid Layouts

Using `getBoundingClientRect()` to measure Flexbox/Grid node positions and then drawing SVG `<polyline>` connectors is fragile and error-prone:

- The SVG's positioning context easily mismatches the measurement reference (e.g., SVG anchored to `diagram-canvas` but coordinates calculated relative to `diagram-body` → offset by header height)
- Coordinates are stale on viewport resize unless a `ResizeObserver` is added (and the LLM will forget this)
- The approach has too many subtle failure modes for reliable LLM generation

**Instead, use CSS Layer Arrows (§Layer Arrow System) for Flexbox/Grid layouts.** Only use SVG connectors with absolute-positioned nodes where coordinates are static and known.

### 4. Legend SVGs Cannot Reference Main Diagram Markers

`<marker id="arrow">` defined in the main diagram SVG is not accessible from a separate `<svg>` element in the legend. Each legend `<svg>` must embed its own `<defs>` with uniquely-named markers (e.g. `id="lg-arrow"`).

### 5. SVG `<rect>` Background for Labels Also Needs Hardcoded Colors

`fill="var(--c-canvas)"` on a connector label background `<rect>` may not resolve inside SVG. Use `fill="#ffffff"` directly.

### 6. Connector CSS Classes Must Set Both `stroke` and `marker-end`

The `.conn--flow` class must explicitly set `stroke: #1d1d1f; marker-end: url(#arrow);` — not just `marker-end` alone. Without an explicit `stroke`, the line inherits the base `.conn` stroke color which may be the border color, making the arrow direction hard to distinguish visually.

### 7. Draw Every `orient="auto"` Marker Pointing Right

With `orient="auto"`, the browser rotates the marker so its +x axis follows the line direction. A marker path must therefore point to the right (e.g. `M 0 1 L 10 5 L 0 9`) with `refX` on its tip, even when the line runs downward. A path drawn pointing down gets rotated a second time and renders sideways.

---

## Critical Requirements

1. Use ONLY system fonts — NO external CDN (like Google Fonts)
2. Return ONLY the complete HTML content — NO markdown code blocks
3. HTML must be a complete, self-contained document with `<!DOCTYPE html>`
4. All styles must be inline within `<style>` tags. **No JavaScript** unless using SVG connectors with absolute positioning.
5. Prefer Chinese text when appropriate, use system fonts
6. **When the diagram contains 2+ entities, MUST express relationships visually. Use CSS Layer Arrows between layers (§Layer Arrow System) or SVG connectors for absolute-positioned nodes.**
7. **Every SVG connector must use a semantic class from the Relationship Types table.**
8. **Diagrams with 2+ connector types must include a Legend section.**
9. **NEVER use CSS custom properties (`var()`) inside SVG `<marker>`, `<pattern>`, or `<clipPath>` elements. Use hardcoded hex color values.**
10. **Every connector CSS class MUST set both `stroke` color and `marker-end` (or `marker-start`) explicitly.**
11. **Legend `<svg>` elements MUST include their own `<defs>` with uniquely-named markers.**
12. **Do NOT use JavaScript `getBoundingClientRect()` to draw SVG connectors over Flexbox/Grid layouts.** Use CSS Layer Arrows instead.
13. **All CSS `position: absolute` values MUST include `px` units.**
14. **For layered architecture diagrams, prefer CSS `.layer-arrow` and `.layer-split` over SVG connectors.**

---

## Output Template

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>[Diagram Title]</title>
    <style>
      :root {
        --c-bg: #f5f5f7;
        --c-canvas: #ffffff;
        --c-border: #d2d2d7;
        --c-hairline: #e8e8ed;
        --c-text-main: #1d1d1f;
        --c-text-sub: #6e6e73;
        --c-tint: #0071e3;
        --c-warn: #ff9500;
        --c-warn-text: #b25000;
        --c-accent: #d70015;
        --font-ui: system-ui, -apple-system, 'Segoe UI', sans-serif;
        --font-mono: 'SF Mono', Monaco, Consolas, monospace;
      }

      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        background: var(--c-bg);
        font-family: var(--font-ui);
        color: var(--c-text-main);
        padding: 40px;
      }

      .diagram-canvas {
        background: var(--c-canvas);
        border: 2px solid var(--c-border);
        padding: 32px;
        max-width: 1200px;
        margin: 0 auto;
        position: relative;
      }

      .diagram-header {
        border-bottom: 1px solid var(--c-border);
        padding-bottom: 16px;
        margin-bottom: 24px;
      }

      .diagram-title {
        font-size: 24px;
        font-weight: 600;
        color: var(--c-text-main);
      }

      .diagram-subtitle {
        font-size: 12px;
        font-weight: 500;
        color: var(--c-text-sub);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
      }

      .diagram-body {
        display: flex;
        flex-direction: column;
        gap: 0;
      }

      /* ── Layer Arrow (CSS-only, primary connector method) ── */
      .layer-arrow {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 32px;
        position: relative;
      }
      .layer-arrow::before {
        content: '';
        display: block;
        width: 1.5px;
        height: 100%;
        background: #1d1d1f;
      }
      .layer-arrow::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #1d1d1f;
      }
      .layer-arrow__label {
        position: absolute;
        left: calc(50% + 10px);
        top: 50%;
        transform: translateY(-50%);
        font-size: 10px;
        font-family: var(--font-mono);
        color: #6e6e73;
        white-space: nowrap;
        background: #ffffff;
        padding: 0 4px;
      }

      /* Dashed variant */
      .layer-arrow--dashed::before {
        background: repeating-linear-gradient(to bottom, #6e6e73 0, #6e6e73 4px, transparent 4px, transparent 8px);
      }
      .layer-arrow--dashed::after {
        border-top-color: #6e6e73;
      }

      /* Dotted variant */
      .layer-arrow--dotted::before {
        background: repeating-linear-gradient(to bottom, #6e6e73 0, #6e6e73 2px, transparent 2px, transparent 6px);
      }
      .layer-arrow--dotted::after {
        border-top-color: #6e6e73;
      }

      /* Warning variant */
      .layer-arrow--warn::before {
        width: 2px;
        background: repeating-linear-gradient(to bottom, #ff9500 0, #ff9500 4px, transparent 4px, transparent 8px);
      }
      .layer-arrow--warn::after {
        border-top-color: #ff9500;
      }
      .layer-arrow--warn .layer-arrow__label {
        color: #b25000;
      }

      /* Branching split */
      .layer-split {
        display: flex;
        justify-content: center;
        height: 36px;
      }
      .layer-split svg {
        overflow: visible;
        max-width: 700px;
      }

      /* Layer divider (no arrow) */
      .layer-divider {
        margin: 18px 0;
        border: none;
        border-top: 1px solid var(--c-hairline);
      }

      /* Node */
      .node {
        background: var(--c-canvas);
        border: 1px solid var(--c-border);
        padding: 12px 16px;
      }

      .node__title {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 4px;
      }
      .node__desc {
        font-size: 11px;
        color: var(--c-text-sub);
      }

      /* Group */
      .group {
        border: 1px dashed var(--c-border);
        padding: 24px 16px 16px;
        position: relative;
      }

      .group__label {
        position: absolute;
        top: -10px;
        left: 12px;
        background: var(--c-canvas);
        padding: 0 6px;
        font-size: 11px;
        font-weight: 600;
        color: var(--c-text-sub);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      /* Badge */
      .badge {
        display: inline-block;
        font-size: 10px;
        font-family: var(--font-mono);
        padding: 2px 6px;
        border: 1px solid var(--c-text-main);
        text-transform: uppercase;
      }

      .badge--filled {
        background: var(--c-text-main);
        color: var(--c-canvas);
      }

      .badge--tint {
        border-color: var(--c-tint);
        color: var(--c-tint);
      }

      .badge--warn {
        border-color: var(--c-warn);
        color: var(--c-warn-text);
      }

      .badge--accent {
        border-color: var(--c-accent);
        color: var(--c-accent);
      }

      /* Mono text */
      .mono {
        font-family: var(--font-mono);
        font-size: 13px;
      }

      /* Legend */
      .legend {
        border-top: 1px solid var(--c-border);
        margin-top: 24px;
        padding-top: 16px;
      }

      .legend__title {
        font-size: 10px;
        font-weight: 600;
        color: var(--c-text-sub);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
      }

      .legend__items {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
      }

      .legend__item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        color: var(--c-text-sub);
      }

      .legend__item svg {
        overflow: visible;
      }
    </style>
  </head>
  <body>
    <div class="diagram-canvas">
      <div class="diagram-header">
        <h1 class="diagram-title">[Title]</h1>
        <p class="diagram-subtitle">[SUBTITLE IN UPPERCASE]</p>
      </div>

      <div class="diagram-body">
        <!-- Layer 1 -->
        <div class="layer">
          <!-- Nodes here -->
        </div>

        <!-- CSS Arrow between layers -->
        <div class="layer-arrow">
          <span class="layer-arrow__label">Label</span>
        </div>

        <!-- Layer 2 -->
        <div class="layer">
          <!-- Nodes here -->
        </div>

        <!-- More layers, arrows, dividers... -->
      </div>

      <!-- Legend (required when 2+ arrow types are used) -->
      <div class="legend">
        <div class="legend__title">Legend</div>
        <div class="legend__items">
          <!-- Legend items with inline SVG markers -->
        </div>
      </div>
    </div>
  </body>
</html>
```
