# Archetypes

Three live-persona archetypes (A/B/C) plus one adversarial observer. Each persona in a run gets exactly one of A/B/C, and all three must differ. The adversarial observer is separate and always runs as itself.

---

## Archetype A: The Skimmer

- **Viewport:** 1280x720
- **Snapshot style:** `snapshot -i` (interactive elements only — skips body text)
- **Click behavior:** clicks the FIRST prominent CTA without reading surrounding text
- **Text tolerance:** skips pages with >3 paragraphs of body text. Logs `SKIPPED: too much text`
- **Form behavior:** fills with minimal input ("fix ceiling", not full sentences)
- **Scroll:** never past 2 viewport heights
- **Timeout:** if something takes >3s with no visual feedback, logs FRICTION and moves on
- **Memory:** forgets fastest. Retains almost nothing from skipped text
- **Word budget:** ≤500 words for the entire session. Bail if bouncing.

**Chain of Thought voice:** short, impatient, visual.
> "Big button. Clicking it." "Too much text, scrolling past." "Where's the thing?"

**Gate handling.** Skimmer goals must be reachable from the surfaces the persona can hit. If Phase 0.7.5 detected a structural blocker (waitlist, paywall, manual approval) on the route the Skimmer's goal needs, do NOT proceed with that goal. Use the gate-handling choice the user picked in Phase 0.7.5 — test the gate as the feature, restrict to unauth surfaces, or substitute the **Casual Browser** archetype below. Don't run a Skimmer who is guaranteed to bounce in 2 steps and call that signal.

---

## Archetype B: The Careful Reader

- **Viewport:** 1440x900
- **Snapshot style:** `snapshot` (full tree — reads everything)
- **Click behavior:** checks what the CTA says, predicts the outcome, then clicks
- **Form behavior:** detailed realistic input. Full sentences. Uses edge cases like apostrophes in names, long text
- **Scroll:** entire page. Checks footer, fine print, terms links
- **Uses `links`:** to compare visible nav against all available links
- **Error handling:** reads every error message word for word
- **Memory:** retains more than the other archetypes

**Chain of Thought voice:** methodical, predictive, checks labels.
> "This button says 'Submit' but I haven't filled in the zip field. Let me check if it's required... red asterisk. I'll fill it first."

- **Word budget:** ≤800 words for the session. The Careful Reader is the most prone to sprawl — they read everything. Cap their narrative; route detail into the Bug List instead of the per-tester section.

---

## Archetype C: The Mobile Tapper

- **Viewport:** 375x812 (MANDATORY `viewport 375x812` before ANY page visit)
- **Snapshot style:** `snapshot -i -C` (interactive + cursor-interactive for tap targets)
- **Touch targets:** notes anything <44px as precision-tap risk
- **Menu test:** hamburger open/close, horizontal overflow
- **Form behavior:** shorter mobile-realistic input
- **Orientation test:** screenshots at both 375x812 and 812x375
- **Memory:** retains visuals better than text

**Chain of Thought voice:** spatial, thumb-aware, scroll-oriented.
> "Menu icon is tiny, top right. Thumb can barely reach... got it. Oh, it overlaps the content."

- **Word budget:** ≤600 words for the session.

---

## Archetype D: The Casual Browser (Skimmer substitute, gated-product mode)

Use only when Phase 0.7.5 detected a structural blocker AND the user picked "substitute Casual Browser" for that run.

- **Viewport:** 1280x720 (same as Skimmer)
- **Mindset:** curious, no urgency, no specific repair task. Browsing to evaluate whether the product is for them.
- **Click behavior:** explores the marketing landing, pricing, public tools — whatever's reachable without auth. Doesn't try to log in.
- **Text tolerance:** reads roughly two paragraphs before deciding "yes/no/maybe."
- **Goal:** "Decide in 90 seconds whether this product would help me." Success = a positive verdict on the unauth surfaces; partial = "interesting, would come back"; fail = "I don't get what this does, leaving."
- **Word budget:** ≤500 words.

**Chain of Thought voice:** evaluative, low-stakes, comparative.
> "OK so this is for home repairs. Cool. What can I actually try without signing up? ... Calculators. Useful. Pricing — $9/mo seems fine. Would I come back?"

This archetype produces signal where Skimmer would just bounce. It's strictly gated to "substitute when the original Skimmer goal is unreachable" — don't replace Skimmer by default.

---

## The Adversarial User (Chaos Agent)

Not one of A/B/C. Runs after the personas as the 5th observer.

- **Viewport:** 1280x720 desktop, then 375x812 mobile pass
- **Mindset:** distrustful, impatient, contrarian, easily distracted
- **Goal:** whatever the app's primary flow is, approached sideways

**Chain of Thought voice:** suspicious, creative, contrarian.
> "This form wants my email? I'm putting in 'notanemail'. Validated? Fine. What about 'a@b'? What about 300 characters? Now I'm bored — I'm hitting back to see if it saved anything."

**Tactics:**
1. **Input chaos:** emoji in text fields, multi-line in single-line, whitespace-only, special chars (`<script>`, `'; DROP TABLE--`, `../../etc/passwd`), 500+ char inputs, numbers where text is expected, empty required fields, garbage in optional fields
2. **Navigation abuse:** 5-10 rapid back clicks, same page in two tabs, deep-link mid-flow, bookmark-then-clear-cookies-then-revisit, forward after back, refresh during loading, close modal via outside click + Escape + X button
3. **Timing:** double-click submits, triple-click CTAs, click one then immediately another, type while loading, submit while previous submit is in flight
4. **State corruption:** complete flow then go back and redo, log out in another tab while interacting here, clear localStorage mid-session, rapid mobile/desktop resize, tab-bounce
5. **Trust / comprehension:** read error messages literally, test recovery paths, confirmation clarity, external link handling

---

## Diversity Enforcement

Before Phase 2A starts, SKILL.md runs a diversity check on the persona set. All three must differ on:

- **Age** (spread across ≥20 years)
- **Tech literacy** (pick from low/medium/high — no two can be the same)
- **Archetype** (A/B/C — all three used)
- **Domain knowledge** (low/medium/high — at least two different values)
- **Patience** (different across all three)
- **Primary goal** (different core flows)

If any axis collapses (e.g., two personas both "high tech literacy" and "careful reader"), regenerate the collapsed persona and re-check. Log the check result:

```
DIVERSITY CHECK: pass | axes confirmed: age, tech, archetype, domain, patience, goal
```

or

```
DIVERSITY CHECK: fail on [axis] — regenerating [Persona N]
```

---

## Return Visitor Persona (conditional)

One of the three personas may be a **return visitor** — but only if the app has state persistence. Before assigning this role, grep the source for persistence signals:

```bash
grep -r -l "localStorage\|sessionStorage\|cookies()\|getServerSession\|useSession\|auth()" src/ 2>/dev/null | head -5
```

- **If persistence signals exist:** one persona gets `VISIT TYPE: return`. Their test focuses on: does the app remember them? Is onboarding skippable? Are preferences retained?
- **If no persistence signals exist:** all three personas are `VISIT TYPE: first`. Log in the report: "No state persistence detected — return-visitor testing skipped. This is itself a finding if the app is expected to remember users."

The other personas are `VISIT TYPE: first`.
