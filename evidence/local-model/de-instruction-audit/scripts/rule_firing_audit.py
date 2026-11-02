"""Rule 2 of the de-instruction plan: find playbook techniques that never fired.

The roadmap's stated method - "grep each technique's distinctive phrase against the
phase logs" - is wrong twice over, and both faults push in opposite directions:

  1. Every phase log OPENS with a Rich panel that prints the playbook verbatim.
     A naive grep therefore matches every technique in every run and concludes
     that nothing is dead.
  2. That panel is wrapped at the console width with box-drawing borders, so a
     phrase like "is NOT evidence of absence" is split across two lines by a
     "|" and a newline. A naive grep therefore finds nothing and concludes that
     everything is dead.

So: strip the banner, unwrap the borders, normalise whitespace, and match on word
n-grams rather than on raw substrings.

EVIDENCE TIERS
  RESTATED  - a >=5-word run of the technique's own wording appears in the agent's
              own output after the banner. Near-proof the rule was read and used.
  TOPICAL   - the technique's distinctive tokens appear, but its wording never does.
              The agent worked the subject; whether this rule caused that is unknown.
  NO TRACE  - neither. Nothing in ~11 runs shows this text influencing anything.

Only NO TRACE is a deletion candidate on evidence. TOPICAL is a candidate on
judgement - the topic was covered whether or not this sentence existed.
"""
import ast
import re
import sys
from collections import Counter
from pathlib import Path

SC = Path(__file__).parent
PLAYBOOKS = SC / "playbooks"
LOGS = SC / "logs"

# The 13 playbooks the v3 runner actually executes, in pipeline order.
IN_PIPELINE = [
    "web_discovery", "blazor_wasm", "a01_a07_access_auth", "a02_misconfiguration",
    "a04_cryptographic", "a05_injection", "a08_integrity", "a09_logging_alerting",
    "a10_exceptional", "consolidate_findings", "chain_findings",
    "adversarial_review", "final_integrity_gate",
]

BOX = "─│┌┐└┘├┤┬┴┼╭╮╯╰╱╲╴╵╶╷╸╹╺╻═║╔╗╚╝╡╤╧╪█░▒▓●•"
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_WORD = re.compile(r"[a-z0-9_./+-]+")


def words_of(text):
    """Tokenise, keeping interior punctuation (strings -e l, /api/auth, q4_0) but
    dropping the sentence punctuation that would otherwise make 'absence.' and
    'absence' two different tokens - which silently deflated every coverage score."""
    out = []
    for w in _WORD.findall(text.lower()):
        w = w.strip("._-+")
        if w:
            out.append(w)
    return out

STOP = set("""a an the and or but if then than that this these those is are was were be been being
of in on at to for from by with without into over under about as it its it's their there here
you your we our they them he she his her not no nor do does did done doing have has had having
can could should would may might must will shall each every any all both few more most other
some such only own same so too very just now new only when where which who whom whose what why
how any also per via use used using make makes made get gets got give gives given take takes
one two three first second next last same different""".split())


def load_techniques():
    """Parse Phase(...) calls out of each playbook with ast - no import, no execution."""
    out = []
    for pb in IN_PIPELINE:
        path = PLAYBOOKS / f"{pb}.py"
        if not path.exists():
            print(f"!! missing playbook {path}", file=sys.stderr)
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Phase"):
                continue
            kw = {k.arg: k.value for k in node.keywords}
            pname = kw["name"].value if "name" in kw else "?"
            techs = kw.get("techniques")
            if techs is None:
                continue
            for i, elt in enumerate(techs.elts, 1):
                try:
                    text = ast.literal_eval(elt)
                except Exception:
                    continue
                out.append({
                    "playbook": pb, "phase": pname, "idx": i,
                    "text": " ".join(text.split()),
                })
    return out


def strip_banner(raw):
    """Drop every Rich panel that reprints the playbook, keep the agent's own output.

    A phase can restart (supervisor respawn), so remove ALL such panels rather than
    assuming one at the top. The panel is identified by its own marker line, and the
    region runs from the opening box corner to the next closing one.
    """
    lines = raw.splitlines()
    marks = [i for i, ln in enumerate(lines) if "PENTESTAGENT - Non-interactive Mode" in ln]
    drop = set()
    for m in marks:
        start = m
        while start > 0 and not lines[start].lstrip().startswith("╭"):
            start -= 1
        end = m
        while end < len(lines) - 1 and not lines[end].lstrip().startswith("╰"):
            end += 1
        drop.update(range(start, end + 1))
    # Also drop the two plain "Loaded playbook:" / "Description:" preamble lines,
    # which repeat the playbook description outside any panel.
    for i, ln in enumerate(lines):
        if ln.startswith(("Loaded playbook:", "Description:", "Mode: ")):
            drop.add(i)
    return "\n".join(ln for i, ln in enumerate(lines) if i not in drop)


def normalize(text):
    """Box-drawn, wrapped console output -> one flat lowercase word stream."""
    text = ANSI.sub(" ", text)
    text = text.translate({ord(c): " " for c in BOX})
    return " ".join(words_of(text))


def ngram_hashes(words, n):
    return {hash(tuple(words[i:i + n])) for i in range(len(words) - n + 1)}


def main():
    techniques = load_techniques()
    logs = sorted(p for p in LOGS.rglob("[0-9][0-9]-*.log"))

    # Dedupe: run20/run21 exist both locally and in the coldstart archive.
    seen_size = {}
    kept = []
    for p in logs:
        key = (p.name, p.stat().st_size)
        if key in seen_size:
            continue
        seen_size[key] = p
        kept.append(p)
    logs = kept

    runs = sorted({str(p.parent.relative_to(LOGS)) for p in logs})
    run_bit = {r: 1 << i for i, r in enumerate(runs)}

    print(f"techniques: {len(techniques)} across {len(IN_PIPELINE)} in-pipeline playbooks")
    print(f"logs:       {len(logs)} phase logs across {len(runs)} runs\n")

    # --- index the corpus, SCOPED PER PLAYBOOK ----------------------------
    # A chain_findings rule whose words turn up in web_discovery's log is not
    # evidence that the chain_findings rule fired. Every test below is therefore
    # scoped to logs of the playbook that owns the technique.
    NS = (10, 8, 6, 5, 4)
    index = {pb: {n: {} for n in NS} for pb in IN_PIPELINE}
    tokens_seen = {pb: Counter() for pb in IN_PIPELINE}
    logs_per_pb = Counter()
    total_body_words = 0
    banner_words = 0

    for p in logs:
        pb = p.stem.split("-", 1)[1] if "-" in p.stem else p.stem
        if pb not in index:
            continue
        raw = p.read_text(errors="replace")
        body = strip_banner(raw)
        banner_words += len(normalize(raw).split()) - len(normalize(body).split())
        words = normalize(body).split()
        total_body_words += len(words)
        logs_per_pb[pb] += 1
        bit = run_bit[str(p.parent.relative_to(LOGS))]
        for w in set(words):
            tokens_seen[pb][w] += 1
        for n in NS:
            idx = index[pb][n]
            for h in ngram_hashes(words, n):
                idx[h] = idx.get(h, 0) | bit

    print(f"corpus:     {total_body_words:,} words of agent output "
          f"(banner stripped {banner_words:,} words)")
    print("logs per playbook: "
          + ", ".join(f"{pb}={logs_per_pb[pb]}" for pb in IN_PIPELINE) + "\n")

    # --- token document-frequency across TECHNIQUES, to find generic vocabulary
    tech_df = Counter()
    for t in techniques:
        for w in set(words_of(t["text"])):
            if w not in STOP and len(w) > 2:
                tech_df[w] += 1
    generic_cut = max(3, int(0.06 * len(techniques)))

    # --- score ------------------------------------------------------------
    results = []
    for t in techniques:
        pb = t["playbook"]
        words = normalize(t["text"]).split()
        best_n, best_bits = 0, 0
        for n in NS:
            if len(words) < n:
                continue
            bits = 0
            for i in range(len(words) - n + 1):
                bits |= index[pb][n].get(hash(tuple(words[i:i + n])), 0)
            if bits:
                best_n, best_bits = n, bits
                break

        sig = sorted(
            (w for w in set(words) if w not in STOP and len(w) > 2
             and tech_df[w] <= generic_cut),
            key=lambda w: (tech_df[w], -len(w)),
        )[:6]
        hits = [w for w in sig if tokens_seen[pb][w]]
        cov = len(hits) / len(sig) if sig else 0.0

        if best_n:
            tier = "RESTATED"
        elif sig and cov >= 0.5:
            tier = "TOPICAL"
        else:
            tier = "NO-TRACE"

        results.append({**t, "tier": tier, "n": best_n,
                        "runs": bin(best_bits).count("1"),
                        "sig": sig, "cov": cov, "words": len(words)})

    # --- report -----------------------------------------------------------
    order = {"NO-TRACE": 0, "TOPICAL": 1, "RESTATED": 2}
    counts = Counter(r["tier"] for r in results)
    print("=" * 78)
    print("TIER SUMMARY")
    print("=" * 78)
    for tier in ("RESTATED", "TOPICAL", "NO-TRACE"):
        print(f"  {tier:9} {counts[tier]:3}  ({counts[tier] / len(results) * 100:.0f}%)")

    print("\n" + "=" * 78)
    print("BY PLAYBOOK")
    print("=" * 78)
    print(f"{'playbook':24} {'tot':>4} {'rest':>5} {'topi':>5} {'none':>5}   dead%")
    for pb in IN_PIPELINE:
        rs = [r for r in results if r["playbook"] == pb]
        if not rs:
            continue
        c = Counter(r["tier"] for r in rs)
        dead = c["NO-TRACE"] / len(rs) * 100
        print(f"{pb:24} {len(rs):4} {c['RESTATED']:5} {c['TOPICAL']:5} "
              f"{c['NO-TRACE']:5}   {dead:4.0f}%")

    # --- is a dead technique dead, or merely never reached? ---------------
    # Phases run in order and a playbook can hit its iteration cap partway
    # through. If NO-TRACE clusters in the LAST phases of a playbook, the tail
    # is unreached, not useless - and deleting it would be the wrong fix.
    print("\n" + "=" * 78)
    print("PHASE POSITION OF DEAD RULES - unreached tail, or genuinely dead?")
    print("=" * 78)
    for pb in IN_PIPELINE:
        rs = [r for r in results if r["playbook"] == pb]
        if not rs:
            continue
        phases = []
        for r in rs:
            if r["phase"] not in phases:
                phases.append(r["phase"])
        print(f"\n{pb}  ({len(phases)} phases, {len(rs)} techniques)")
        for pi, ph in enumerate(phases, 1):
            prs = [r for r in rs if r["phase"] == ph]
            c = Counter(r["tier"] for r in prs)
            bar = ("R" * c["RESTATED"]) + ("t" * c["TOPICAL"]) + ("." * c["NO-TRACE"])
            print(f"   {pi}. {ph[:44]:46} {bar}")
    print("\n  legend: R restated   t topical   . no trace")

    for tier in ("NO-TRACE", "TOPICAL"):
        print("\n" + "=" * 78)
        print(f"{tier} TECHNIQUES")
        print("=" * 78)
        for r in sorted([x for x in results if x["tier"] == tier],
                        key=lambda x: (x["playbook"], x["phase"], x["idx"])):
            print(f"\n[{r['playbook']} / {r['phase']} #{r['idx']}]  "
                  f"({r['words']}w, sig={r['sig']}, cov={r['cov']:.0%})")
            print(f"  {r['text'][:400]}")

    # --- Rule 1 evidence: near-duplicate techniques ------------------------
    # "Every new rule replaces one, or it does not go in." Pairs with high content
    # overlap are the additions that were restatements of a rule already present.
    # Only ONE playbook is loaded per phase, so a technique cloned across playbooks
    # costs no prompt tokens at runtime - it is a maintenance smell, not bloat.
    # Within-playbook duplication is the kind that competes for attention.
    print("\n" + "=" * 78)
    print("WITHIN-PLAYBOOK NEAR-DUPLICATES (Jaccard >= 0.20) - Rule 1 targets")
    print("=" * 78)
    def content(t):
        return {w for w in words_of(t["text"]) if w not in STOP and len(w) > 3}
    by_key = {(r["playbook"], r["phase"], r["idx"]): r for r in results}
    dupes, cross = [], 0
    for i in range(len(techniques)):
        ci = content(techniques[i])
        if len(ci) < 5:
            continue
        for j in range(i + 1, len(techniques)):
            cj = content(techniques[j])
            if len(cj) < 5:
                continue
            jac = len(ci & cj) / len(ci | cj)
            if jac < 0.20:
                continue
            if techniques[i]["playbook"] != techniques[j]["playbook"]:
                cross += 1
            else:
                dupes.append((jac, techniques[i], techniques[j]))
    dupes.sort(key=lambda x: -x[0])
    print(f"{len(dupes)} within-playbook pairs "
          f"({cross} cross-playbook pairs excluded as runtime-free)\n")
    for jac, a, b in dupes:
        ra = by_key[(a["playbook"], a["phase"], a["idx"])]
        rb = by_key[(b["playbook"], b["phase"], b["idx"])]
        print(f"  {jac:.2f}  {a['playbook']}")
        print(f"      [{ra['tier']:8}] {a['phase']}#{a['idx']}: {a['text'][:170]}")
        print(f"      [{rb['tier']:8}] {b['phase']}#{b['idx']}: {b['text'][:170]}")

    print("\n" + "=" * 78)
    print("STRONGEST DELETE CANDIDATES")
    print("  NO-TRACE *and* a within-playbook near-duplicate of a technique that")
    print("  DID leave a trace - the rule survives the deletion, the tokens do not.")
    print("=" * 78)
    strong = []
    for jac, a, b in dupes:
        ra = by_key[(a["playbook"], a["phase"], a["idx"])]
        rb = by_key[(b["playbook"], b["phase"], b["idx"])]
        for dead, live in ((ra, rb), (rb, ra)):
            if dead["tier"] == "NO-TRACE" and live["tier"] != "NO-TRACE":
                strong.append((jac, dead, live))
    seen = set()
    for jac, dead, live in sorted(strong, key=lambda x: -x[0]):
        k = (dead["playbook"], dead["phase"], dead["idx"])
        if k in seen:
            continue
        seen.add(k)
        print(f"\n  DROP  {dead['playbook']}/{dead['phase']}#{dead['idx']}  "
              f"({dead['words']}w, jaccard {jac:.2f})")
        print(f"        {dead['text'][:220]}")
        print(f"  KEEP  {live['playbook']}/{live['phase']}#{live['idx']} [{live['tier']}]")
        print(f"        {live['text'][:220]}")
    print(f"\n  -> {len(seen)} techniques deletable on this combined test")

    print("\n" + "=" * 78)
    print("CALIBRATION - rules known to have changed behaviour must NOT read NO-TRACE")
    print("=" * 78)
    for probe in ("STOP AND JOIN THEM", "wide encoding", "provider",
                  "WITHOUT the credential", "control test", "notes"):
        hit = [r for r in results if probe.lower() in r["text"].lower()]
        if not hit:
            print(f"  {probe!r:26} -> (no technique contains this text)")
        for h in hit[:3]:
            print(f"  {probe!r:26} -> {h['tier']:9} n={h['n']} runs={h['runs']} "
                  f"[{h['playbook']}/{h['phase']}#{h['idx']}]")


if __name__ == "__main__":
    main()
