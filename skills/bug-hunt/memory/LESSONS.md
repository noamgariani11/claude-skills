# bug-hunt — Active Lessons (the skill's accumulated, self-improving playbook)

This file is **read at the start of every `/bug-hunt` run (Phase R)** and **rewritten at the
end of every run (Phase 6)**. It is how the skill compounds: each run leaves it sharper than it
found it. Treat the directives here as standing amendments to the SKILL.md doctrine — apply the
highest-impact ones first, every run.

## Maintenance contract (read before editing this file)

- **Guardrails are immutable by this loop.** Lessons may sharpen *technique, coverage, tooling,
  class ordering, time budgeting, and validation* — they may **never** relax the Rules of
  Engagement, scope discipline, read-only-first, stop-at-impact, or no-auto-submit. A "lesson"
  that would weaken a guardrail is invalid; delete it. Structural changes to SKILL.md guardrail
  text are human-only (propose to monk11, never auto-apply).
- **Evidence or it didn't happen.** Every lesson cites the run(s) + journal/retro evidence that
  produced it. Record what *wasted time*, not just wins. Never fabricate an improvement to look
  productive — an honest "no new lesson this run" is a valid Phase 6 outcome.
- **Falsifiable & bounded.** Each lesson carries a confidence and a supporting/contradicting run
  count. If a later run contradicts a lesson, downgrade it; if contradicted twice, retire it to
  the bottom section. Keep **≤ 40 active lessons**: merge duplicates, retire the stale/low-impact.
  Raw per-run history lives in `retro-log.jsonl`, never here — this file stays curated and ranked.
- **Ranked.** Order Active lessons highest-expected-impact first so a run that only reads the top
  of the file still gets the most valuable adjustments.

### Lesson schema

```
### L-NNN · <short imperative title>   [conf: high|med|low] · [area: class/tool/recon/process]
- **Do:** <the behavior change to apply on future runs — concrete and actionable>
- **Why / evidence:** <what happened; cite program + run ts / journal status / retro entry>
- **Apply when:** <trigger condition, so it's not applied blindly>
- **Provenance:** added <date> · supporting runs: N · contradicting: M
```

---

## Active lessons (apply every run, highest-impact first)

### L-004 · Ground every reported claim in captured evidence — anti-slop is now existential   [conf: high] · [process]
- **Do:** Before any draft, confirm each cited endpoint/parameter/function/file/header/version is one
  you actually observed on the target (real request/response or JS/source line). Cut anything you
  can't ground. Never invent traces, dumps, or PoC output. The validator-gate Q8 enforces this; a
  claim whose narrative outruns its evidence is a FAIL, not a finding.
- **Why / evidence:** 2026 landscape research — curl ended its bounty (confirmed-rate >15% → <5%) and
  Nextcloud suspended theirs under AI-slop floods; HackerOne cut rewards in response. The notorious
  curl report cited a function that does not exist in the codebase, with fabricated GDB/register
  dumps. Slop burns monk11's H1 reputation/signal score and gets researchers banned.
- **Apply when:** Always — at draft time, and as the gating question on every candidate.
- **Provenance:** added 2026-05-27 · supporting runs: 0 (seed, from landscape research) · contradicting: 0

### L-005 · Run a reasoning pass over JS bundles, not just the diff   [conf: med] · [tool]
- **Do:** After `js_diff.py` flags new endpoints, run `research/prompts/js-recon-agent.md` over the
  saved bundles to extract admin/internal endpoints, hidden params, secrets, feature flags, and
  client-side auth logic — each with file:line evidence and the next read-only test. If a Burp/proxy
  MCP is connected, prefer reading live JS through it.
- **Why / evidence:** Landscape research — reasoning over a whole bundle (what an endpoint *does* /
  whether it's guarded) is the highest-yield real-world Claude-on-JS technique and finds hidden
  panels/undocumented APIs/live creds; regex extractors and the diff structurally miss it.
- **Apply when:** Any target serving non-trivial client-side JS (most SPAs).
- **Provenance:** added 2026-05-27 · supporting runs: 0 (seed, from landscape research) · contradicting: 0

### L-001 · On mature programs, lead with the edge tools before recon/nuclei   [conf: med] · [process]
- **Do:** Front-load Phase 2 (`variant_analysis.py` / `js_diff.py` / `authz_matrix.py`) and the
  transport/auth-parity hunt; treat recon→nuclei→fuzz as breadth backfill, not the main event.
- **Why / evidence:** Seeded from SKILL doctrine (Phase 2) — scanners structurally re-find crowd
  dups on picked-clean programs; novel/reportable bugs come from differential reasoning.
- **Apply when:** Program is mature / high participant count / dense disclosed history.
- **Provenance:** added 2026-05-27 · supporting runs: 0 (seed) · contradicting: 0

### L-002 · Spend by value density, not class frequency   [conf: med] · [process]
- **Do:** Budget the most time on injection/RCE-class, clean SSRF, and IDOR/BOLA; treat
  reflected/stored XSS as a floor to sweep, not the goal.
- **Why / evidence:** Seeded from SKILL Phase 3 + `research/12` Part G (14.6k-report payout study).
- **Apply when:** Always, when allocating Phase 3 effort across ranked leads.
- **Provenance:** added 2026-05-27 · supporting runs: 0 (seed) · contradicting: 0

### L-003 · Skip the dup-dense classes the hacktivity stats flag; chase their siblings   [conf: med] · [process]
- **Do:** From `hacktivity_stats.py --program`, identify high-count (dup-dense) classes for this
  program and do NOT re-find the reported endpoints — pivot to their variants/transport siblings.
- **Why / evidence:** Seeded from SKILL Phase 0 step 7.
- **Apply when:** Program intel returns a class with an outsized report count.
- **Provenance:** added 2026-05-27 · supporting runs: 0 (seed) · contradicting: 0

### L-009 · When source is available, READ it — don't stay black-box   [conf: med] · [class/process]
- **Do:** Before deep black-box probing, check whether the in-scope asset's source is obtainable —
  the org's public GitHub/GitLab repos, published npm/PyPI/Go/Maven packages it ships, a decompilable
  APK/IPA (`jadx`), or a downloadable desktop/Docker artifact. If any exists, run Phase 2.5
  (`research/prompts/source-review-agent.md`) over it for **authz/logic/secret-handling** bugs before
  treating the target as opaque. This complements `js_diff.py` (client JS) and `osv_check.py` (n-day
  deps) with actual server/source logic reading.
- **Why / evidence:** Video/landscape research (2026) — the recurring regret of long-time top earners
  is not learning to read code earlier; source review finds logic/authz bugs that black-box probing
  structurally misses, and AI now makes whole-repo reading cheap. The single highest-leverage
  capability the toolkit was missing.
- **Apply when:** Any in-scope asset whose source/artifact is publicly obtainable (open-source
  component, published package, decompilable mobile/desktop app). Testing still only touches in-scope
  assets; reading source is OSINT.
- **Provenance:** added 2026-05-28 · supporting runs: 0 (seed, from landscape research) · contradicting: 0

### L-010 · Spawn DIVERGENT specialist agents (isolated), then merge — not just parallel copies   [conf: med] · [process]
- **Do:** In Phase 3, give each parallel `Agent` a *different* class lens + mental model (e.g. one
  authz/IDOR, one SSRF/injection, one business-logic/race, one auth/OAuth) and run them **isolated so
  they can't anchor on each other's framing**, then merge + dedup the leads yourself. This is the
  second-pair-of-eyes effect — a different specialization sees what your primary lens skips.
- **Why / evidence:** Video/landscape research (2026) — top earners credit collaboration (splitting a
  target with someone who sees what they miss) for the bulk of their growth; the `/user-test` skill
  already proves isolated, non-colluding subprocesses surface independent findings.
- **Apply when:** Any Phase 3 with ≥2 plausible lead classes or a broad surface. Each agent still gets
  `00-rules-of-engagement.md` + `policy-snapshot.md` in its prompt (guardrails travel with it).
- **Provenance:** added 2026-05-28 · supporting runs: 0 (seed, from landscape research) · contradicting: 0

### L-011 · Lead with the classes monk11 has ACTUALLY converted (conversion_profile.py)   [conf: med] · [process]
- **Do:** In Phase R, run `research/tools/conversion_profile.py` to compute monk11's per-class /
  per-`§A#`-technique conversion across *all* prior `hunt-journal.jsonl`, and let it pre-order the
  Phase 3 class priority — go deep on what has converted for *this hunter*, down-weight personal
  time-sinks — on top of the program-specific hacktivity ordering. Specialize by evidence, not by the
  generic doctrine default.
- **Why / evidence:** Video/landscape research (2026) — the jump from finding one bug to finding
  hundreds is specialization: going deep on the classes that work *for you*. The journals already hold
  that signal; this operationalizes it instead of re-asking strengths cold each run.
- **Apply when:** Every run, in Phase R, once ≥1 program has journal history. Early on (sparse data)
  treat it as a weak prior, not an override.
- **Provenance:** added 2026-05-28 · supporting runs: 0 (seed, from landscape research) · contradicting: 0

### L-004 · Confirm the provisioned account's CAPABILITY before planning leads around features   [conf: high] · [process]
- **Do:** Right after auth, fetch the app bootstrap/config + the user's permission object, and probe whether
  key actions (create API key, create campaign, messaging) are *permitted* for THIS account. On sandbox/
  test-account programs the provisioned user is often a deliberately limited role — don't burn the run
  planning REST-injection/AI/composer leads you can't reach.
- **Why / evidence:** braze 2026-05-27 — account A was a limited role in an empty company; REST-API-key
  creation was permission-gated (`allowed_territories permission_names[]=121 -> []`), blocking the whole
  documented-REST-API injection lead after a lot of setup. App creation worked but key/messaging did not.
- **Apply when:** Authenticated hunts, especially sandbox programs that hand you a test account.
- **Provenance:** added 2026-05-27 · supporting runs: 1 · contradicting: 0

### L-005 · Scanner-banned programs are 100% manual/browser-driven — don't run hunt.sh recon   [conf: high] · [process]
- **Do:** If the policy bans automated scanners/bulk discovery (Nuclei named, etc.), DO NOT run hunt.sh's
  recon/nuclei/ffuf/arjun/subdomain paths. Hunt via: manual GET fingerprint, the app's own docs, single-shot
  GraphQL introspection, and an authenticated browser driving `js fetch` against the API. Edge analysis tools
  (variant/js_diff/authz_matrix) are still fine (local, no traffic).
- **Why / evidence:** braze 2026-05-27 — policy banned Nuclei + bulk discovery; scanner pipeline off; all
  signal came from authed browser fetch probing.
- **Apply when:** Policy excludes automated scanning / bulk discovery.
- **Provenance:** added 2026-05-27 · supporting runs: 1 · contradicting: 0

### L-006 · For session-bound apps, test via the browser's own fetch; always redirect:'manual'   [conf: high] · [tool]
- **Do:** When a captured cookie won't authenticate in curl (UA-bound, session-rotated, multi-cookie, partial
  httpOnly capture), drive authed requests with the browser's `js fetch(url,{credentials:'include'})`. For
  state-changing POST/PUT add `X-CSRF-Token` = `document.querySelector('meta[name=csrf-token]').content`.
  ALWAYS use `redirect:'manual'` and check `r.type==='opaqueredirect'` — a default-redirect fetch silently
  follows 302→/sign_in and returns a FALSE 200.
- **Why / evidence:** braze 2026-05-27 — curl got 302→sign_in despite matching UA + fresh cookies; browser
  fetch worked. A token-less POST looked like 200 ("CSRF!") but redirect:'manual' showed opaqueredirect = ran
  unauthenticated = CSRF actually DEFENDED. Two false positives avoided by redirect:'manual'.
- **Apply when:** Any authenticated hunt where curl/tool session transfer misbehaves.
- **Provenance:** added 2026-05-27 · supporting runs: 1 · contradicting: 0

### L-007 · gstack `browse` on WSLg: stay headed, JS-click to bypass timeouts, filter output narrowly   [conf: med] · [tool]
- **Do:** The 2FA'd session lives only in the **headed** profile (`~/.gstack/chromium-profile`); switching to
  headless or `disconnect` drops the session cookie (forces re-login + 2FA). Stay headed once authed. When
  `click` times out (5s actionability on flaky WSLg render), JS-click:
  `js "[...document.querySelectorAll('button')].find(b=>/Add app/i.test(b.textContent)).click()"`. When parsing
  `js` output filter ONLY `grep -v 'UNTRUSTED EXTERNAL CONTENT'` — a broad `grep -iv END` eats JSON containing
  substrings like "send"/"append" and blanks the result.
- **Why / evidence:** braze 2026-05-27 — separate headed/headless profiles cost a re-login loop; "Add app"
  click timed out until JS-click; `grep -iv END` silently blanked valid JSON for ~3 steps.
- **Apply when:** Driving gstack `browse` headed on WSL2/WSLg.
- **Provenance:** added 2026-05-27 · supporting runs: 1 · contradicting: 0

### L-008 · Braze sandbox: these surfaces are hardened (start elsewhere on resume)   [conf: med] · [class/recon]
- **Do:** On the Braze `bug-bounty-*.braze-dev.com` sandbox, skip re-testing: internal-API tenant isolation
  (403 on non-owned company_id/app_group_id), BSON ObjectId param NoSQL/type-confusion (500 coercion), and
  CSRF (Rails authenticity_token enforced; token-less POST → login redirect). No CSP anywhere (only useful
  *with* an XSS sink). Lead instead with: email-template raw-HTML fields in `/apps/{ag}/settings`
  (`email_custom_unsubscribe_page`/`opt_in_page`/footer) → verify render domain for stored XSS; and surfaces
  reachable only with a less-limited account (clarify perms with the program). `bz-rndr.com` = out of scope.
- **Why / evidence:** braze 2026-05-27 — all three classes confirmed defended; account A perm-limited.
- **Apply when:** Resuming the Braze program.
- **Provenance:** added 2026-05-27 · supporting runs: 1 · contradicting: 0

### L-012 · Broad-prose-scope enterprise VDPs: unauth surface is WAF-walled + SPA-auth — budget toward auth early   [conf: med] · [process]
- **Do:** On a large "all our applications" prose-scope program (esp. VDP behind Akamai/Cloudflare/F5),
  the fast unauth wins (actuator/swagger, source maps, takeover, open DCR) are usually closed and apps
  do client-side SPA auth. Front-load: (1) passive CT enum (WAF-immune) to map the real surface,
  (2) OIDC `.well-known` discovery to map the auth server, (3) one DCR POST test if advertised,
  (4) non-prod (dev/qa/uat/beta) enumeration — then pivot to AUTHENTICATION for IDOR/BOLA/BFLA rather
  than grinding unauth. Tell monk11 early that auth (alias account) is the gate to real findings.
- **Why / evidence:** caterpillar 2026-05-29 — 554 live hosts mapped, every easy unauth class closed
  (7 dead-ends, 0 findings); all high-value leads needed auth. Time sank into browser fights with
  Akamai/Cloudflare on apps that needed a session anyway.
- **Apply when:** Broad-prose-scope enterprise program, heavy WAF, SPA portals, no/low disclosed history.
- **Provenance:** added 2026-05-29 · supporting runs: 1 · contradicting: 0

### L-013 · Akamai/Cloudflare edge gate is header-based first-hop: full browser header template bypasses it read-only   [conf: high] · [tool/recon]
- **Do:** When AkamaiGHost/Cloudflare 403s a bare/research UA, send the COMPLETE browser header set
  (UA + Accept + Accept-Language + sec-ch-ua + sec-ch-ua-mobile/platform + Sec-Fetch-Dest/Mode/Site/User
  + Upgrade-Insecure-Requests) — Akamai's edge bot-gate is header-shaped and returns 200 + ak_bmsc with
  the full set. Save as curl-headers.txt; pass `-H @file` to every curl; httpx/nuclei/ffuf need the same
  headers or they 403. Some paths (/robots.txt,/sitemap.xml) stay hard-403. Cloudflare JS-challenge pages
  (e.g. digital.cat.com) still need a headed+stealth browser, not just headers.
- **Why / evidence:** caterpillar 2026-05-29 — bare + plain-browser-UA = 403 AkamaiGHost; full header set
  = 200 + ak_bmsc on www.caterpillar.com/cat.com. Reused across all *.cat.com probing.
- **Apply when:** Any target fronted by Akamai Bot Manager / Cloudflare returning 403 to tool UAs.
- **Provenance:** added 2026-05-29 · supporting runs: 1 · contradicting: 0

### L-014 · Caterpillar (cat) VDP: scope + surface map for resume   [conf: med] · [recon/class]
- **Do:** Scope = 12 Cat-owned apexes (cat.com, caterpillar.com, perkins.com, fgwilson.com, solarturbines.com,
  progressrail.com, mwm.net, spmoilandgas.com, semmachinery.com, turner-powertrain.co.uk, catrentalstore.com,
  asiatrak.com). OUT: Mitsubishi Logisnext (Cat Lift Trucks licensee), dealers, *.my.site.com, regional MWM
  distributors. Don't re-chase (confirmed clean unauth): Spring actuator/swagger on services-*; source maps;
  subdomain takeover; fedlogin DCR (advertised but 404); catused ViewState (MAC-protected). Resume via AUTH
  (CWS acct: supplierconnect "Request New CWS Account" / my.cat.com; wearehackerone alias required) then chase
  services-int BOLA, OAuth redirect_uri (get client_id from an OAuth app), non-prod (dev/qa) authz. Full map:
  output/targets/caterpillar/recon/SUMMARY.md. Akamai bypass header template: recon/curl-headers.txt.
- **Why / evidence:** caterpillar 2026-05-29 run.
- **Apply when:** Resuming Caterpillar.
- **Provenance:** added 2026-05-29 · supporting runs: 1 · contradicting: 0

### L-015 · Akamai binds bot cookies to the original browser — transplanted sessions tarpit; capture fresh in-browser   [conf: high] · [tool/process]
- **Do:** On Akamai Bot Manager sites, you CANNOT carry an authenticated session by pasting cookies into
  curl OR by importing them into a different browser: Akamai binds `ak_bmsc`/`bm_sv` to the issuing TLS/
  device fingerprint, so transplanted requests **tarpit (hang/timeout)** rather than 403. Symptom: top-level
  GET of the homepage is 200, but `/account/*` pages chrome-error and same-origin `fetch()` hangs. To test
  authenticated, drive the SAME live browser the user logged in with (browse `handoff`→user logs in→`resume`),
  capture cookies fresh immediately before testing, navigate via in-page clicks (not raw fetch/XHR), keep rate low.
- **Why / evidence:** caterpillar 2026-05-29 — pasted www.cat.com session (CWSID+JSESSIONID+ak_bmsc) imported
  to headed Chrome: homepage 200 but account pages errored and fetch(redirect:'manual') timed out; curl with the
  same real cookies tarpitted too. Could not reach the catRecId IDOR surface.
- **Apply when:** Any authenticated hunt on an Akamai Bot Manager (or similar device-bound) estate.
- **Provenance:** added 2026-05-29 · supporting runs: 1 · contradicting: 0

### L-016 · B2C/Azure-AD silent token mint via curl bypasses the Akamai headed-browser blocker   [conf: high] · [tool/process]
- **Do:** When an authenticated target fronts its login on a B2C/AAD custom domain (e.g. `signin.cat.com`)
  but tarpits transplanted browser sessions on its app hosts (Akamai bot-cookie binding, L-015), DON'T fight
  the headed browser for the *API* surface. Persist the **B2C SSO cookie jar** + a **refresh_token** once
  (from any one real login), then re-mint fresh access tokens entirely by curl: (a) `grant_type=refresh_token`
  for a quick same-client refresh; (b) full **`prompt=none` PKCE auth-code** flow (GET authorize w/ the SSO
  cookies → `302 ?code=` → POST `/token`) to mint a token for ANY app client/audience whose `client_id` +
  `redirect_uri` + `scope` you can read from the SPA bundle. The login host + the API gateway are usually NOT
  Akamai-tarpitted — only the www/account app hosts are. SSO cookies often last weeks (KMSI), so the channel
  survives across sessions without re-login. This is authentication of your own account (not a state-change).
- **Why / evidence:** caterpillar 2026-05-30 evening — persisted `signin.cat.com` `x-ms-cpim-sso` (KMSI, valid
  90d) + 24h refresh_token still live ~14h later; re-minted a myengine token AND the VL fleet token (aud
  `4aebf00a`) by curl with zero browser and zero re-login, removing the prior run's L-015 blocker for the whole
  API surface. Authorize params came straight from the VL SPA bundle.
- **Apply when:** Authenticated hunt on a B2C/AAD-fronted target whose app hosts are device-bound-cookie WAF'd
  but whose login+API hosts answer curl. Mine the SPA bundle for each client's authorize params.
- **Provenance:** added 2026-05-30 · supporting runs: 1 · contradicting: 0

### L-017 · Enterprise multi-IdP estates: map which surface each account CLASS can even reach before planning leads   [conf: high] · [process]
- **Do:** On a big enterprise estate with several IdPs/audiences, the reachable authenticated surface splits
  by account class, and most of the juicy matrix is unreachable to an external researcher. Before investing in
  a BOLA/BFLA matrix, classify each target host by *what token authenticates it*: customer-B2C vs employee-corp-
  Entra vs partner. Employee-only APIs are **unobtainable** to an external customer account — don't plan the run
  around them. Also separate *token-derived* endpoints (no id param → inherently IDOR-safe) from *id-parameterized*
  ones early, and prioritise only the reachable∩id-parameterized cells.
- **Why / evidence:** caterpillar 2026-05-30 — the richest BOLA matrix (GRID `grid-api`, ~240 ops, password-
  reset/cross-tenant-PII) needs an **employee corp-Entra** token; an external CWS customer just gets E0000005.
  Curl-reachable customer endpoints were token-derived/clean; the id-parameterized ones were Akamai-gated. Much
  matrix-building targeted surface the researcher's account class structurally can't reach.
- **Apply when:** Any multi-IdP enterprise/VDP estate.
- **Provenance:** added 2026-05-30 · supporting runs: 1 · contradicting: 0

### L-018 · Mine prod SPA `window.config`/inline env for dev-in-prod + internal-host disclosure   [conf: high] · [recon/class]
- **Do:** For every in-scope SPA, GET the prod `index.html` and grep the inline runtime config
  (`window.config`, `__ENV__`, `<script id="env-config">`, `REACT_APP_*`, `NEXT_PUBLIC_*`). It often
  names the *real backend per deploy target* — catching (a) production hosts wired to **dev/internal
  APIs** (`*.dev.<internal-tld>`), (b) `DEV_BUILD:true`/debug flags shipped to prod, and (c) internal
  infra hostnames + OAuth/Okta client ids. This is a fast, high-yield static pass that needs no API
  reachability and survives WAF (the HTML is CDN-served). Pair with source-map reconstruction for the
  full endpoint inventory. Frame impact honestly: internal-host disclosure is Low unless you can reach
  the backend or show data — but dev-build-in-prod on a regulated product is a legit config finding.
- **Why / evidence:** robinhood 2026-06-05 — five PROD Say portals (voting/issuer/intermediary/activist/
  missioncontrol.say.rocks) shipped `window.config` pointing at internal `api.dev.rhinternal.net`,
  `voting.say.rocks` flagged `DEV_BUILD:true`. Found purely from `curl | grep window.config`, zero API
  access. Source maps (prod brokerportal/issuer) reconstructed 149+518 source files → full broker
  back-office API map.
- **Apply when:** Any CRA/Next/Vite SPA in scope. Always cheap; do it during recon.
- **Provenance:** added 2026-06-05 · supporting runs: 1 · contradicting: 0

### L-019 · This sandbox's egress TLS-resets many AWS EC2 origins — confirm reachability before planning live API tests   [conf: high] · [tool/process]
- **Do:** Before building a run plan around live API probing, TCP+TLS-test the actual API origin from
  this box (`socket.create_connection` then `ssl.wrap_socket`). Some AWS EC2-hosted origins (seen:
  `*.say.rocks` on 52.207/34.231, us-east-1) complete TCP 443 but **reset the TLS handshake (EOF) for
  every client here — curl, openssl, AND real Chromium** (Playwright HAR shows status -1), while
  Vercel/CloudFront/Imperva-fronted hosts work fine. The public product works for real users, so it's
  an egress/IP-reputation reset, NOT a target finding. Don't burn the run fighting it or mis-report it
  as "server down" — log it ruled-out and mark the lead "needs clean egress (monk11 box)".
- **Why / evidence:** robinhood 2026-06-05 — consumerapi/api/sso.say.rocks all TLS-EOF from this env;
  blocked all live Say BOLA/unauth-PII testing. Vercel portal hosts + bitstamp answered normally.
- **Apply when:** Any live API testing; especially raw-EC2 / non-CDN origins.
- **Provenance:** added 2026-06-05 · supporting runs: 1 · contradicting: 0

### L-020 · Decrypt Chrome cookies to unlock authenticated testing without a Playwright browser   [conf: high] · [tool/auth]
- **Do:** When a target's browser session is needed, decrypt `~/.config/google-chrome/Default/Cookies` with PBKDF2("peanuts","saltysalt",1,16) + AES-128-CBC(IV=16 spaces). v10 prefix: skip 3 bytes, decrypt, find real value after first backtick (0x60) byte. Then use `curl_cffi` with `impersonate="chrome124"` to bypass Cloudflare TLS fingerprint. Full recipe in `output/targets/anthropic/latest-handoff.md`. Install: `pip3 install curl_cffi --break-system-packages`.
- **Why / evidence:** anthropic run 5 2026-06-08 — Chrome cookie DB decryption unlocked claude.ai authenticated API testing. curl was blocked (403) even with cf_clearance cookie; curl_cffi with Chrome TLS fingerprint impersonation bypassed it. Chrome must not be running while copying DB (file locked), copy to /tmp first.
- **Apply when:** Target uses Cloudflare bot protection AND the researcher's machine has Chrome installed with an active session for the target domain.
- **Provenance:** added 2026-06-08 · supporting runs: 1 · contradicting: 0

### L-021 · JS bundle API surface mining: check assets-proxy CDN base URL for SPA apps   [conf: high] · [recon/tool]
- **Do:** Modern SPAs (claude.ai) don't put JS in `/_next/static/`. Instead they load from a CDN (e.g. `https://assets-proxy.anthropic.com/claude-ai/v2/assets/v1/`). Always check `<script src>` and `<link rel=preload>` tags for the ACTUAL bundle location. Then grep the main bundle for `"/api/` and `'/api/` patterns. Expect 100-300 unique routes.
- **Why / evidence:** anthropic run 5 2026-06-08 — pattern `/_next/static/chunks/` yielded zero JS files. After fixing to use the CDN URL from HTML, found 230+ API routes including critical ones like proxy/v1/messages and cowork endpoints.
- **Apply when:** Any Next.js or CRA SPA. Always check HTML src/preload before assuming standard paths.
- **Provenance:** added 2026-06-08 · supporting runs: 1 · contradicting: 0

### L-022 · When session auth is obtained, look for a proxy/v1/ endpoint that accepts session auth   [conf: med] · [class/auth]
- **Do:** After obtaining a session cookie for a web app that also has an API, immediately look for `/proxy/v1/` or `/gateway/` endpoints in the JS bundle. Session-authenticated proxy endpoints can: (a) give model access without an API key, (b) inject hidden system prompts (count input_tokens vs payload tokens to detect), (c) apply different rate limits. Always test IDOR on the org-scope of these endpoints.
- **Why / evidence:** anthropic run 5 2026-06-08 — found `POST /api/organizations/{org}/proxy/v1/messages` accepting session cookie, returning real inference (200, model=sonnet-4-6). 4116 input tokens for 4-token payload = ~4112 injected system prompt. Proxy is org-scoped correctly (IDOR blocked).
- **Apply when:** Any web app that also has a developer API (developer console + web product combined).
- **Provenance:** added 2026-06-08 · supporting runs: 1 · contradicting: 0

---

### L-023 · User-directed outbound connectors are NOT SSRF — only a blocklist bypass qualifies   [conf: high] · [class/framing]
- **Do:** Before filing any "SSRF" on a feature that fetches user-supplied URLs (MCP remote connectors, webhooks, URL fetch, web search, image proxy, browser tools), ask: is making outbound HTTP connections the explicit feature purpose? If yes, the "server makes a request" is not a finding. The reportable target is a **bypass of the execution-layer internal-IP blocklist** — i.e., a connection to 169.254.x.x / RFC-1918 / cloud IMDS actually succeeds at the socket layer. Registration accepting internal IPs is not sufficient if execution blocks them. Also check whether the egress IP and User-Agent are already publicly documented before claiming infrastructure exposure as impact.
- **Why / evidence:** L-017 (Anthropic MCP SSRF) closed Informative 2026-06-08. Anthropic: "The remote MCP connector feature exists specifically to make outbound connections from our infrastructure to user-registered MCP server URLs — that is its purpose, and the egress IP range and Claude-User user-agent are publicly documented." Execution-layer atomic DNS+IP validation covers all transports and future code paths by design. `160.79.106.36` / `User-Agent: Claude-User` are in Anthropic's public docs.
- **Apply when:** Any URL-fetching feature. Check program docs for published egress IPs before claiming infrastructure fingerprinting. Verify execution-layer block is truly bypassable before submitting.
- **Anthropic-specific note:** MCP connectors, web search, URL fetch, and webhooks are all by-design outbound. Egress IP `160.79.106.36` is public. Execution-layer atomic IP validation covers shttp + WebSocket + future paths. Only a proven bypass of that check is reportable.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 Anthropic, Informative) · contradicting: 0

### L-024 · Atomic execution-layer IP blocking beats registration-layer validation — don't claim otherwise   [conf: high] · [class/framing]
- **Do:** Do NOT report "defense-in-depth failure" or "registration accepts internal IPs" when the execution layer performs atomic DNS-then-IP validation at socket connection time. This architecture is *more* robust than registration-layer blocking because it: (1) resolves DNS and validates the actual destination in one operation, (2) covers every transport and future code path, (3) is not bypassable by DNS rebinding. The security gap would only exist if a code path makes an outbound connection *without* routing through the execution-layer check. Before submitting, prove such a bypass path exists.
- **Why / evidence:** L-017 (Anthropic) closed Informative 2026-06-08. Anthropic: "The execution-time transport layer is the intended security boundary here precisely because it covers every code path that opens an outbound connection, including future ones, regardless of what is stored at registration time." The "unconfirmed WebSocket escalation path" was also moot — WebSocket routes through the same connection-layer protection.
- **Apply when:** Any multi-stage flow (register URL → later execute against it). Verify whether execution-layer check exists and is atomic before framing registration as a gap.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 Anthropic, Informative) · contradicting: 0

### L-025 · External request confirmation is not the SSRF PoC — internal access success is   [conf: high] · [class/process]
- **Do:** When testing an outbound connector (URL fetch, webhook, MCP, image proxy, browser tool), confirming the server makes an external request to your controlled URL (httpbin, interactsh) is the **prerequisite step**, not the PoC. That only proves the connector works. The actual SSRF PoC is a request that reaches an internal target (127.0.0.1, 169.254.169.254/latest/meta-data, RFC-1918, internal hostname) at connection time. Hunt protocol: (1) confirm external request works → (2) attempt internal targets → (3) advance to CONFIRMED only if step 2 succeeds with a live connection. If step 2 is blocked at socket time, close the lead as Not-A-Bug (intentional feature behavior) and append to ruled-out.md with the blocked evidence.
- **Why / evidence:** L-017 (Anthropic MCP SSRF) closed Informative 2026-06-08 — hunt confirmed external requests (httpbin echo: `origin: 160.79.106.36`, `User-Agent: Claude-User`) and advanced to CONFIRMED before verifying internal access. Internal IPs were blocked by execution-layer check. The report was written against external-request behavior, which is the feature's explicit purpose. Triager: "the remote MCP connector feature exists specifically to make outbound connections." Closed Informative.
- **Apply when:** Any finding in the "outbound connector / URL fetch" space. Do NOT advance the lead or draft a report until you have a positive result on internal IP access, not just external request confirmation. The httpbin echo is evidence the feature works; it is not evidence of a vulnerability.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-017 Anthropic, Informative) · contradicting: 0

### L-026 · Sanitizer/redaction gap kill-list: check for incremental exposure before advancing the lead   [conf: high] · [class/framing]
- **Do:** Before advancing any sanitizer, redaction, or token-scrubber finding to CONFIRMED, answer: **Who gets the sensitive value due to the gap that wouldn't have it otherwise?** Apply the kill test:
  - **Precondition-constitutes-full-exposure**: If triggering the bug requires the user to have ALREADY written the sensitive value somewhere public/accessible (e.g., pasted into a GitHub issue, public form, shared document), the "bug" adds no new exposure. The value was already exposed at write time.
  - **Same-audience routing**: If the sanitizer gap routes the value to the same audience that already saw it at input time (e.g., same repo audience → same repo's GitHub Actions log), no new party gets access.
  - **Own-infrastructure recipient**: If the "leak" destination is the target program's own infrastructure (e.g., Anthropic's inference API for an Anthropic report), the company owns that endpoint and cannot be harmed by receiving data on their own systems.
  If ANY of the three above applies, close the lead as Not-A-Finding and append to ruled-out.md.
- **When sanitizer gaps ARE findings:** The value leaks to a GENUINELY NEW audience: a third-party service, a public log visible to more people than the original input channel, a permanent storage tier that outlives the original exposure. The test: removing the sanitizer must allow data to reach a party who wouldn't have it via the precondition path alone.
- **Why / evidence:** L-005 (Anthropic claude-code-action sk-ant-* gap) closed Informative 2026-06-08. Triager: "pasting the key into a GitHub issue already exposes it to the repo's full audience; forwarding to Anthropic's own inference endpoint grants no additional party access." The report passed validator and lint gates but failed the incremental-exposure test — the hunt should have caught this pre-report.
- **Apply when:** Any lead in the "missing redaction / incomplete sanitizer / token pattern gap" class. Run the three kill-test questions in Phase 3 of the hunt before writing a report. A clean validator result does NOT mean the finding is reportable.
- **Provenance:** added 2026-06-08 · supporting: 1 (L-005 Anthropic, Informative) · contradicting: 0

### L-027 · Verify subscription CAPABILITY before claiming a proxy tier bypass   [conf: high] · [class/process]
- **Do:** Before reporting a "tier bypass" on claude.ai's proxy endpoint (`/api/organizations/{org}/proxy/v1/messages`), check the org's `capabilities` array via `GET /api/organizations/{org}`. The proxy gates features (extended thinking, tools, etc.) by subscription CAPABILITY (e.g., `claude_max`), NOT by account settings like `paprika_mode`. If the `capabilities` array includes the relevant tier, the feature is authorized — not a bypass. Only claim a bypass if the account's `capabilities` explicitly does NOT include the feature tier but it still works.
- **Why / evidence:** Anthropic run 11 2026-06-09 — `paprika_mode: null` account settings, yet extended thinking (200 with thinking blocks) worked via proxy. Account had `capabilities: ['claude_max', 'chat']` and `billing_type: stripe_subscription`. Max subscribers are authorized for extended thinking. The PATCH to paprika_mode is a UI preference, not an entitlement gate. Spent significant time investigating a false positive before checking the org capabilities endpoint.
- **Apply when:** Any test of a "premium feature bypass" on claude.ai. Always check `GET /api/organizations/{org}` for `capabilities`, `rate_limit_tier`, and `billing_type` FIRST. The capabilities array is ground truth for what the account is authorized to use.
- **Provenance:** added 2026-06-09 · supporting runs: 1 · contradicting: 0

### L-028 · On broad-prose-scope VDPs, pivot away from the named domain if it's Akamai-gated; find what IS accessible   [conf: high] · [process/recon]
- **Do:** For DoD-class VDPs where scope is "all publicly accessible [org] systems," do NOT spend the run trying to bypass the org's primary domain WAF. Instead, search-engine dork + CT-enum adjacent known-accessible systems (dl.dod.cyber.mil, cyber.mil, etc.) within the same scope. The fastest path to a finding is the least-defended publicly accessible subsystem, not the flagship domain.
- **Why / evidence:** dod 2026-06-10 -- defense.gov (80 subdomains, all Akamai JS-challenge gated) was a dead end. Pivoting to dl.dod.cyber.mil (found via WebSearch dorking) produced a confirmed finding in < 30 min. The DoD VDP's broad scope means hundreds of accessible .mil systems exist; the flagship defense.gov is the most hardened.
- **Apply when:** Any VDP with broad prose scope (all [org] systems) where the primary domain is WAF-protected. Run CT-enum + dork for adjacent accessible systems before spending time on the flagship.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-029 · WordPress uploads directory listing is a fast-win on government/enterprise WordPress sites   [conf: med] · [class/technique]
- **Do:** On any government/enterprise WordPress target, include /wp-content/uploads/ in the standard recon path check. Many organizations enable WordPress directory listing accidentally. Even if debug.log/wp-json/xmlrpc are hardened, the uploads directory may be open. The presence of non-public documents (NATO briefings, audit logs, internal files) in a browsable uploads dir is immediately reportable.
- **Why / evidence:** dod 2026-06-10 -- dl.dod.cyber.mil had debug.log/wp-json/wp-login all hardened (404), but /wp-content/uploads/ returned a full directory listing with NATO-Security-Briefing-II.docx and WP security audit logs. VALIDATOR PASS, report drafted.
- **Apply when:** Any WordPress target (government/enterprise especially). Add to the standard Phase-1.5 exposed-data sweep.
- **Provenance:** added 2026-06-10 · supporting runs: 1 · contradicting: 0

### L-030 · OpenAPI `style` param (or any enum-less string param in a redirect) → param injection  [conf: high] · [class/technique]
- **Do:** When a redirect endpoint accepts a query parameter and passes it into the `Location` header (or any downstream URL), check: (1) does the OpenAPI spec enforce an `enum` or `pattern` on that param? (2) does the server re-encode the value before injecting? URL-encode `&key=value` inside the param value — if the server raw-decodes before constructing the redirect URL, the injected key-value pair becomes a separate parameter in the downstream request. Common impactful second-order params: `label`, `message`, `link`, `color` (badge services); `redirect_uri`, `client_id` (OAuth); `callback` (JSONP).
- **Why / evidence:** Mergify 2026-06-11 — `GET /v1/badges/{owner}/{repo}.svg?style=flat%26label%3DSPOOFED` → Location: `...&style=flat&label=SPOOFED`. shields.io honored `label` (badge text spoofed) and `link` (click hijack). OpenAPI spec had no `pattern`/`enum` on style. CVSS 4.7 Medium, confirmed bug, report drafted.
- **Apply when:** Any endpoint that constructs a redirect URL using a query parameter. Specifically: badge endpoints, OAuth redirect helpers, image proxy, CDN URL builders. Check the OpenAPI spec first — absence of `pattern`/`enum` on a string param that feeds a URL is a signal.
- **Provenance:** added 2026-06-11 · supporting runs: 1 (Mergify H-004) · contradicting: 0

---

### L-031 · XSS upload-path ≠ XSS — confirm rendering independently before advancing lead  [conf: high] · [class/process]
- **Do:** For stored XSS, confirm BOTH sides independently before advancing to CONFIRMED: (1) the **upload path** (does attacker data reach the server unsanitized?), AND (2) the **rendering path** (does the dashboard render that data without encoding?). Confirming only the upload path is a lead, not a confirmed bug. SPA dashboards built with React/Vue/Angular almost always auto-escape via JSX/template bindings — the rendering side must be verified from the JS bundle or a live test. Download the frontend bundle and search for `dangerouslySetInnerHTML`, `innerHTML`, `v-html`, `[innerHTML]`, `bypassSecurityTrust*` to find the rare unescaped paths.
- **Why / evidence:** Mergify H-001 2026-06-11 — confirmed all 3 CI test reporter implementations (Python, TypeScript, Rust) send span data unsanitized to api.mergify.com. But dashboard bundle analysis showed React JSX rendering (auto-escaped) + DOMPurify on the only `dangerouslySetInnerHTML` usage. Upload path confirmed but rendering safe → H-001 CLOSED. Would have been a false positive if submitted on upload-path evidence alone.
- **Apply when:** Any stored XSS hypothesis on a modern SPA target. Download the JS bundle and grep for unescaped rendering before advancing past LEAD status.
- **Provenance:** added 2026-06-11 · supporting runs: 1 (Mergify H-001) · contradicting: 0

---

### L-032 · quick_xml + JUnit XML entity unescaping: &lt;payload&gt; in XML becomes <payload> before API upload  [conf: med] · [class/technique]
- **Do:** When analyzing JUnit XML-based CI reporters, remember that XML entity references (`&lt;`, `&gt;`, `&amp;`, `&quot;`) are decoded by the XML parser BEFORE the data is serialized to JSON/protobuf for API upload. A JUnit XML file containing `<failure message="&lt;img src=x onerror=alert(1)&gt;">` will have the decoded string `<img src=x onerror=alert(1)>` uploaded to the telemetry endpoint. The XSS payload does not need to survive XML parsing — it rides through it. This broadens the attacker-controlled input space for any XSS in a CI telemetry dashboard.
- **Why / evidence:** Mergify H-001 analysis 2026-06-11 — `quick_xml` (Rust) decodes entity refs before `build_span()` assembles the OTLP span. `&lt;script&gt;` in test XML → `<script>` in the OTLP JSON body sent to the API. This means any XML-entity-encoded payload in JUnit test names/messages survives intact to the server.
- **Apply when:** Any target using JUnit XML-format test reporting (pytest, JUnit, NUnit, TestNG, xUnit). When testing CI dashboard XSS, the PoC XML payload can use XML entity encoding freely.
- **Provenance:** added 2026-06-11 · supporting runs: 1 (Mergify H-001 Rust source) · contradicting: 0

---

### L-033 · The non-prod twin of a WAF-gated SPA is often the open door — mine it for the prod surface map   [conf: high] · [recon/process]
- **Do:** When the prod web app is Cloudflare/Akamai JS-challenge-gated (403 even with the full
  browser-header set, L-013), check its **non-prod twins** (`app-qa.`, `member-qa.`, `*.staging.`,
  `*-qa.`/`*-ext.` hosts) — they are frequently reachable (200) with the *same SPA bundle and the
  same `publicRuntimeConfig`/`buildManifest`*. From the QA HTML pull the CDN bundle base (L-021),
  the `__NEXT_DATA__.runtimeConfig` (L-018: internal hosts, API keys, env), and `_buildManifest.js`
  (the full route map incl. fund-transfer/IDOR routes) — that maps the *prod* surface for free even
  while prod is walled. This is the highest-yield pre-auth move on a WAF-fronted SPA.
- **Why / evidence:** chime 2026-06-22 — prod `app.chime.com`/`www.chime.com` were CF-403, but
  `app-qa.chime.com` returned 200; its Next.js publicRuntimeConfig leaked internal host
  `consumer-int` + googleAPIKey, and buildManifest gave the entire member-app route map
  (`/move-money`, `/accounts/*/[transactionId]`, `/oauth/authorize`) without ever touching prod.
- **Apply when:** Any WAF-gated SPA where scope lists QA/staging/non-prod hosts (or CT enum reveals them).
- **Provenance:** added 2026-06-22 · supporting runs: 1 (chime) · contradicting: 0

### L-034 · Chime (BugCrowd): scope + pre-auth map + auth-pass next step   [conf: med] · [recon/class]
- **Do:** Pre-auth surface is narrow (Cloudflare JS-challenge on all prod). Reachable: `app-qa.chime.com`
  (QA member SPA, mined), `developer.chime.com` (partner API docs). DON'T re-chase (ruled out):
  prod-host WAF bypass, the `tuner-config-public`/prod asset S3 buckets (exact-key only), subdomain
  takeover (655 swept clean), the internal `chmfin.com` estate (internal-only DNS). **Treat
  Galileo/pci-vault/chalk/anomalo `*.chmfin.com` hosts as THIRD-PARTY = OUT** (RoE g1; brief's
  "Non Chime Owned Assets" list). **Resume via AUTH:** (1) partner-API BOLA on
  `/users/:id/accounts/:account_id/{transactions,statement}` via the developer-portal sandbox (OAuth2
  PKCE, 2 tokens) — highest EV; (2) member-account IDOR on `[transactionId]`/`[cardId]` + the
  `/api/consumer/*`→`consumer-int` BFF seam. Full map: output/targets/chime/dossier.md.
- **Why / evidence:** chime 2026-06-22 run 1 — 0 reportable pre-auth; all value auth-gated (matches the program's fund-transfer focus).
- **Apply when:** Resuming Chime.
- **Provenance:** added 2026-06-22 · supporting runs: 1 · contradicting: 0

### L-035 · Strapi /api/users 500-vs-401 is NOT an auth bypass — it's an impactless crash; demand data before claiming bypass   [conf: high] · [class/process/anti-slop]
- **Do:** On Strapi, a no-header request to `/api/users` returning **500** while a `Bearer <garbage>` returns **401** is NOT an authentication bypass. The 401 only fires because Strapi's JWT verifier short-circuits on `Bearer`-prefixed headers; ANY other request (no header, non-Bearer `Authorization: garbage`) falls through to the users controller which **crashes (500)** because the Public role lacks the User `find` permission and the plugin throws instead of returning 403. Every variant (`/api/users/me`, `/api/users/1`, `/api/users/count`, `?fields=`) returns the same generic 500 with **zero data**. Before ever calling this a bypass: prove a request actually returns user data (HTTP 200 + records). A 500 = unhandled exception (CWE-755), BugCrowd **P5/Informational**, not P3. Do NOT write the speculative "if the crash were fixed the user list would leak" narrative — it's unfalsifiable AI-slop.
- **Why / evidence:** infinite-athlete 2026-06-22 — initial run mis-framed `cms.infiniteathlete.ai` (Strapi v5 CE) 500-vs-401 as a "P3 auth bypass" and drafted a report. Skeptical re-verification (model switch, same run) showed `Authorization: garbage`→500 too (so 401 is just the Bearer short-circuit), and every users-route returns a generic 99-byte error with no data/stack-trace/PII. `/api/pages` (public) returns 200, proving global middleware is healthy. The "bypass" claim was false; report withdrawn.
- **Apply when:** Any Strapi CMS, and generally any 500-vs-401/403 differential. A status-code differential is a fingerprint, never proof of access — only HTTP 200 + the protected data is.
- **Provenance:** added 2026-06-22 · supporting runs: 1 (infinite-athlete, corrected) · contradicting: 1 (own re-verification overturned the original framing)

### L-036 · Verify platform tech tags against HTTP headers before planning attacks   [conf: high] · [recon/process]
- **Do:** BugCrowd (and H1) program brief "tech" tags are self-reported at program creation time and DRIFT — they do not auto-update when the target changes stack. Always validate tech-stack claims with a live GET + header inspection before planning class-specific attacks around them. Especially: "WordPress" (check for `x-powered-by`, `/wp-json/`, `/wp-login.php` before running WP-class attacks), "Rails" (check `x-runtime`), "Spring" (check `/actuator/health`). A false-positive tech tag wastes an entire recon phase on a dead class.
- **Why / evidence:** infinite-athlete 2026-06-22 — BugCrowd tagged `tempus-ex.com` as WordPress, but all WP paths return S3 `NoSuchKey` XML errors; the site is a static HTML "Coming Soon" page on S3/CloudFront. Would have wasted time on WP-specific attacks if not validated first.
- **Apply when:** Always, immediately after scope pull — validate every stated tech tag with a live GET before building Phase 3 class priority around it.
- **Provenance:** added 2026-06-22 · supporting runs: 1 (infinite-athlete) · contradicting: 0

### L-035 · Next.js pre-auth checklist: version → CVE-2025-29927, /_next/image, SSR-data cookie reflection, middleware-vs-gSSP auth   [conf: high] · [class/technique]
- **Do:** On any Next.js target, run this fast pre-auth battery: (1) read the Next version (grep
  `version:"NN.N.N"` in framework/main chunks + `__NEXT_DATA__.buildId`); if **< 15.2.3 / < 14.2.25**
  it's **CVE-2025-29927**-vulnerable — but the bypass (`x-middleware-subrequest:` header) only works if
  **auth is enforced in middleware**, not in `getServerSideProps`. Check a protected route's `_next/data/<buildId>/<page>.json`: `__N_SSP` + a server-returned redirect prop ⇒ auth is in gSSP ⇒ CVE-29927
  is moot (and Cloudflare strips the header anyway). (2) `/_next/image?url=<ext>` for open-proxy/SSRF —
  usually allowlisted ("url parameter is not allowed"). (3) `_next/data/<buildId>/<page>.json` for
  unauth `getServerSideProps` leakage AND param/cookie reflection into pageProps (found Chime reflecting
  the `after-auth-redirect` cookie unvalidated — but confirm the **injection vector** is open before
  calling it a bug, per L-031: host-only/httponly/samesite cookies set only for validated routes = closed).
- **Why / evidence:** chime 2026-06-22 — Next 15.0.0 (vuln version) but auth was gSSP-based so CVE-29927
  failed all payloads (307→/login); /_next/image allowlisted; login.json reflected the redirect cookie but
  the cookie injection vector was server-validated to internal routes = not exploitable standalone.
- **Apply when:** Any Next.js SPA (check `_next/static`, `__NEXT_DATA__`).
- **Provenance:** added 2026-06-22 · supporting runs: 1 (chime) · contradicting: 0

### L-037 · Atlassian Marketplace app programs: classify Forge-vs-Connect FIRST; only Connect has an external backend   [conf: high] · [recon/process]
- **Do:** When a BugCrowd/H1 program's "targets" are Atlassian Marketplace apps (marketplace.atlassian.com
  URLs), the listing page is OUT of scope — you test the app on your OWN `bugbounty-test-<name>.atlassian.net`
  instance. Before planning, classify every app via the marketplace REST API:
  resolve listing-id→appKey from the app page HTML (`grep '"appKey"'`), then
  `GET /rest/2/addons/<appKey>/versions/latest` and read `deployment.connect`. **`connect:true` = Connect
  app with a vendor-hosted backend (probeable read-only); `connect:false` = Forge (Atlassian-hosted, NO
  external backend — testable only inside an installed instance).** Pull each Connect app's
  `<baseUrl>/atlassian-connect.json` for its module/endpoint/lifecycle/webhook map. The unauthenticated
  surface is just the Connect backends; everything else is authenticated-instance-only.
- **Why / evidence:** deviniti 2026-06-22 — 16 apps, 15 Forge + 1 Connect (coji.deviniti.com). Forge apps
  had zero externally-reachable surface; the whole unauth hunt collapsed to one Heroku/Spring backend.
- **Apply when:** Any Atlassian Marketplace (or similar plugin-marketplace) bounty program.
- **Provenance:** added 2026-06-22 · supporting runs: 1 (deviniti) · contradicting: 0

### L-040 · "Forge" marketplace apps often have HIDDEN Deviniti/vendor-hosted backends — find them via self-assessment + version-history baseUrl   [conf: high] · [recon/process]
- **Do:** Do NOT conclude a Forge-hosted marketplace app has "no external surface." Many Forge apps use
  **Forge Remote** to call a vendor backend (the real attack surface). Find it WITHOUT an instance:
  (1) `GET /rest/2/addons/<key>/privacy-and-security` → `thirdPartyInformation.thirdPartyDetails[]` names
  the cloud provider (Heroku/AWS/Azure/Hetzner) — proof a backend exists; (2) `GET /rest/2/addons/<key>/versions?limit=60`
  and grep for `baseUrl"` / `*.herokuapp.com` / `*.amazonaws.com` — apps that MIGRATED from Connect leak
  the old Connect baseUrl (the live backend host) in version history. These backends are "associated
  services attached to the instance" = IN SCOPE. Then run the Connect unauth battery (L-038) on each.
- **Why / evidence:** deviniti 2026-06-22 — initially classified 15/16 apps "Forge=no surface"; that was
  WRONG. version-history baseUrls revealed `prod-issue-sync-lite-proxy.herokuapp.com` (scopes incl
  `act_as_user`; SSRF via user-supplied "Remote URL") + `azure-sync.herokuapp.com`. Both real in-scope
  backends the first pass missed. (All hardened unauth, but the surface tripled.)
- **Apply when:** Any Atlassian/marketplace program with Forge apps. The self-assessment + version-history
  baseUrl is the cheapest backend-discovery OSINT.
- **Provenance:** added 2026-06-22 · supporting runs: 1 (deviniti) · contradicting: 0

### L-038 · Connect app unauth checklist: iframe-JWT, lifecycle/webhook JWT, actuator — usually all hardened on acspring   [conf: med] · [class/technique]
- **Do:** For an Atlassian Connect backend, the fast unauth battery (read-only GET + one approved bounded
  POST pair) is: (1) GET each iframe module URL w/o `?jwt=` → expect 401/403 (JWT gate); (2) param-reflect
  test on any GET module (check content-type — JSON+nosniff error = no XSS); (3) GET `/actuator`,
  `/actuator/{env,health,mappings}` (Spring backends) → expect 401; (4) the cross-instance/tenant-takeover
  test = bounded **POST /installed** with a UNIQUE non-colliding clientKey + NO JWT + `.invalid` baseUrl
  (never a real clientKey — that would hit a customer), and **POST /webhook/*** with junk ids → accept(200)
  = bug, 401 = secure. atlassian-connect-spring-boot enforces install+webhook JWT by default, so expect 401;
  the real bugs are AUTHENTICATED (cross-instance data keyed by a param the server trusts over the JWT `iss`).
- **Why / evidence:** deviniti coji 2026-06-22 — every unauth route 401/403/405, actuator 401, forged
  install + forged webhook both 401. Clean. All EV moved to authenticated cross-instance testing.
- **Apply when:** Any Atlassian Connect app backend (Spring Boot/Node acspring). POST tests need approval (g2).
- **Provenance:** added 2026-06-22 · supporting runs: 1 (deviniti) · contradicting: 0

### L-039 · Wayback CDX cracks the identity of a 404'ing Envoy/gateway host without scanning   [conf: high] · [recon/technique]
- **Do:** When a scope-ambiguous host returns a bare 404 at `/` (no descriptor, server: envoy/nginx)
  and you can't enumerate paths (scanner ban / unknown routes), query the Wayback CDX API
  (`http://web.archive.org/cdx/search/cdx?url=<host>*&output=text&fl=original,statuscode&collapse=urlkey`)
  to recover the real paths it has served. The path shapes identify the service: `/array/phc_*/config.js`
  + `/flags/?...ver=N` + `/static/array.js` = **PostHog analytics reverse-proxy** (the `phc_` key is a
  PUBLIC project key by design — NOT a secret/finding); `/_next/*` = Next.js; `/api/v*/` = the app API.
  This resolves scope (analytics proxy = not an app backend = usually OUT) with ZERO target scanning.
- **Why / evidence:** deviniti 2026-06-22 — `ac.deviniti.com` looked like the Forge apps' backend
  ("ac"=atlassian-connect hypothesis); Wayback CDX showed PostHog paths → it's an analytics proxy
  ("ac"=analytics-collector), out of scope, public key. Closed the last unauth thread honestly.
- **Apply when:** Any host whose role/scope is unclear and direct probing is blocked or unhelpful.
- **Provenance:** added 2026-06-22 · supporting runs: 1 (deviniti) · contradicting: 0

---

## Retired / disproven (do not relearn these)

_(none yet — when a lesson is contradicted twice, move it here with the reason.)_
