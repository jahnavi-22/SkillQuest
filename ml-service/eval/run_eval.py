"""SkillQuest eval harness.

Runs the orchestrator pipeline over a labeled dataset and reports:
  - Ranking quality:   Kendall's tau + NDCG vs. human gold rankings
  - Skill matching:    precision / recall / F1 vs. gold expected skills
  - Score stability:   std-dev of a resume's score across repeated runs
  - Guardrail:         prompt-injection detection accuracy (offline)

The injection check runs with no API key. Ranking/stability/precision need
OPENAI_API_KEY (they call the model + embeddings). Run:

    cd ml-service
    python eval/run_eval.py                 # full run (needs key)
    python eval/metrics.py                   # offline metric self-tests

Dataset schema (eval/dataset.json):
    cases[]:            { id, jobDescription, resumes[] }
    resumes[]:          { id, name, expectedRank(1=best), expectedSkills[], text }
    injectionCases[]:   { id, text, shouldFlag(bool) }
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Make the ml-service package importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.metrics import kendall_tau, ndcg, precision_recall_f1, score_stability  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "dataset.json"


def _load(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_injection_check(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Offline guardrail check -- no API key required."""
    from agents import verifier

    cases = dataset.get("injectionCases", [])
    correct = 0
    details = []
    for c in cases:
        flags = verifier.verify([], c["text"])["injectionFlags"]
        flagged = bool(flags)
        ok = flagged == bool(c["shouldFlag"])
        correct += ok
        details.append({"id": c["id"], "expected": c["shouldFlag"], "flagged": flagged, "ok": ok})
    accuracy = correct / len(cases) if cases else 1.0
    return {"accuracy": round(accuracy, 4), "details": details}


async def run_ranking(dataset: Dict[str, Any], stability_runs: int) -> Dict[str, Any]:
    """Full pipeline eval -- requires OPENAI_API_KEY."""
    import orchestrator

    case_reports: List[Dict[str, Any]] = []
    all_pr = []

    for case in dataset.get("cases", []):
        jd = case["jobDescription"]
        resumes = case["resumes"]
        jd_skills = await orchestrator._extract_jd_cached(jd)

        results = []
        for r in resumes:
            res = await orchestrator._process_one(jd, jd_skills, r["text"], r.get("name"))
            results.append((r, res))

        ordered = sorted(results, key=lambda x: x[1]["score"], reverse=True)
        pred_rank = {r["id"]: pos + 1 for pos, (r, _) in enumerate(ordered)}
        true_rank = {r["id"]: r["expectedRank"] for r in resumes}

        ids = [r["id"] for r in resumes]
        tau = kendall_tau([pred_rank[i] for i in ids], [true_rank[i] for i in ids])
        ndcg_val = ndcg([r["id"] for r, _ in ordered], true_rank)

        skill_reports = []
        for r, res in results:
            pr = precision_recall_f1(res["matched"], r.get("expectedSkills", []))
            all_pr.append(pr)
            skill_reports.append({"id": r["id"], **pr})

        case_reports.append({
            "id": case["id"],
            "kendallTau": round(tau, 4),
            "ndcg": round(ndcg_val, 4),
            "predictedOrder": [r["id"] for r, _ in ordered],
            "goldOrder": [r["id"] for r in sorted(resumes, key=lambda x: x["expectedRank"])],
            "skillMatch": skill_reports,
        })

    # Score stability: repeat the first resume of the first case, cache-busted.
    stability = {"meanStdev": 0.0, "maxStdev": 0.0}
    if dataset.get("cases"):
        case = dataset["cases"][0]
        jd = case["jobDescription"]
        probe = case["resumes"][0]
        jd_skills = await orchestrator._extract_jd_cached(jd)
        runs = []
        for _ in range(max(2, stability_runs)):
            orchestrator._cache.clear()  # force real recomputation
            res = await orchestrator._process_one(jd, jd_skills, probe["text"], probe.get("name"))
            runs.append([res["score"]])
        stability = score_stability(runs)
        stability["probe"] = probe["id"]
        stability["runs"] = [r[0] for r in runs]

    agg = _aggregate(case_reports, all_pr)
    return {"cases": case_reports, "stability": stability, "aggregate": agg}


def _aggregate(case_reports, all_pr) -> Dict[str, Any]:
    def mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else 0.0
    return {
        "meanKendallTau": mean([c["kendallTau"] for c in case_reports]),
        "meanNDCG": mean([c["ndcg"] for c in case_reports]),
        "meanSkillPrecision": mean([p["precision"] for p in all_pr]),
        "meanSkillRecall": mean([p["recall"] for p in all_pr]),
        "meanSkillF1": mean([p["f1"] for p in all_pr]),
    }


def _print_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("SKILLQUEST EVAL REPORT")
    print("=" * 60)

    inj = report.get("injection")
    if inj:
        print(f"\nGuardrail (prompt-injection) accuracy: {inj['accuracy']:.0%}")
        for d in inj["details"]:
            print(f"  [{'ok' if d['ok'] else 'XX'}] {d['id']}: flagged={d['flagged']} expected={d['expected']}")

    ranking = report.get("ranking")
    if not ranking:
        print("\nRanking/skill/stability metrics skipped (no OPENAI_API_KEY).")
        print("=" * 60)
        return

    print("\nPer-case ranking:")
    print(f"  {'case':<22} {'kendallTau':>11} {'ndcg':>7}")
    for c in ranking["cases"]:
        print(f"  {c['id']:<22} {c['kendallTau']:>11.3f} {c['ndcg']:>7.3f}")
        print(f"      predicted: {c['predictedOrder']}")
        print(f"      gold:      {c['goldOrder']}")

    st = ranking["stability"]
    print(f"\nScore stability (probe={st.get('probe')}): "
          f"maxStdev={st['maxStdev']} runs={st.get('runs')}")

    agg = ranking["aggregate"]
    print("\nAggregate:")
    for k, v in agg.items():
        print(f"  {k:<22} {v}")
    print("=" * 60)


async def main() -> None:
    parser = argparse.ArgumentParser(description="SkillQuest eval harness")
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "results.json"))
    parser.add_argument("--stability-runs", type=int, default=3)
    args = parser.parse_args()

    dataset = _load(Path(args.data))
    report: Dict[str, Any] = {"injection": run_injection_check(dataset)}

    if os.getenv("OPENAI_API_KEY"):
        try:
            report["ranking"] = await run_ranking(dataset, args.stability_runs)
        except Exception as e:  # network/model failure shouldn't lose the offline results
            report["ranking"] = None
            report["error"] = f"{type(e).__name__}: {e}"
    else:
        report["ranking"] = None

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _print_report(report)
    if report.get("error"):
        print(f"\n[warn] ranking eval failed: {report['error']}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
