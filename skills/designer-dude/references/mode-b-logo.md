# Mode B - Logo / brand mark

## Question sequence

Seven questions, **one at a time**, via `AskUserQuestion`. Do not list them
all at once. Reflect the previous answer in the next question's framing.

1. What does the product actually do, in one plain sentence?
2. Who is the target person? Be specific - not "everyone".
3. Three adjectives, at least one surprising (not "clean", "bold", "modern").
4. Color intuition: any colors you are drawn to, or ones you would ban?
5. Form preference: wordmark, symbol, lettermark, or combination mark?
6. An existing logo you admire - any industry. Tell me why.
7. Versatility priority: where does it live most - favicon, app icon,
   embroidery, billboard?

Question 7 is not filler. It determines how much detail the mark can carry:
a mark that lives at 16px in a browser tab and a mark that lives on a
building are different briefs, and trying to serve both without saying so
is how you get a logo that works nowhere.

Three directions per round: **safe / distinctive / wildcard.**

---

## Simplicity & survival tests

**All must pass.** Fail any → back to the board.

- **Squint test** - does the silhouette survive blur?
- **Favicon at 16px** - does it still read?
- **Single-color** - does it hold without color?
- **T-shirt at 30ft / billboard at 60mph** - does it read from distance?
- **Dark-mode invert** - does it work inverted, or does it need a dedicated
  dark variant? (Needing one is fine. Not having noticed is not.)
- **App-icon row** - place it beside nine real iOS home-screen icons. Does
  it hold its own, or vanish into the grid?
- **AI-sniff test** - does it look Midjourney-generated? Tells: gradient
  foil letters, faux lens flares, excessive bevel, that uncanny
  "vector but soft" feel, over-rendered 3D, aurora borealis for no reason.
  If yes, burn it.

**Run these in a browser, not in your head.** Five of the seven are literally
questions about rendering, and an SVG that reads fine as source can turn to
mud at 16px because a 1px stroke fell between pixels. Build a
`logo-tests.html` that lays the mark out at 16 / 24 / 32 / 64 / 512px, once in
full colour, once in a single colour, once inverted on the dark surface, once
blurred (`filter: blur(3px)`), and once in a row beside nine real app icons.
Then serve and look at it through the `browse` skill:

```bash
BASE=$(~/.claude/skills/browse/serve.sh --dir design-explore/{date})
# browser_navigate $BASE/logo-tests.html  →  screenshot  →  READ the screenshot
```

Also drop it in as a real `<link rel="icon">` and look at the actual browser
tab: the favicon test is about the tab, and that is the one place a screenshot
of the page cannot show you. `browser-verification.md` has the session order
and the screenshot conventions.

### Two more that catch real failures

- **The describe-it-over-the-phone test.** If you cannot describe the mark
  in one sentence such that someone could roughly sketch it, it is too
  complex to become memorable.
- **The prior-art check.** Before presenting, search for the mark's core
  form plus the industry. A lettermark in a circle has been done ten
  thousand times; you are looking for an actual collision with a known
  brand in an adjacent category. **You are not clearing it legally** - say
  so explicitly and tell the user a trademark search by a professional is a
  separate, necessary step before they commit. Never imply a mark is
  legally safe to use.

---

## Deliverable

- **`LOGO-BRIEF.md`** - the brief, the three directions, the reasoning, the
  survival-test results per direction.
- **Optional `logo-skeleton.svg`** - construction geometry, not a finished
  mark: the grid, the proportions, the optical corrections.

Be honest about the medium. You are working in text and SVG, not in
Illustrator with a type designer. A skeleton and a rigorous brief that a
human designer can execute against is a genuinely useful deliverable. A
half-rendered SVG presented as a finished logo is not - do not pretend
otherwise, and say plainly when the next step needs a human designer.
