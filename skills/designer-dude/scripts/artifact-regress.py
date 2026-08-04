#!/usr/bin/env python3
"""Compare pinned visual and accessibility-tree evidence without dependencies.

This is a regression gate, not an aesthetic judge. It compares PNG pixels
after explicit masks and compares normalized ARIA snapshots. Baselines are
valid only when the runner recorded consecutive stable captures in a pinned
browser/font/OS environment.

  python3 artifact-regress.py --baseline .design/baseline \
      --current .design --out .design/artifact-regression.json

Optional mask JSON:
  {
    "masks": {"screenshots/dashboard-*.png": [[x, y, width, height]]},
    "ariaIgnorePatterns": ["Updated [0-9]+ minutes ago"]
  }
"""

import argparse
import fnmatch
import json
import pathlib
import re
import struct
import sys
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def chunks(data):
    pos = 8
    while pos + 12 <= len(data):
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        yield kind, body
        pos += 12 + size


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def read_png(path):
    data = pathlib.Path(path).read_bytes()
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    width = height = depth = color = interlace = None
    packed, palette, transparency = bytearray(), None, None
    for kind, body in chunks(data):
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            packed.extend(body)
        elif kind == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b"tRNS":
            transparency = body
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if depth != 8 or channels is None or interlace != 0:
        raise ValueError(f"unsupported PNG depth={depth} color={color} interlace={interlace}")
    raw = zlib.decompress(bytes(packed))
    stride, bpp, pos = width * channels, channels, 0
    prior, rows = bytearray(stride), []
    for _ in range(height):
        method, pos = raw[pos], pos + 1
        scan = bytearray(raw[pos:pos + stride]); pos += stride
        for i in range(stride):
            left = scan[i - bpp] if i >= bpp else 0
            up = prior[i]
            upper_left = prior[i - bpp] if i >= bpp else 0
            if method == 1:
                scan[i] = (scan[i] + left) & 255
            elif method == 2:
                scan[i] = (scan[i] + up) & 255
            elif method == 3:
                scan[i] = (scan[i] + ((left + up) // 2)) & 255
            elif method == 4:
                scan[i] = (scan[i] + paeth(left, up, upper_left)) & 255
            elif method != 0:
                raise ValueError(f"unknown PNG filter {method}")
        rows.append(scan); prior = scan
    pixels = []
    for row in rows:
        for i in range(0, len(row), channels):
            sample = row[i:i + channels]
            if color == 0:
                pixels.append((sample[0], sample[0], sample[0], 255))
            elif color == 2:
                pixels.append((sample[0], sample[1], sample[2], 255))
            elif color == 3:
                rgb = palette[sample[0]]
                alpha = transparency[sample[0]] if transparency and sample[0] < len(transparency) else 255
                pixels.append((*rgb, alpha))
            elif color == 4:
                pixels.append((sample[0], sample[0], sample[0], sample[1]))
            else:
                pixels.append(tuple(sample))
    return width, height, pixels


def png_chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)


def write_diff(path, width, height, before, after, changed):
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            i = y * width + x
            if changed[i]:
                rows.extend((255, 32, 32, 255))
            else:
                r, g, b, _ = after[i]
                grey = int((r + g + b) / 3)
                rows.extend((grey, grey, grey, 96))
    body = PNG_SIG
    body += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    body += png_chunk(b"IDAT", zlib.compress(bytes(rows), 9))
    body += png_chunk(b"IEND", b"")
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_bytes(body)


def masks_for(rel, config):
    found = []
    for pattern, rects in (config.get("masks") or {}).items():
        if fnmatch.fnmatch(rel, pattern):
            found.extend(rects)
    return found


def masked(x, y, rects):
    return any(len(r) == 4 and r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]
               for r in rects)


def normalize_aria(text, patterns):
    text = text.replace("\r\n", "\n").rstrip() + "\n"
    for pattern in patterns:
        text = re.sub(pattern, "<ignored>", text)
    return text


def relative_files(root, suffix):
    root = pathlib.Path(root)
    return {str(path.relative_to(root)): path for path in root.rglob(f"*{suffix}")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mask-config")
    ap.add_argument("--pixel-threshold", type=int, default=16,
                    help="maximum per-channel delta treated as anti-alias noise (default 16)")
    ap.add_argument("--max-diff-ratio", type=float, default=0.001,
                    help="unmasked changed-pixel ratio allowed per image (default 0.001)")
    args = ap.parse_args()
    config = json.loads(pathlib.Path(args.mask_config).read_text()) if args.mask_config else {}
    base_png, now_png = relative_files(args.baseline, ".png"), relative_files(args.current, ".png")
    base_aria, now_aria = relative_files(args.baseline, ".aria.yml"), relative_files(args.current, ".aria.yml")
    report = {"baseline": str(pathlib.Path(args.baseline).resolve()),
              "current": str(pathlib.Path(args.current).resolve()),
              "pixelThreshold": args.pixel_threshold, "maxDiffRatio": args.max_diff_ratio,
              "visual": [], "aria": [], "failures": []}
    diff_root = pathlib.Path(args.out).with_suffix("").parent / "artifact-diffs"

    for rel in sorted(set(base_png) | set(now_png)):
        if rel not in base_png or rel not in now_png:
            state = "missing-current" if rel not in now_png else "new-current"
            report["visual"].append({"path": rel, "status": state})
            report["failures"].append(f"visual {state}: {rel}")
            continue
        try:
            bw, bh, bp = read_png(base_png[rel]); nw, nh, np = read_png(now_png[rel])
            if (bw, bh) != (nw, nh):
                report["visual"].append({"path": rel, "status": "dimension-change",
                                         "baseline": [bw, bh], "current": [nw, nh]})
                report["failures"].append(f"visual dimensions changed: {rel}")
                continue
            rects, changed, eligible = masks_for(rel, config), [False] * len(bp), 0
            count, max_delta = 0, 0
            for i, (a, b) in enumerate(zip(bp, np)):
                x, y = i % bw, i // bw
                if masked(x, y, rects):
                    continue
                eligible += 1
                delta = max(abs(a[c] - b[c]) for c in range(4))
                max_delta = max(max_delta, delta)
                if delta > args.pixel_threshold:
                    changed[i] = True; count += 1
            ratio = count / eligible if eligible else 0
            status = "pass" if ratio <= args.max_diff_ratio else "regression"
            row = {"path": rel, "status": status, "changedPixels": count,
                   "eligiblePixels": eligible, "diffRatio": round(ratio, 8),
                   "maxChannelDelta": max_delta, "masks": rects}
            if status == "regression":
                diff = diff_root / rel
                write_diff(diff, bw, bh, bp, np, changed)
                row["diffImage"] = str(diff)
                report["failures"].append(f"visual regression {ratio:.4%}: {rel}")
            report["visual"].append(row)
        except Exception as exc:
            report["visual"].append({"path": rel, "status": "unreadable", "reason": str(exc)})
            report["failures"].append(f"visual unreadable: {rel}: {exc}")

    ignore = config.get("ariaIgnorePatterns") or []
    for rel in sorted(set(base_aria) | set(now_aria)):
        if rel not in base_aria or rel not in now_aria:
            state = "missing-current" if rel not in now_aria else "new-current"
            report["aria"].append({"path": rel, "status": state})
            report["failures"].append(f"ARIA {state}: {rel}")
            continue
        before = normalize_aria(base_aria[rel].read_text(), ignore)
        after = normalize_aria(now_aria[rel].read_text(), ignore)
        status = "pass" if before == after else "regression"
        report["aria"].append({"path": rel, "status": status})
        if status == "regression":
            report["failures"].append(f"ARIA regression: {rel}")

    report["status"] = "pass" if not report["failures"] else "fail"
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(f"artifact regression: {report['status']} -> {args.out}")
    print(f"visual {len(report['visual'])} · ARIA {len(report['aria'])} · failures {len(report['failures'])}")
    if report["failures"]:
        for failure in report["failures"][:20]:
            print("  " + failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
