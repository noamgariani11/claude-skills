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

These are my own authored skills (the gstack package and Claude Code plugins are
intentionally **not** included — they manage and update themselves separately):

- Engineering modes: `back-end-dude`, `front-end-dude`, `designer-dude`,
  `debug-dude`, `contractor-dude`, `qa-dude`, `retro-dude`, `plan-dude`
- Code review: `general-code-review`, `fe-code-review`, `be-code-review`,
  `be2-code-review`, `nextjs-code-review`, `code-quality`
- Security / bug bounty: `security-dude`, `bug-hunt`, `fleet-hunt`,
  `pick-program`, `vuln-research`, `h1-report`, `bug-finder-dude`
- Orchestration / ops: `orchestrate`, `helm`, `push-dude`, `checker`
- User testing: `user-test`, `user-test-2`, `user-test-massive`,
  `user-test-miskari`
- Misc: `logo-design`, `cruise-planner`, `flight-finder`, `round-trip-stocks`

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

- Skills authored inside *other* project repos (e.g. `aiml-dude`, `write-article`)
  are left where they live and symlinked into `~/.claude/skills/` from there —
  they are not duplicated into this repo.
- `memory/LESSONS.md` files (curated, accumulated knowledge) are tracked.
  `memory/*-log.jsonl` run logs are git-ignored — they are mutable runtime state.
