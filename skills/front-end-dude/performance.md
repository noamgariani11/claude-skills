# Performance — Core Web Vitals deep reference

Measure the real thing: CrUX p75 field data, or web-vitals.js in prod. Lighthouse is a diagnostic tool; it is not the score Google uses for ranking.

## LCP — Largest Contentful Paint (target ≤ 2.5s)

**Identify the LCP element first.** Chrome DevTools → Performance → LCP marker. Or:
```js
new PerformanceObserver(list => console.log(list.getEntries())).observe({ type: 'largest-contentful-paint', buffered: true })
```

**If it's an image:**
- Use `next/image` with `priority` prop on above-the-fold images.
- Set explicit `width`/`height` to prevent CLS.
- `fetchpriority="high"` on the raw `<img>` if not using `next/image`.
- Serve AVIF (smallest) or WebP. Sized via `sizes` attribute — don't send a 2000px image into a 400px slot.

**If it's text:**
- Preload fonts above the fold: `<link rel="preload" as="font" crossorigin>`.
- `next/font` self-hosts and generates the preload link automatically. Prefer it.
- Use `font-display: optional` to prevent render blocking; `swap` only when FOUT is acceptable.

**Eliminate render-blocking resources:**
- Inline critical CSS for above-the-fold content.
- Defer non-critical JS: `<script defer>` or `dynamic(() => import(...))`.
- Move third-party scripts to `<Script strategy="afterInteractive">` or `"lazyOnload"`.

**TTFB:** keep under 600ms at origin. Cache static pages at the CDN edge. Use `stale-while-revalidate` for semi-dynamic routes.

## INP — Interaction to Next Paint (target ≤ 200ms)

This is where modern React apps most commonly fail. INP measures the worst interaction latency at p75 across the session.

**Break long tasks (> 50ms blocks the next paint):**
```js
// Yield to the browser
await scheduler.yield() // Chrome 115+; polyfill with Promise.resolve()
// Or defer non-urgent updates
startTransition(() => setExpensiveState(value))
```

**Move heavy work off the main thread:**
- JSON parsing of large payloads → web worker
- Syntax highlighting, markdown rendering, hash computation → web worker
- `@shopify/react-web-worker` or `comlink` for ergonomic worker wrappers

**Input handling:**
- Debounce `input` (300ms) and `resize`/`scroll` (16ms rAF) event handlers.
- Batch state updates — React batches automatically in event handlers; `flushSync` defeats this, so avoid it.

**Large lists:**
- Virtualize with TanStack Virtual when the list exceeds ~50 items and each item is non-trivial.
- `overscan: 5` is usually right. Don't over-render.

**Minimize re-renders:**
- Push state down to the component that owns it — don't lift to global store unnecessarily.
- `useDeferredValue` for derived expensive renders (search results, filtered lists).
- `memo()` only when you've measured: wrap the expensive child, not the parent.
- Context causes ALL consumers to re-render on every context value change. Split contexts by update frequency.

**Measure INP in field conditions:**
```js
import { onINP } from 'web-vitals/attribution'
onINP(({ value, attribution }) => {
  console.log('INP:', value, 'element:', attribution.interactionTarget)
})
```

## CLS — Cumulative Layout Shift (target ≤ 0.1)

Layout shift happens when content moves after the first render.

- **Images and videos:** always set `width` + `height` (or `aspect-ratio`). The browser reserves space before the image loads.
- **Async content:** skeletons that match the real content's dimensions. Placeholder height must equal real height.
- **Injecting content above fold:** banners, cookie notices, A/B variant inserts. Reserve space with min-height before the content loads.
- **Font swap:** FOIT/FOUT causes layout shift. Use `font-display: optional` to skip swap entirely, or size-adjust the fallback font so the line height matches.
- **Embeds and iframes:** set explicit `height` on the container.

## Bundle hygiene

**Analyze first:**
```bash
ANALYZE=true next build  # requires @next/bundle-analyzer in next.config
```
Any client chunk > 170KB gzip warrants investigation.

**Dynamic import for heavy client-only deps:**
```tsx
const HeavyChart = dynamic(() => import('./HeavyChart'), { ssr: false })
```

**Tree-shake correctly:**
```ts
// Good — named import, tree-shaken
import { debounce } from 'lodash-es'
// Bad — entire lodash in the bundle
import _ from 'lodash'
```

**Common bundle offenders:**
- `date-fns` imported as default → use named imports
- `moment` → replace with `date-fns` or `dayjs`
- Icon libraries (heroicons, lucide) → import individual icons, not the barrel
- `lodash` → `lodash-es` with named imports
- `recharts` / `chart.js` → dynamic import, SSR off

**Polyfill audit:** check `browserslist` in `package.json`. Targeting modern browsers eliminates large polyfill bundles.
