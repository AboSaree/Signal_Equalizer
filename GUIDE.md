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
│   │   │   └── home/
│   │   │       ├── home.component.ts
│   │   │       ├── home.component.html
│   │   │       └── home.component.scss
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

The **Start** button on the homepage is wired to `HomeComponent.onStartClick()`
in `src/app/pages/home/home.component.ts`:

```typescript
onStartClick(): void {
  // TODO: Replace '/app' with the actual route path when ready
  this.router.navigate(['/app']);
}
```

**Steps to connect it to a real page:**

1. Create your functional page component (see Section 5).
2. Register it in `app.routes.ts` under the path `/app` (or whatever you choose).
3. Update the `router.navigate(['/app'])` call above to match.

That's it — no changes needed in the HTML template.

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
| `/app` | *(to be created)* | Main functioning page — wired to Start button |

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

---

## 13. Recommended Next Steps

| Priority | Task |
|---|---|
| 🔴 High | Add `src/assets/images/Equalizer.png` |
| 🔴 High | Create the main app page and wire the Start button (Section 6) |
| 🟡 Medium | Add a `404 / not-found` page component |
| 🟡 Medium | Create a shared `ButtonComponent` for reuse across pages |
| 🟢 Low | Add NgRx or a simple Angular service for shared state |
| 🟢 Low | Set up Karma / Jasmine unit tests for components |
| 🟢 Low | Configure CI/CD pipeline (GitHub Actions, etc.) |
| 🟢 Low | Replace placeholder `favicon.ico` with the real favicon |

---

## 14. Changelog

| Version | Date | Changes |
|---|---|---|
| v1 | Project init | Initial homepage replica — navbar, hero image, headline, body, Start button |
| v2 | UI refinements | • Removed navbar (logo + icon) from homepage<br>• Image vertically centered (`align-items: center` + `object-fit: contain`)<br>• "Equalizer" fully visible (removed `overflow: hidden`, added `white-space: nowrap`, adjusted `clamp` range)<br>• Start button centered relative to headline block (`align-self: center`) |

---

*Questions or changes? Update this file as the project evolves so the team
always has a single source of truth.*
