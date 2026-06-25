# Testing — front-end deep reference

Testing Library philosophy: "the more your tests resemble the way your software is used, the more confidence they can give you." Query by role, label, and text — not by test-id spam or implementation details.

## The pyramid

| Layer | Tool | What it tests | When to add |
|---|---|---|---|
| Unit | Vitest | Pure logic: formatters, reducers, parsers, validators | Every pure function |
| Component | Vitest + Testing Library | Interaction: renders, user events, visible output | Every interactive component |
| E2E | Playwright | Critical user flows: login, checkout, the primary action | Flows that make or lose money |
| Visual regression | Playwright screenshots / Chromatic | Design-critical pages | After a major UI change |

## Component tests (Vitest + Testing Library)

**Query priority order** (use the highest one that works):
1. `getByRole` (button, link, heading, textbox, checkbox, combobox, etc.) — semantics-correct
2. `getByLabelText` — for form controls
3. `getByPlaceholderText` — fallback for unlabeled inputs (fix the a11y too)
4. `getByText` — for non-interactive elements
5. `getByTestId` — last resort only; means the element has no semantic identity

**User events over `fireEvent`:**
```ts
import { userEvent } from '@testing-library/user-event'
const user = userEvent.setup()
await user.click(screen.getByRole('button', { name: 'Save' }))
await user.type(screen.getByLabelText('Email'), 'a@b.com')
```
`userEvent` simulates real browser events (mousedown, focus, keydown, etc.). `fireEvent` fires a single synthetic event — it misses validation and browser-native behavior.

**Server Actions in tests:**
Mock the action module, not the fetch layer. Test the component's response to the action's return value.
```ts
vi.mock('./actions', () => ({ saveItem: vi.fn().mockResolvedValue({ success: true }) }))
```

**Accessibility in component tests:**
```ts
import { axe } from 'jest-axe'
it('has no a11y violations', async () => {
  const { container } = render(<MyForm />)
  expect(await axe(container)).toHaveNoViolations()
})
```

**Test boundaries:**
- Test the component that owns the behavior, not the parent that renders it.
- One assertion per behavior, not one test per file.
- Failing tests should have one obvious fix.

## E2E tests (Playwright)

**Cover exactly three things:**
1. The primary happy path (signup → core action → success)
2. The primary auth gate (protected route redirects when logged out)
3. Any flow that processes money or sends external messages

Everything else belongs in component tests — they're faster and easier to debug.

**Locators — use semantic selectors:**
```ts
page.getByRole('button', { name: 'Submit' })
page.getByLabel('Email address')
page.getByText('Payment confirmed')
// Avoid:
page.locator('.btn-primary')  // fragile
page.locator('[data-testid="submit"]')  // last resort
```

**Page Object Model for shared flows:**
```ts
class LoginPage {
  constructor(private page: Page) {}
  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email)
    await this.page.getByLabel('Password').fill(password)
    await this.page.getByRole('button', { name: 'Sign in' }).click()
    await this.page.waitForURL('/dashboard')
  }
}
```

**Assertions over waits:**
```ts
// Good — assertion waits automatically
await expect(page.getByText('Saved')).toBeVisible()
// Bad — arbitrary wait
await page.waitForTimeout(2000)
```

**axe in Playwright:**
```ts
import { checkA11y } from 'axe-playwright'
await checkA11y(page, undefined, { includedImpacts: ['critical', 'serious'] })
```

## What NOT to test

- CSS classes or computed styles (test behavior, not implementation)
- The output of a third-party library (test your usage of it)
- Internal state of a component (test what the user sees)
- Implementation details that would change on a safe refactor

If a refactor breaks your tests without breaking user behavior, the tests are wrong.

## Common mistakes

- `screen.getByText('Submit')` when the button's accessible name is "Submit order" — use partial match or the role query
- `waitFor` wrapping a synchronous check — remove the wrapper
- `act()` warnings — almost always caused by state updates after `render()` that Testing Library doesn't know about; use `userEvent` and `waitFor` instead of manually flushing
- Mocking `fetch` at the network level for component tests — mock the module that calls fetch instead
