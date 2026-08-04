#!/usr/bin/env python3
"""Per-section token accounting for a system prompt.

Answers the three questions AIPATH.md Section 3 and the standing budget
gates need, without guessing:

  1. How many tokens is each section of the prompt?
  2. Which sections are the biggest, i.e. where is the dead weight?
  3. Does the static cache prefix still fit the 2000-token budget?

Exists because the old instruction was "wc -w times 1.3, flag as
approximate". That is fine for a total and useless for the actual
decision, which is always per-section: this block costs 180 tokens and
a role-first rewrite does the same job in 65. You cannot make that call
from a whole-file word count.

ACCURACY. This is a heuristic, not a tokenizer. It blends a chars/4 and a
words*1.33 estimate, which lands within roughly +/-15% of a real BPE count
on English prose, and drifts wider on code, markup, and heavy punctuation.
Every number it prints is labelled approximate. That is honest and it is
enough for "which section is fat" and for a budget check with headroom.
It is NOT enough to certify a prefix at 1990 of 2000 tokens. If the repo
has a real tokenizer, use it and say which you used.

Usage:
  prompt_tokens.py src/app/api/chat/prompt.ts --extract-template
  prompt_tokens.py AIPATH.md --top 5
  prompt_tokens.py prompt.ts --extract-template --boundary "## User profile"
  prompt_tokens.py --selftest

Flags:
  --extract-template  Pull the contents of backtick template literals only,
                      so TypeScript scaffolding is not counted as prompt.
  --boundary TEXT     Everything before the line containing TEXT counts as
                      the static cache prefix; everything after is dynamic.
  --budget N          Prefix budget in tokens (default 2000).
  --top N             Show only the N largest sections.
"""

import argparse
import re
import sys

DEFAULT_BUDGET = 2000
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*\S)\s*$")


def estimate_tokens(text):
    """Blend a char-based and a word-based estimate.

    chars/4 is the standard rule of thumb and over-counts whitespace-heavy
    markdown. words*1.33 under-counts punctuation and code. Averaging the
    two is more stable across the mix of prose, bullets, and inline schema
    that a real system prompt contains than either alone.
    """
    if not text.strip():
        return 0
    by_chars = len(text) / 4.0
    by_words = len(text.split()) * 1.33
    return int(round((by_chars + by_words) / 2.0))


def extract_template_literals(source):
    """Concatenate the contents of backtick template literals.

    A system prompt living in a .ts file is inside backticks; the imports,
    exports, and function signature around it are not prompt and must not
    be billed as prompt. Deliberately simple: it does not parse nested
    template expressions, and it says so when it finds none.
    """
    out = []
    i = 0
    n = len(source)
    while i < n:
        if source[i] == "`":
            j = i + 1
            buf = []
            while j < n:
                if source[j] == "\\" and j + 1 < n:
                    buf.append(source[j + 1])
                    j += 2
                    continue
                if source[j] == "`":
                    break
                buf.append(source[j])
                j += 1
            out.append("".join(buf))
            i = j + 1
        else:
            i += 1
    return "\n".join(out)


def split_sections(text):
    """Split on markdown headings. Returns [(title, level, start_line, body)]."""
    lines = text.split("\n")
    sections = []
    current_title = "(preamble)"
    current_level = 0
    current_start = 1
    buf = []
    for lineno, line in enumerate(lines, start=1):
        m = HEADING.match(line)
        if m:
            if buf or sections or current_title != "(preamble)":
                sections.append((current_title, current_level, current_start, "\n".join(buf)))
            current_title = m.group(2)
            current_level = len(m.group(1))
            current_start = lineno
            buf = []
        else:
            buf.append(line)
    sections.append((current_title, current_level, current_start, "\n".join(buf)))
    # Drop an empty synthetic preamble.
    if sections and sections[0][0] == "(preamble)" and not sections[0][3].strip():
        sections = sections[1:]
    return sections


def report(text, args):
    sections = split_sections(text)
    total = estimate_tokens(text)
    rows = []
    for title, level, start, body in sections:
        tok = estimate_tokens(body) + estimate_tokens("#" * level + " " + title)
        rows.append({"title": title, "level": level, "line": start, "tokens": tok})

    display = sorted(rows, key=lambda r: -r["tokens"])[: args.top] if args.top else rows

    print(f"TOTAL ~{total} tokens (approximate, heuristic — see script docstring)")
    print(f"{len(rows)} sections")
    print()
    width = max((len(r["title"]) for r in display), default=10)
    width = min(max(width, 20), 52)
    print(f"{'line':>5}  {'section'.ljust(width)}  {'~tokens':>8}  {'share':>6}")
    print(f"{'-'*5}  {'-'*width}  {'-'*8}  {'-'*6}")
    for r in display:
        share = (r["tokens"] / total * 100) if total else 0
        title = ("  " * (r["level"] - 1) if r["level"] > 0 else "") + r["title"]
        if len(title) > width:
            title = title[: width - 1] + "…"
        print(f"{r['line']:>5}  {title.ljust(width)}  {r['tokens']:>8}  {share:>5.1f}%")

    if args.top and len(rows) > args.top:
        print(f"\n({len(rows) - args.top} smaller sections hidden by --top {args.top})")

    print()
    if args.boundary:
        lines = text.split("\n")
        cut = None
        for i, line in enumerate(lines):
            if args.boundary in line:
                cut = i
                break
        if cut is None:
            print(f"CACHE PREFIX: boundary text {args.boundary!r} not found in the file.")
            print("Nothing measured. Fix the boundary string rather than assuming it fits.")
        else:
            prefix = "\n".join(lines[:cut])
            dynamic = "\n".join(lines[cut:])
            p_tok = estimate_tokens(prefix)
            d_tok = estimate_tokens(dynamic)
            print(f"CACHE PREFIX (lines 1-{cut}):   ~{p_tok} tokens")
            print(f"DYNAMIC TAIL  (lines {cut + 1}-{len(lines)}): ~{d_tok} tokens")
            verdict(p_tok, args.budget)
    else:
        print("Whole file treated as static prefix (no --boundary given).")
        verdict(total, args.budget)


def verdict(tokens, budget):
    headroom = budget - tokens
    print()
    if tokens > budget:
        print(f"OVER BUDGET by ~{-headroom} tokens (budget {budget}).")
        print("Cut before adding. The kill-a-feature discipline exists for this:")
        print("ignored instructions, conflicting instructions, and guidance for")
        print("scenarios that never appear in real transcripts all go first.")
    elif headroom < budget * 0.1:
        print(f"WITHIN BUDGET but only ~{headroom} tokens of headroom (budget {budget}).")
        print("The estimate carries roughly +/-15% error, which is wider than this")
        print("margin. Treat the prefix as effectively at budget and confirm with a")
        print("real tokenizer before adding anything.")
    else:
        print(f"WITHIN BUDGET: ~{headroom} tokens of headroom (budget {budget}).")


def selftest():
    failures = []

    def check(name, got, want):
        ok = got == want
        if not ok:
            failures.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")

    print("estimate_tokens")
    check("empty is zero", estimate_tokens(""), 0)
    check("whitespace is zero", estimate_tokens("   \n  "), 0)
    monotonic = estimate_tokens("word " * 100) > estimate_tokens("word " * 10)
    check("monotonic in length", monotonic, True)
    # A 1000-word English passage should land in a plausible BPE range.
    est = estimate_tokens("the quick brown fox jumps over a lazy dog " * 111)
    check("1000 words lands in 1100-1500", 1100 <= est <= 1500, True)

    print("extract_template_literals")
    src = 'export const P = `Hello\nworld`;\nconst x = 1;\n'
    check("pulls literal body", extract_template_literals(src), "Hello\nworld")
    check("no literals -> empty", extract_template_literals("const x = 1;"), "")
    check("escaped backtick survives",
          extract_template_literals(r'`a\`b`'), "a`b")

    print("split_sections")
    doc = "# A\nalpha\n## B\nbeta\n### C\ngamma\n"
    secs = split_sections(doc)
    check("three sections", len(secs), 3)
    check("titles", [s[0] for s in secs], ["A", "B", "C"])
    check("levels", [s[1] for s in secs], [1, 2, 3])
    check("start lines", [s[2] for s in secs], [1, 3, 5])
    check("preamble kept when present",
          split_sections("intro\n# A\nx")[0][0], "(preamble)")
    check("empty preamble dropped",
          split_sections("\n# A\nx")[0][0], "A")
    # A '#' inside a fenced code block is not a heading we care about, but
    # neither is it common in a system prompt; document the known limit.
    check("indented 4+ spaces is not a heading",
          len(split_sections("    # not a heading\ntext")), 1)

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("all selftests passed")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Per-section token accounting for a system prompt.",
    )
    parser.add_argument("path", nargs="?", help="prompt file (.ts, .md, .txt)")
    parser.add_argument("--extract-template", action="store_true",
                        help="count only the contents of backtick template literals")
    parser.add_argument("--boundary", help="text marking the end of the static cache prefix")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--top", type=int, help="show only the N largest sections")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.path:
        parser.print_help()
        sys.exit(1)

    try:
        with open(args.path) as fh:
            text = fh.read()
    except OSError as exc:
        raise SystemExit(f"cannot read {args.path}: {exc}")

    if args.extract_template:
        extracted = extract_template_literals(text)
        if not extracted.strip():
            raise SystemExit(
                f"{args.path}: --extract-template found no backtick literals. "
                "Rerun without the flag, or check that the prompt really lives in one."
            )
        text = extracted

    report(text, args)


if __name__ == "__main__":
    main()
