#!/usr/bin/env python3
"""Wiki link audit — run before uploading droid-wiki/ to the Factory app.

Checks every markdown link in droid-wiki/ for four failure classes. The last one
is invisible from a plain filesystem check and is the reason this script exists:
the published wiki receives ONLY the droid-wiki/ subtree, so a link from a wiki
page to anything outside it (../../pilots/, ../../PRD.md) resolves locally and
404s for anyone reading the wiki in the app.

  dead      — target file does not exist on disk
  anchor    — target file exists but has no matching #heading
  absolute  — http(s):// link on a wiki page (house rule: backticked repo paths
              or in-wiki relative links only; absolute URLs got scrubbed once and
              should not creep back)
  escaping  — a droid-wiki/ page links to a path outside droid-wiki/ (resolves in
              git, 404s in the published wiki)

Exit 0 = clean, exit 1 = findings. Assert on the published boundary, not the disk.
"""

import os
import re
import sys

WIKI = "droid-wiki"
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def slug(heading):
    h = heading.strip().lower()
    h = re.sub(r"[^\w\s-]", "", h)
    return re.sub(r"\s+", "-", h)


def anchors_of(path):
    out = set()
    with open(path, errors="ignore") as f:
        for line in f:
            m = re.match(r"#+\s+(.*)", line)
            if m:
                out.add(slug(m.group(1)))
    return out


def skeleton_drift():
    """The landing page carries the loop twice: once as the method practiced today,
    once with the enforcement layer on top. The second only reads as "the same shape,
    now enforced" if it IS the same shape plus annotation.

    Node-set equality was the first cut at this, and it was a proxy rather than the
    invariant: it holds only while the overlay lives entirely in edge labels, and it
    breaks the moment the overlay needs a node of its own. Assert the real thing:

      1. every diagram-1 node still appears in diagram 2 (the flow is preserved), and
      2. any node diagram 2 adds is annotation only -- it may attach with a dotted
         edge (-.->) but never with a solid one, so an overlay cannot quietly join
         the flow and turn diagram 2 into a different picture.
    """
    page = os.path.join(WIKI, "overview", "index.md")
    if not os.path.exists(page):
        return []
    blocks = re.findall(r"```mermaid(.*?)```", open(page, encoding="utf-8").read(), re.S)
    if len(blocks) != 2:
        return []
    nodes = [set(re.findall(r"([A-Z][A-Z0-9]*)\s*(?:\[|\{)", b)) for b in blocks]
    out = []
    missing = sorted(nodes[0] - nodes[1])
    if missing:
        out.append(("skeleton", page, f"diagram 2 dropped diagram 1 node(s): {', '.join(missing)}"))
    solid = [ln for ln in blocks[1].splitlines() if "-->" in ln]
    for extra in sorted(nodes[1] - nodes[0]):
        if any(re.search(rf"\b{re.escape(extra)}\b", ln) for ln in solid):
            out.append(("skeleton", page, f"overlay node {extra} joins the flow with a solid edge"))
    return out


def main():
    root = os.getcwd()
    if not os.path.isdir(WIKI):
        print(f"error: run from repo root (no {WIKI}/ here)", file=sys.stderr)
        return 2

    anchor_cache = {}
    findings = []
    page_count = 0

    for dp, _, files in os.walk(WIKI):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            page = os.path.normpath(os.path.join(dp, fn))
            page_count += 1
            base = os.path.dirname(page)
            with open(page, errors="ignore") as f:
                body = f.read()
            for _text, url in LINK.findall(body):
                if url.startswith("mailto:"):
                    continue
                if url.startswith("http://") or url.startswith("https://"):
                    findings.append(("absolute", page, url))
                    continue
                path, _, frag = url.partition("#")
                if path == "":
                    target = page  # same-page anchor
                else:
                    target = os.path.normpath(os.path.join(base, path))
                    # escaping: a wiki page pointing outside the published subtree
                    if not (target + os.sep).startswith(WIKI + os.sep) and target != WIKI:
                        findings.append(("escaping", page, url))
                if not os.path.exists(target):
                    findings.append(("dead", page, url))
                    continue
                if frag and target.endswith(".md"):
                    if target not in anchor_cache:
                        anchor_cache[target] = anchors_of(target)
                    if frag not in anchor_cache[target]:
                        findings.append(("anchor", page, url))

    findings += skeleton_drift()

    counts = dict.fromkeys(("dead", "anchor", "absolute", "escaping", "skeleton"), 0)
    for kind, _p, _u in findings:
        counts[kind] += 1
    summary = " ".join(f"{k}={counts[k]}" for k in counts)
    print(f"{page_count} pages · {summary}")

    if findings:
        for kind, page, url in findings:
            rel = os.path.relpath(page, root)
            print(f"  {kind.upper():9} {rel}  ->  {url}")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
