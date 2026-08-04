<!-- VENDORED into /user-test-splitsquad on 2026-07-21 from /user-test-sheevook (itself from /user-test). This skill OWNS this copy: edit it here. -->

# Chain of Thought

AI testing tools jump straight to conclusions. Real users hesitate, second-guess, form wrong
hypotheses, and reason their way through interfaces. Every persona MUST show internal reasoning
before every action. This is what separates a useful test from a mechanical walkthrough.

**For this skill, THINKING blocks carry a second load:** they must expose the persona's
*expectation about the number*. A cent-counter doesn't just click — he clicks with a figure already
in his head, and the gap between his figure and the app's IS the finding. **Write the expected
number first, then the action, then what the app said.** A THINKING block that only reports what
appeared has skipped the part that matters.

---

## How to Write Chain of Thought

Before every click, scroll, or form fill, write a `THINKING:` block in the persona's voice and
literacy level. It must include:

1. **What they notice** — filtered through their archetype (the organizer sees the flow; the
   cent-counter sees the digits; the stranger sees whether he has to sign up)
2. **What they expect** — including, for anything money-bearing, **the number they expect**
3. **Why they chose this action** — their reasoning, including wrong assumptions
4. **What they're ignoring** — and why

Example (Dev, the cent-counter — note the figure stated *before* the action):

```
THINKING: "Lunch was €118 plus 8.5% tax plus 12% tip. That's 118 + 10.03 + 14.16 = €142.19,
three ways, so €47.40 each — and one of us is going to be a cent short, I want to see who.
If it shows €47.40 three times I already know the total on the card can't be €142.19."
→ ACTION: open expense exp-1
→ RESULT: total €142.19, shares 47.40 / 47.40 / 47.40
→ GAP: 47.40 × 3 = €142.20. The card's total and the sum of its own shares disagree by a cent,
  on screen, in the same view. Small — but I now have to check the next one too.
```

---

## What Chain of Thought Catches

- **Wrong mental models** — "Settle up" read as "send money" when it only records an intent
- **Expectation violations** — "I clicked Save and the balance didn't move. Did it save?"
- **Hidden confusion** — right action, wrong reasoning. Another user reasoning differently fails
- **Missed elements** — "I never saw the split-type selector. My eyes went to the amount field."
- **Trust decisions** — "It converted my yen and didn't tell me the rate. I'm checking this in
  another app, and if it's wrong I'm not using this."

---

## When to Skip Chain of Thought

Only for purely mechanical navigation with no decision (e.g. "scrolled down"). Every interaction
involving a choice — and **every single money-bearing screen** — gets a THINKING block.

---

## Visual Hierarchy Score (every page, first visit)

```
EYE PATH: 1) [element] → 2) [element] → 3) [element]
DESIGNER INTENDED: 1) [element] → 2) [element] → 3) [element]
ALIGNMENT: [match / partial / mismatch]
```

Infer intent from heading hierarchy and CTA placement. **On a money screen there is an extra
question:** is the user's *own* number the most visually dominant thing? If a member has to hunt
for what they personally owe, that is an actionable finding regardless of how good the layout is.

---

## PULSE Reading

```
PULSE [page name]:
  Trust: X/5 | Confidence: X/5 | Engagement: X/5
  Trigger: [what specifically moved the needle]
```

- **Trust** — do they believe this number?
- **Confidence** — do they know what to do next?
- **Engagement** — do they care enough to keep going?

Take a PULSE reading on the landing page, after every meaningful state change, after **every
balance change**, and at the end of the session.
