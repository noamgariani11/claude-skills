# Mode Specifics

This skill runs in one of three modes. The main SKILL.md handles intent detection. This file spells out exactly what each mode does in every phase.

---

## Full Mode

**Question answered:** "How does this whole app feel to real users?"

- 3 personas run, all different archetypes
- Route coverage: every route in the Phase 0 map visited by at least one persona
- Technical Reviewer audits console/network/a11y across all routes
- Adversarial User roams freely
- Codex (if available) gets a broad repo review prompt:
  ```
  codex exec "Run a thorough code review of this repository. Focus on things
  a user-driven test would NOT catch: correctness bugs, security issues, race
  conditions, auth boundaries, missing error handling, accessibility gaps in
  code, and UX code smells. Output a structured markdown report with
  Critical/High/Medium/Low severity tags, file:line references, and a 'Top 5
  highest-leverage fixes' section at the end." > "$_CODEX_OUT" 2>&1
  ```
- Report title: `User Test Report — [App Name]`

---

## Diff Mode

**Question answered:** "Does this change work from a user's perspective, and did it break anything nearby?"

Triggered by `--diff`, `--changes`, or a trigger phrase like "test my changes" / "pre-push review."

**Phase 0 additions:**
```bash
echo "=== UNSTAGED ==="; git diff --name-only
echo "=== STAGED ==="; git diff --cached --name-only
echo "=== UNTRACKED ==="; git ls-files --others --exclude-standard
git diff; git diff --cached
```

Build a **changes manifest**:
```
CHANGES MANIFEST:
  Files changed: [N]
  Routes affected: [list]
  Features affected: [list]
  Shared dependencies touched: [list — widens blast radius]
  Routes to test: [final list incl. blast radius]
```

**Behavior:**
- Persona count drops to 2 (one fast archetype + one careful archetype)
- Persona GOALs must directly exercise the changed code
- Routes not in the manifest are skipped
- Tech Reviewer + Adversarial User focus only on changed areas
- Codex prompt: `codex review > "$_CODEX_OUT" 2>&1`
- Report title: `Diff-Targeted User Test Report`
- Report includes a **Changes Under Test** table (file → route/feature → type of change)

---

## Focus Mode

**Question answered:** "Is this specific page or feature ready? Does every detail hold up under pressure?"

Triggered by `--focus <page-or-feature>` or a phrase like "deep test the maintenance page."

**Phase 0 additions:**
```bash
find src/app -name "page.tsx" -o -name "page.jsx" 2>/dev/null | sort
grep -r "<focus-keyword>" src/app --include="*.tsx" -l 2>/dev/null | head -10
```

Build a **focus manifest**:
```
FOCUS MANIFEST:
  Target: [page/feature name as given]
  Resolved route: [e.g. /dashboard/maintenance]
  File(s): [source paths]
  Sub-flows on this page: [modals, inline forms, tabs, steps contained within]
  Entry paths: [direct URL, navigated from X, deep-linked from Y]
```

Read the source for the focused page so you understand intended behavior before testing.

**Behavior:**
- All 3 personas test ONLY the focused page and its sub-flows
- Each persona arrives via a different entry path from the manifest
- Each persona runs 8–12 distinct actions on that page (depth > breadth)
- Persona GOALs must be scoped to actions available on that page — no goals that require leaving
- Tech Reviewer runs a deeper audit: full Tab traversal, console/network sweep, layout at 80%/100%/150% zoom, every interactive element
- Adversarial User exhausts every input and interaction surface on the page
- Codex prompt:
  ```
  codex exec "Review the focused page at <resolved-route> (source:
  <file-paths>). Audit every handler, interactive surface, and edge
  case. Flag anything brittle, unsafe, or inconsistent with the rest of
  the codebase. Markdown report with severity tags and file:line refs."
  > "$_CODEX_OUT" 2>&1
  ```
- Report title: `Focused User Test Report — [Page/Feature Name]`
- Report opens with a **Focus Target** section

---

## Mode Auto-Detection Heuristics

SKILL.md's Step 0 tries to infer mode from the trigger phrase before asking.

**Infer full mode if trigger contains:** "full review", "the whole app", "everything", "test the app", or no qualifier.

**Infer diff mode if trigger contains:** "my changes", "what I changed", "pre-push", "before push", "diff", "uncommitted", "unstaged", `--diff`, `--changes`.

**Infer focus mode if trigger contains:** "the X page", "just the X flow", "deep test X", "focus on X", "hyper test X", `--focus`. The target is whatever comes after those keywords.

If the trigger is ambiguous, ask the mode question. If it is clear, skip the question and confirm the inferred mode inline (one sentence: "Running in focus mode on the maintenance page — proceeding.").
