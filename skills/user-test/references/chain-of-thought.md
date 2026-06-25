# Chain of Thought

AI testing tools jump straight to conclusions. Real users hesitate, second-guess, form wrong hypotheses, and reason their way through interfaces. Every persona MUST show internal reasoning before every action. This is what separates a useful test from a mechanical walkthrough.

---

## How to Write Chain of Thought

Before every click, scroll, or form fill, write a `THINKING:` block in the persona's voice and literacy level. It must include:

1. **What they notice** — filtered through their archetype (Skimmer sees headlines only; Careful Reader sees fine print)
2. **What they expect** — prediction of what will happen next
3. **Why they chose this action** — their reasoning, including wrong assumptions
4. **What they're ignoring** — and why (didn't see it, didn't care, too much text)

Example:
```
THINKING: "There's a big green button that says 'Get Started' and a smaller
link that says 'Learn More'. I don't care about learning more, I want to
fix my sink. I'm clicking the green button. I bet it takes me to some kind
of form."
→ ACTION: click @e5 (Get Started button)
→ RESULT: Navigated to /signup
→ GAP: Expected a form about my problem, got a signup form. Didn't want to
  create an account yet.
```

---

## What Chain of Thought Catches

- **Wrong mental models** — "Get Started" interpreted as "start a repair" when it means "create an account"
- **Expectation violations** — "I clicked Save and nothing happened. Did it save? I'll click again."
- **Hidden confusion** — right action, wrong reasoning. Another user with different reasoning would fail
- **Missed elements** — "I didn't even see the sidebar. My eyes went straight to the center content."
- **Trust decisions** — "This page wants my address. Why? I just wanted a repair estimate. I'm not giving my address to a random site."

---

## When to Skip Chain of Thought

Only skip for purely mechanical navigation with no decision involved (e.g., "scrolled down to see more content"). Every interaction involving a choice gets a THINKING block.

---

## Visual Hierarchy Score (every page, first visit)

Based on element size, contrast, position, whitespace, and isolation, estimate where the user's eye goes:

```
EYE PATH: 1) [element] → 2) [element] → 3) [element]
DESIGNER INTENDED: 1) [element] → 2) [element] → 3) [element]
ALIGNMENT: [match / partial / mismatch]
```

If DESIGNER INTENDED is unknown (no DESIGN.md), infer from heading hierarchy and CTA placement. A mismatch means the most important element isn't the most visually dominant — that is an actionable finding.

---

## PULSE Reading

```
PULSE [page name]:
  Trust: X/5 | Confidence: X/5 | Engagement: X/5
  Trigger: [what specifically moved the needle]
```

- **Trust** — do they believe this is legitimate?
- **Confidence** — do they know what to do next?
- **Engagement** — do they care enough to keep going?

Take a PULSE reading on the landing page, after every meaningful state change, and at the end of the session.
