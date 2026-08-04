# claude-skills

A version-controlled home for my custom [Claude Code](https://claude.com/claude-code)
skills. Each skill lives under [`skills/`](./skills) and is made available to
Claude **globally** (in every project, on this machine) via a symlink from the
global skills directory.

## How global access works

Claude Code discovers skills in `~/.claude/skills/`. Rather than keeping the real
skill folders there, this repo holds the source of truth and the global directory
just points at it:

```
~/.claude/skills/<skill>  ->  /home/drago/claude-skills/skills/<skill>
```

Because the global location is a symlink into this repo, the skills are editable
and version-controlled here, yet usable from any working directory.

## Skills in this repo

These are my own authored skills (Claude Code plugins are
intentionally **not** included — they manage and update themselves separately):

- Engineering modes: `back-end-dude`, `front-end-dude`, `designer-dude`,
  `debug-dude`, `contractor-dude`, `qa-dude`, `retro-dude`, `plan-dude`
- Applied AI/ML: `aiml-dude`
- Code review: `general-code-review`, `fe-code-review`, `be-code-review`,
  `be2-code-review`, `nextjs-code-review`, `code-quality`
- Security / bug bounty: `security-dude`, `bug-hunt`, `fleet-hunt`,
  `pick-program`, `vuln-research`, `h1-report`, `bug-finder-dude`
- Orchestration / ops: `orchestrate`, `helm`, `push-dude`, `checker`
- User testing: `user-test`, `user-test-2`, `user-test-massive`,
  `user-test-miskari`
- Marketing / SEO: `seo-dude`
- Product / research: `book-to-product`
- Misc: `logo-design`, `cruise-planner`, `flight-finder`, `round-trip-stocks`

### `seo-dude` — note on structure

`seo-dude` is the first skill here to use **`SKILL.md` + `references/`** rather
than a single file. Eight reference files (technical audit, content & keywords,
authority & links, vertical/local/international, penalties & recovery, report
format, **currency check**, **obsolescence & claims**) are loaded on demand, so a
quick scoped run doesn't pay for the full corpus. `designer-dude`,
`user-test-miskari`, and `aiml-dude` now follow the same pattern; the rest of the
repo remains single-file.

Two of those references are load-bearing in an unusual way and are read on
**every** run:

- **`07-currency-2026.md`** — the skill's substance is distilled from a 2023 book,
  and search changed more between 2024 and 2026 than in the decade before. This
  file carries the corrections (INP replaced FID, Helpful Content folded into
  core, FAQ/HowTo rich results retired, AI Overviews breaking the
  rank→CTR→sessions chain), tiered **DOCUMENTED / KNOW / BELIEVE / FOLKLORE**, and
  **it overrides anything in `01`–`06` it contradicts**. It has an expiry date and
  says so; the skill re-verifies it live when stale.
- **`08-obsolescence-and-claims.md`** — the inverse risk. SEO writing peaked as a
  volume phenomenon around 2008–2014, so a model's default recommendation is
  frequently *mainstream white-hat best practice from a decade ago*. That advice
  breaks no rules, triggers no penalty, and simply wastes a quarter. This file is
  the deny-list for it, plus the unresolvable claims to assert nothing about and
  the attribution discipline for what counts as evidence.

**Re-verify `07` quarterly.** A stale currency file is worse than none, because
the skill states its contents with confidence.

## Adding a new skill

Create it inside this repo and symlink it into the global directory:

```bash
# author the skill here
mkdir -p skills/my-skill && $EDITOR skills/my-skill/SKILL.md

# make it globally available
ln -s "$PWD/skills/my-skill" ~/.claude/skills/my-skill
```

## Re-linking on a new machine

After cloning this repo to `<path>`, point the global directory at each skill:

```bash
for d in <path>/claude-skills/skills/*/; do
  ln -s "$d" ~/.claude/skills/"$(basename "$d")"
done
```

## Notes

- Skills authored inside *other* project repos (e.g. `write-article`)
  are left where they live and symlinked into `~/.claude/skills/` from there —
  they are not duplicated into this repo.
- `memory/LESSONS.md` files (curated, accumulated knowledge) are tracked.
  `memory/*-log.jsonl` run logs are git-ignored — they are mutable runtime state.
