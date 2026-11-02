"""Remove the 33 evidence-backed dead techniques from the playbooks.

Deletion is done through AST source offsets, not text matching: every technique is
a list element built from implicitly concatenated string literals, so its exact
source span is known and the surrounding formatting is untouched.

Refuses to run unless the local copy is byte-identical to the box, so this can
never silently patch a stale snapshot.

Verifies after writing: each file still parses, the technique count dropped by
exactly the number targeted, and every surviving technique's text is unchanged.
"""
import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

SC = Path(__file__).parent
PB = SC / "playbooks"
TARGETS = json.load(open(SC / "final-deletions.json"))
LIVE_MD5 = dict(
    line.split("  ")[::-1] for line in (SC / "live-md5.txt").read_text().splitlines()
    if "  " in line
)


def techniques_of(src):
    """[(phase, idx, text, start_offset, end_offset)] over the source string."""
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))

    def off(lineno, col):
        return starts[lineno - 1] + col

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Phase"):
            continue
        kw = {k.arg: k.value for k in node.keywords}
        if "techniques" not in kw:
            continue
        phase = kw["name"].value
        for i, elt in enumerate(kw["techniques"].elts, 1):
            out.append((phase, i, ast.literal_eval(elt),
                        off(elt.lineno, elt.col_offset),
                        off(elt.end_lineno, elt.end_col_offset)))
    return out


def main():
    by_pb = {}
    for t in TARGETS:
        by_pb.setdefault(t["playbook"], []).append((t["phase"], t["idx"]))

    # Guard: refuse to patch a stale snapshot.
    for pb in by_pb:
        p = PB / f"{pb}.py"
        got = hashlib.md5(p.read_bytes()).hexdigest()
        want = LIVE_MD5.get(f"{pb}.py")
        if got != want:
            print(f"ABORT: {pb}.py differs from the box ({got} vs {want})", file=sys.stderr)
            return 1
    print(f"checksum guard passed for {len(by_pb)} playbooks\n")

    total = 0
    for pb, keys in sorted(by_pb.items()):
        p = PB / f"{pb}.py"
        src = p.read_text()
        before = techniques_of(src)
        want = set(keys)
        doomed = [t for t in before if (t[0], t[1]) in want]
        if len(doomed) != len(want):
            print(f"ABORT: {pb}: matched {len(doomed)} of {len(want)} targets",
                  file=sys.stderr)
            return 1

        # Cut whole lines: from the start of the element's first line through the
        # newline after its trailing comma. Taking only the element's own span and
        # then eating the following whitespace stole the NEXT element's
        # indentation, leaving it flush against the margin.
        # Cut from the end so earlier offsets stay valid.
        new = src
        for _, _, _, s, e in sorted(doomed, key=lambda t: -t[3]):
            line_start = new.rfind("\n", 0, s) + 1        # 0 if on the first line
            assert new[line_start:s].strip() == "", \
                "element does not start its own line; refusing to cut"
            end = e
            if new[end:end + 1] == ",":
                end += 1
            while end < len(new) and new[end] in " \t":
                end += 1
            if new[end:end + 1] == "\n":
                end += 1
            new = new[:line_start] + new[end:]

        after = techniques_of(new)          # raises if the file no longer parses
        assert len(after) == len(before) - len(doomed), (
            f"{pb}: expected {len(before) - len(doomed)} techniques, got {len(after)}")
        survivors_before = {t[2] for t in before} - {t[2] for t in doomed}
        assert {t[2] for t in after} == survivors_before, \
            f"{pb}: surviving technique text changed"

        shutil.copy(p, PB / f"{pb}.py.orig-preDeInstruct")
        p.write_text(new)
        total += len(doomed)
        print(f"  {pb:24} {len(before):3} -> {len(after):3} techniques "
              f"(-{len(doomed)})")

    print(f"\nremoved {total} techniques; every file re-parsed and every "
          f"survivor verified byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
