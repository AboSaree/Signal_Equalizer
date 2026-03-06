# SOFI APP — Developer Guide
> Last updated: after homepage UI refinements (v2)

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Folder Structure](#2-folder-structure)
3. [Getting Started](#3-getting-started)
4. [Design System](#4-design-system)
5. [Adding a New Page](#5-adding-a-new-page)
6. [Connecting the "Start" Button](#6-connecting-the-start-button)
7. [Adding New Components](#7-adding-new-components)
8. [Assets & Images](#8-assets--images)
9. [Environment Configuration](#9-environment-configuration)
10. [Routing Reference](#10-routing-reference)
11. [Styling Conventions](#11-styling-conventions)
12. [Homepage Layout Notes](#12-homepage-layout-notes)
13. [Recommended Next Steps](#13-recommended-next-steps)
14. [Changelog](#14-changelog)

---

## 1. Project Overview

| Item | Value |
|---|---|
| Framework | Angular 17 (standalone components) |
| Styling | SCSS + CSS custom properties |
| Fonts | DM Sans (Google Fonts) |
| State management | Angular services (add NgRx if complexity grows) |
| Routing | `@angular/router` |

The app follows a **feature-based folder structure** — each page lives in
`src/app/pages/<page-name>/` and each reusable UI piece lives in
`src/app/components/<component-name>/`.

---

## 2. Folder Structure

```
sofi-app/
├── src/
│   ├── app/
│   │   ├── app.component.ts          ← Root shell (router outlet only)
│   │   ├── app.config.ts             ← Bootstrap providers (router, animations)
│   │   ├── app.routes.ts             ← ALL routes defined here
│   │   │
│   │   ├── components/               ← Shared / reusable UI components
│   │   │   └── navbar/               ← Navbar exists but is NOT used on homepage
│   │   │       ├── navbar.component.ts
│   │   │       ├── navbar.component.html
│   │   │       └── navbar.component.scss
│   │   │
│   │   ├── pages/                    ← One subfolder per route/page
│   │   │   ├── home/
│   │   │   │   ├── home.component.ts
│   │   │   │   ├── home.component.html
│   │   │   │   └── home.component.scss
│   │   │   └── upload/               ← Upload page (routed from Start button)
│   │   │       ├── upload.component.ts
│   │   │       ├── upload.component.html
│   │   │       └── upload.component.scss
│   │   │
│   │   └── services/                 ← (create as needed)
│   │
│   ├── assets/
│   │   └── images/                   ← All images go here
│   │       └── Equalizer.png         ← Hero image (YOU must add this file)
│   │
│   ├── environments/
│   │   ├── environment.ts            ← Dev config
│   │   └── environment.prod.ts       ← Prod config
│   │
│   ├── index.html
│   ├── main.ts
│   └── styles.scss                   ← Global styles & CSS variables
│
├── angular.json
├── package.json
├── tsconfig.json
└── GUIDE.md                          ← You are here
```

---

## 3. Getting Started

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:4200)
npm start

# Build for production
npm run build
```

> **Node version:** 18+ recommended.

---

## 4. Design System

All design tokens live as CSS custom properties in `src/styles.scss`:

```scss
:root {
  --color-bg:         #f5f4f2;   /* off-white background */
  --color-black:      #0a0a0a;   /* headlines, buttons  */
  --color-white:      #ffffff;
  --color-accent:     #7b6ee0;   /* purple — device window colour */
  --color-text-muted: #5a5a5a;   /* body copy            */
  --font-primary:     'DM Sans', sans-serif;
  --transition-base:  0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow:  0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**To change the colour palette** — edit only these variables; all components
inherit them automatically.

---

## 5. Adding a New Page

### Step A — Create the component

```bash
# Using Angular CLI
ng generate component pages/my-new-page
```

Or create the files manually following the pattern in `src/app/pages/home/`.

### Step B — Register the route

Open `src/app/app.routes.ts` and add:

```typescript
{
  path: 'my-new-page',
  loadComponent: () =>
    import('./pages/my-new-page/my-new-page.component')
      .then(m => m.MyNewPageComponent),
  title: 'Sofi — My New Page'
}
```

Using `loadComponent` (lazy loading) keeps the initial bundle small.

---

## 6. Connecting the "Start" Button

The **Start** button navigates to `/app`, which is now fully wired to the
`UploadComponent` (`src/app/pages/upload/`).

```typescript
// home.component.ts
onStartClick(): void {
  this.router.navigate(['/app']);   // → UploadComponent
}
```

The route is registered in `app.routes.ts` using lazy loading:

```typescript
{
  path: 'app',
  loadComponent: () =>
    import('./pages/upload/upload.component')
      .then(m => m.UploadComponent),
  title: 'Sofi — Upload Signal'
}
```

**To redirect the Start button to a different page later:**

1. Create the new page component (see Section 5).
2. Register it in `app.routes.ts` under your chosen path.
3. Update `router.navigate(['/app'])` in `home.component.ts` to match.

---

## 7. Adding New Components

Shared components (used in more than one page) go in `src/app/components/`.

```bash
ng generate component components/my-widget
```

Page-specific components can also live inside their page folder:

```
pages/
  dashboard/
    dashboard.component.ts
    dashboard.component.html
    dashboard.component.scss
    components/            ← page-local sub-components
      stats-card/
```

> **Note on the Navbar component:** The navbar files exist in
> `src/app/components/navbar/` and are preserved for future use. The homepage
> intentionally does **not** render it (removed from `home.component.html` and
> `home.component.ts` imports). Re-add `<app-navbar>` and import
> `NavbarComponent` in any page that needs a top navigation bar.

---

## 8. Assets & Images

All static files go under `src/assets/`.

```
src/assets/
  images/          ← raster images (.png, .jpg, .webp)
  icons/           ← SVG icons (add as needed)
  fonts/           ← self-hosted fonts (add as needed)
```

Reference in templates:

```html
<!-- Served at /images/Equalizer.png thanks to angular.json asset mapping -->
<img src="images/Equalizer.png" alt="..." />
```

Reference in SCSS:

```scss
background-image: url('/assets/images/bg-texture.png');
```

> **Important:** The hero image must be placed at
> `src/assets/images/Equalizer.png` for the homepage to display correctly.
> The `angular.json` asset configuration maps `src/assets/images/` → `/images/`
> in the build output.

---

## 9. Environment Configuration

| File | Used when |
|---|---|
| `src/environments/environment.ts` | `ng serve` / development builds |
| `src/environments/environment.prod.ts` | `ng build` production |

Import in any service or component:

```typescript
import { environment } from '../../../environments/environment';

const apiUrl = environment.apiBaseUrl;
```

---

## 10. Routing Reference

| Path | Component | Notes |
|---|---|---|
| `/` | `HomeComponent` | Landing / hero page (no navbar) |
| `/app` | `UploadComponent` | Upload signal file — wired to Start button |

Add new rows to this table as you expand the app.

---

## 11. Styling Conventions

- **SCSS** for all component styles.
- **BEM** naming: `.block__element--modifier`.
- **No global class overrides** — component styles are encapsulated by Angular's ViewEncapsulation.
- Use **CSS custom properties** (`var(--color-black)`) rather than hard-coded hex values.
- Breakpoints (mobile-first):
  - `@media (max-width: 1100px)` — narrow desktop / large tablet
  - `@media (max-width: 900px)` — tablet / landscape phone
  - `@media (max-width: 480px)` — small phones

---

## 12. Homepage Layout Notes

The homepage (`HomeComponent`) has the following intentional design decisions
as of v2:

| Element | Behaviour | Where to change |
|---|---|---|
| **Navbar (logo + icon)** | Hidden — not rendered on homepage | `home.component.html` (do not add `<app-navbar>`) |
| **Hero image** | Vertically centered using `align-items: center` on wrapper + `object-fit: contain` | `home.component.scss` → `.hero__image-wrapper` |
| **"Equalizer" headline** | Fully visible — `overflow: hidden` removed, `white-space: nowrap` applied, font-size uses `clamp(4rem, 8vw, 8rem)` | `home.component.scss` → `.hero__headline` |
| **Start button** | Horizontally centered relative to the headline block via `align-self: center` on the button and `align-items: flex-start` on `.hero__content` | `home.component.scss` → `.hero__cta` |

### Re-enabling the navbar on the homepage

If you later need the navbar back on the homepage:

1. **`home.component.html`** — add `<app-navbar></app-navbar>` as the first element.
2. **`home.component.ts`** — add `NavbarComponent` to the `imports` array:
   ```typescript
   import { NavbarComponent } from '../../components/navbar/navbar.component';
   // ...
   imports: [NavbarComponent],
   ```
3. **`home.component.scss`** — restore top padding on `.hero__content`:
   ```scss
   padding-top: 5rem; // offset for fixed navbar
   ```

## 13. Cine Viewer — Dual Signal Display (Input & Output)

The **cine viewer** renders two side-by-side animated scrolling waveform canvases that appear below the upload UI after the user clicks **Analyse**. The left canvas shows the **Input Signal**; the right canvas shows the **Output Signal** (currently a mirror of the input — ready for you to apply processing). A single shared **control panel** below both canvases drives both simultaneously.

---

### Layout

```
┌─────────────────────┐  ┌─────────────────────┐
│   Input Signal      │  │   Output Signal      │
│   [canvas]          │  │   [canvas]           │
└─────────────────────┘  └─────────────────────┘
┌──────────────────────────────────────────────┐
│  Playback | Zoom | Speed | View (ctrl-panel) │
└──────────────────────────────────────────────┘
```

- On screens **≥ 860 px** the two canvases sit side by side (`flex-direction: row`).
- On screens **< 860 px** they stack vertically (`flex-direction: column`).
- The wrapper `.dual-viewer` expands up to `1720 px` to make the most of wide screens.
- The `.ctrl-panel-wrap` beneath it spans the full width of both canvases.

---

### CSV format expected

Two columns, no header row. Delimiter: comma, semicolon, or tab.

```
0,0.12
1,0.45
2,0.78
```

| Column | Meaning | Unit |
|---|---|---|
| First  | Time      | ms |
| Second | Amplitude | mV |

Rows that cannot be parsed are silently skipped.

---

### Architecture — how it works

#### History buffer
Every sample consumed by the playhead is pushed into `history: SignalSample[]`. This is the source of truth for all rendering — it enables panning into the past and re-rendering at any zoom level without re-reading the signal array.

#### Viewport window
Each render call computes a `windowSlice` — the subset of `history[]` that is currently visible — based on three factors:

| Factor | State property | Effect |
|---|---|---|
| Playhead position | `signalIndex` | How far into the signal we are |
| Pan offset | `panOffset` (samples) | How far back from the live head the view is |
| Zoom level | `pixelsPerSample` | How many canvas pixels one sample occupies |

```
samplesVisible = floor(plotW / pixelsPerSample)
headIdx        = history.length - 1 - panOffset
tailIdx        = headIdx - samplesVisible + 1
windowSlice    = history[tailIdx … headIdx]
```

#### Speed
`samplesPerFrame` controls how many samples are consumed per `requestAnimationFrame` tick. At 1 (default) the signal scrolls at one sample per frame (~60 smp/s at 60 fps). Increasing it speeds up playback without dropping samples.

---

### Axis labels & dynamic Y limits

- **Y-axis (mV):** computed once from global signal min/max with 10 % padding. Quarter-point values labelled at 0 %, 25 %, 50 %, 75 %, 100 % of plot height. Reset via **Reset** button.
- **X-axis (ms):** shows the actual time values of the current `windowSlice` — updates every frame as the buffer shifts. Quarter-point timestamps shown at 0 %, 25 %, 50 %, 75 %, 100 % of plot width.

---

### Panning (canvas drag)

Implemented directly on the `<canvas>` element via mouse and touch event listeners bound in `bindCanvasEvents()`.

| Gesture | Behaviour |
|---|---|
| Drag right | Move forward in time (decrease `panOffset`) |
| Drag left  | Go further back in history (increase `panOffset`) |
| Release    | Freeze pan offset; live playback continues |

A subtle **"Drag to pan"** label is displayed in the bottom-right corner of the canvas at all times.

---

### Control panel buttons

All controls live in `.ctrl-panel` below the canvas.

| Button | Group | Behaviour |
|---|---|---|
| **Stop**    | Playback | `cancelAnimationFrame` — freezes at current position. Disabled while paused. |
| **Resume**  | Playback | Re-enters RAF loop from current `signalIndex`. Disabled while playing or signal finished. |
| **Restart** | Playback | Clears `history`, resets `signalIndex` to 0 and `panOffset` to 0, restarts animation. |
| **Zoom +**  | Zoom | Multiplies `pixelsPerSample` by 1.1 → fewer ms visible (narrow window). Clamped to 50. |
| **Zoom −**  | Zoom | Divides `pixelsPerSample` by 1.1 → more ms visible (wide window). Clamped to 0.05. |
| **Speed +** | Speed | Multiplies `samplesPerFrame` by 1.1. Clamped to 200. |
| **Speed −** | Speed | Divides `samplesPerFrame` by 1.1. Clamped to 0.01. |
| **Reset**   | View | Restores `pixelsPerSample`, `samplesPerFrame`, `panOffset` to defaults; restores Y limits. Redraws immediately if paused. |

The **Speed** group shows a live badge (e.g. `1.0×`, `2.3×`) reflecting the current multiplier relative to the default.

---

### Key component properties

| Property | Type | Purpose |
|---|---|---|
| `signal` | `SignalSample[]` | Parsed CSV data — never mutated after parsing |
| `history` | `SignalSample[]` | All samples consumed so far — source for pan/zoom |
| `signalIndex` | `number` | Index of the next sample to consume from `signal` |
| `pixelsPerSample` | `number` | Current zoom level (default `1`) |
| `samplesPerFrame` | `number` | Current speed (default `1`) |
| `panOffset` | `number` | Samples behind live head (0 = live) |
| `yMin / yMax` | `number` | Current Y-axis range (reset via Reset) |
| `yMinBase / yMaxBase` | `number` | Original Y limits from signal data |
| `CANVAS_W/H` | `readonly` | Canvas pixel dimensions (800 × 260) |
| `PAD_*` | `readonly` | Plot area margins for axis label space |
| `canvasRef` | `ElementRef` | Reference to the left (Input Signal) canvas |
| `outputCanvasRef` | `ElementRef` | Reference to the right (Output Signal) canvas |

---

### Theming

The canvas uses a dark background (`#0d0d0d` / `#111111`) to contrast with the light page. The waveform is drawn in `--color-accent` (`#7b6ee0`) with a `shadowBlur: 6` glow.

The control panel (`.ctrl-panel`) sits on `--color-white` with a light border and subtle shadow, styled with four button variants:

| Class | Usage |
|---|---|
| `.ctrl-btn--primary` | Stop — solid black pill |
| `.ctrl-btn--outline` | Resume — accent-colour outline pill |
| `.ctrl-btn--ghost`   | Restart, Zoom ±, Speed ± — neutral tinted pill |
| `.ctrl-btn--reset`   | Reset — accent-tinted ghost pill |

---

## 14. Recommended Next Steps

| Priority | Task |
|---|---|
| 🔴 High | Add `src/assets/images/Equalizer.png` |
| 🔴 High | Connect `UploadComponent.onAnalyse()` to your signal-processing service |
| 🟡 Medium | Create a results / analysis page and navigate to it after file upload |
| 🟡 Medium | Add a `404 / not-found` page component |
| 🟡 Medium | Create a shared `ButtonComponent` for reuse across pages |
| 🟡 Medium | Add mouse-wheel zoom on the canvas |
| 🟢 Low | Add NgRx or a simple Angular service for shared state |
| 🟢 Low | Set up Karma / Jasmine unit tests for components |
| 🟢 Low | Configure CI/CD pipeline (GitHub Actions, etc.) |
| 🟢 Low | Replace placeholder `favicon.ico` with the real favicon |

---

## 15. Changelog

| Version | Date | Changes |
|---|---|---|
| v1 | Project init | Initial homepage replica — navbar, hero image, headline, body, Start button |
| v2 | UI refinements | • Removed navbar from homepage<br>• Image vertically centered<br>• "Equalizer" headline fully visible<br>• Start button centered |
| v3 | Upload page | • Created `UploadComponent` at `/app` route<br>• Drag-and-drop + click-to-upload drop zone<br>• "Analyse" CTA button<br>• Back arrow<br>• Fully themed |
| v4 | Cine viewer | • Canvas-based scrolling waveform<br>• Appears after "Analyse" click<br>• Parses two-column CSV (time ms, value mV)<br>• Dynamic Y-axis limits<br>• X-axis with actual time values<br>• Quarter-point tick labels on both axes<br>• Stop / Resume buttons<br>• Accent waveform with glow |
| v5 | Cine controls & pan | • History buffer architecture replacing simple FIFO<br>• Canvas drag-to-pan (mouse + touch)<br>• Restart button — replays from sample 0<br>• Zoom + / − buttons (±10 % pixelsPerSample)<br>• Speed + / − buttons (±10 % samplesPerFrame) with live badge<br>• Reset button — restores zoom, speed, pan, Y limits<br>• `.ctrl-panel` component with grouped layout and four button variants<br>• GUIDE.md Section 13 fully updated |
| v5.1 | Pan fixes | • Reversed pan direction — drag right moves forward in time (matches standard chart behaviour)<br>• Removed pan offset indicator text from canvas top-right |
| v5.2 | Dual-plot layout | • Added second (Output Signal) canvas to the right of Input Signal<br>• Single shared control panel drives both plots simultaneously<br>• Responsive: side-by-side ≥ 860 px, stacked < 860 px<br>• `.dual-viewer` wrapper expands to 1720 px for wide screens<br>• `outputCanvasRef` ViewChild wired to separate `<canvas #outputCanvas>`<br>• `renderCanvas()` called for both contexts each frame/pause redraw<br>• GUIDE.md Section 13 updated with dual-viewer layout docs |
| v5.2.1 | Upload section alignment | • Restored `align-items: center` on `.upload-page` — upload block re-centred; dual-viewer and ctrl-panel-wrap remain full-width beneath it |

---

*Questions or changes? Update this file as the project evolves so the team always has a single source of truth.*
