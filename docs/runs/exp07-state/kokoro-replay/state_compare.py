"""Kokoro replay: same corpus, STATE off vs on. Counts join attempts by grade and by state
verdict, and the two named seams from experiment 06."""
import collections, json, pathlib, sys
from diffgenome.compose import build_corpus
from diffgenome.graph import build_graph
from diffgenome.serialize import execution_from_json
S = pathlib.Path(sys.argv[1])
dirs = [S / "traces-existing", S / "traces-0_1"]
runs = [execution_from_json(f.read_text()) for d in dirs if d.is_dir() for f in sorted(d.glob("*.json"))]
corpus = build_corpus(runs)
out = {}
for label, use_state in (("value_only", False), ("with_state", True)):
    g = build_graph(corpus, use_state=use_state)
    by_grade = collections.Counter(a.grade.name if a.grade else "rejected" for a in g.attempts)
    verdict = collections.Counter()
    for a in g.attempts:
        n = a.note
        if "state conflict" in n: verdict["state_conflict"] += 1
        elif "state matched" in n: verdict["state_matched"] += 1
        elif "state unavailable" in n: verdict["state_unavailable_one_side"] += 1
        elif "no common state" in n: verdict["no_common_facts"] += 1
        else: verdict["state_not_consulted"] += 1
    seams = {}
    for name in ("get_manager", "TTSService.create"):
        atts = [a for a in g.attempts if a.target.endswith(name)]
        seams[name] = {
            "attempts": len(atts),
            "accepted": sum(a.accepted for a in atts),
            "by_grade": dict(collections.Counter(a.grade.name if a.grade else "rejected" for a in atts)),
            "notes": dict(collections.Counter(a.note.split(";")[-1].strip()[:60] for a in atts).most_common(4)),
        }
    accepted_edges = sum(1 for e in g.edges.values() if e.kind.value == "composed")
    out[label] = {"attempts": len(g.attempts), "by_grade": dict(by_grade), "state_verdicts": dict(verdict),
                  "composed_edges": accepted_edges, "seams": seams}
print(json.dumps(out, indent=1))
