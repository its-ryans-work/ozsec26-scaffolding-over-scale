"""Build the three chain_findings variants to A/B test against the run33 failure.

run33 had the key, all three tokens including admin's, and attempted the decrypt. It
failed because it retyped "Vu1nB1az0r$ecretKey!2026@@@@@@@@" with SIX @ instead of eight,
measured the result (30 bytes), correctly suspected the @ count, then went looking in the
DLL with `strings` instead of re-reading the .cs file it already had, and gave up.

Two rules already forbade exactly this, in that exact phase, totalling 248 words:
  #2 "MEASURE THE MATERIAL, DO NOT EYEBALL IT ... counting repeated padding characters by
     eye has produced a wrong figure more than once"
  #3 "USE THE COPY YOU MEASURED ... retyping the value into a second command is where a
     character is gained or lost"

It obeyed #2 and violated #3. So the hypothesis under test is NOT that guidance is
missing - it is that 248 words in the largest playbook do not get read, and that the
demand has to be both shorter and positioned where it fires regardless of phase.

  A baseline  - exactly as run33 ran
  B merged    - #2 and #3 become one ~95-word technique (net -1), ending with the
                recovery step run33 never took: re-read from the same file
  C merged+cp - B, plus one line in the periodic checkpoint, which fires every 12 tool
                calls wherever the agent is. Relocation is what finally made the run26
                recording rule bind; this tests whether it works twice.
"""
import ast
import shutil
import sys
from pathlib import Path

SC = Path(__file__).parent
PB = SC / "playbooks"
OUT = SC / "variants"
OUT.mkdir(exist_ok=True)

PHASE = "Validate every finding against the live target"
MERGED = (
    "MEASURE THE MATERIAL AND USE THE COPY YOU MEASURED. Never count characters by eye - "
    "runs of repeated padding are miscounted and the machine is not. Read the literal out "
    "of the file with a command, hold it in a variable, print its length from that "
    "variable, and pass THAT SAME variable onward; retyping it into a second command is "
    "where a character is gained or lost. A plausible length is not a correct one: most "
    "ciphers accept several key sizes, so a bad extraction often lands on a legal one and "
    "simply produces garbage. IF THE LENGTH IS WRONG THE EXTRACTION IS WRONG, NOT THE "
    "SECRET - re-read it from the same file programmatically before doubting the value or "
    "reaching for a lower-level artifact."
)

CHECKPOINT_LINE = (
    '                "  4. Did you retype a recovered value into a command? If a '
    'secret, "\n'
    '                "key or token exists in a file, read it FROM that file in the '
    'same "\n'
    '                "command that uses it. A value you typed out by hand is '
    'unverified "\n'
    '                "however carefully you read it, and a length that comes back '
    'wrong "\n'
    '                "means the extraction is wrong, not the secret.",\n'
)


def techniques_of(src):
    tree = ast.parse(src)
    starts, acc = [0], 0
    for ln in src.splitlines(keepends=True):
        acc += len(ln)
        starts.append(acc)
    off = lambda l, c: starts[l - 1] + c
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Phase"):
            continue
        kw = {k.arg: k.value for k in node.keywords}
        if "techniques" not in kw:
            continue
        for i, elt in enumerate(kw["techniques"].elts, 1):
            out.append((kw["name"].value, i, ast.literal_eval(elt),
                        off(elt.lineno, elt.col_offset),
                        off(elt.end_lineno, elt.end_col_offset)))
    return out


def as_literal(text, indent):
    import textwrap
    pad = " " * indent
    lines = textwrap.wrap(text, 72 - indent)
    return "\n".join(f'{pad}"{l} "' for l in lines).lstrip()


def cut_line_span(src, s, e):
    """Delete the whole lines an element occupies, plus its trailing comma."""
    line_start = src.rfind("\n", 0, s) + 1
    end = e
    if src[end:end + 1] == ",":
        end += 1
    while end < len(src) and src[end] in " \t":
        end += 1
    if src[end:end + 1] == "\n":
        end += 1
    return src[:line_start] + src[end:]


def main():
    src = (PB / "chain_findings.py").read_text()
    shutil.copy(PB / "chain_findings.py", OUT / "A-chain_findings.py")

    techs = techniques_of(src)
    t2 = [t for t in techs if t[0] == PHASE and t[1] == 2]
    t3 = [t for t in techs if t[0] == PHASE and t[1] == 3]
    if not t2 or not t3:
        print("ABORT: could not locate #2/#3", file=sys.stderr)
        return 1
    if not t2[0][2].strip().startswith("MEASURE THE MATERIAL"):
        print(f"ABORT: #2 is not the measure rule: {t2[0][2][:60]!r}", file=sys.stderr)
        return 1
    if not t3[0][2].strip().startswith("USE THE COPY"):
        print(f"ABORT: #3 is not the copy rule: {t3[0][2][:60]!r}", file=sys.stderr)
        return 1

    before_words = len(t2[0][2].split()) + len(t3[0][2].split())

    # Remove #3 first (higher offset), then replace #2.
    new = cut_line_span(src, t3[0][3], t3[0][4])
    indent = t2[0][3] - (new.rfind("\n", 0, t2[0][3]) + 1)
    new = new[:t2[0][3]] + as_literal(MERGED, indent) + new[t2[0][4]:]

    after = techniques_of(new)
    assert len(after) == len(techs) - 1, f"expected -1 technique, got {len(after)-len(techs)}"
    merged_now = [t for t in after if t[0] == PHASE and t[1] == 2][0][2]
    assert " ".join(merged_now.split()) == " ".join(MERGED.split()), "merge text mismatch"
    # every other technique untouched
    keep_before = [t[2] for t in techs if (t[0], t[1]) not in {(PHASE, 2), (PHASE, 3)}]
    keep_after = [t[2] for t in after if not (t[0] == PHASE and t[1] == 2)]
    assert keep_before == keep_after, "a sibling technique changed"

    (OUT / "B-chain_findings.py").write_text(new)
    print(f"  B: merged #2+#3 -> one technique  ({before_words}w -> "
          f"{len(MERGED.split())}w, {len(techs)} -> {len(after)} techniques)")
    print(f"  C: same playbook as B, plus a checkpoint line in base_agent.py")
    (OUT / "C-checkpoint-line.txt").write_text(CHECKPOINT_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
