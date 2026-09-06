"""Pure-python evaluation metrics (no scipy/numpy dependency).

Kept dependency-free and side-effect-free so the metric math can be unit-tested
offline, without an API key or network. Run this file directly to self-test.
"""

import math
from statistics import pstdev
from typing import Dict, List, Sequence


def kendall_tau(rank_a: Sequence[float], rank_b: Sequence[float]) -> float:
    """Kendall rank correlation (tau-a) between two aligned rank sequences.

    Values in +1 (identical order) .. -1 (reversed). Inputs are ranks for the
    same items in the same order. Ties contribute 0 to the numerator.
    """
    n = len(rank_a)
    if n < 2 or n != len(rank_b):
        return 0.0
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (rank_a[i] - rank_a[j]) * (rank_b[i] - rank_b[j])
            if s > 0:
                concordant += 1
            elif s < 0:
                discordant += 1
    denom = n * (n - 1) / 2
    return (concordant - discordant) / denom if denom else 0.0


def ndcg(predicted_order: List[str], true_rank: Dict[str, int]) -> float:
    """NDCG of a predicted ordering against gold ranks (1 = best).

    Relevance is derived from the gold rank: the best item gets the highest
    gain. Returns 0..1 (1 = predicted order matches the ideal order).
    """
    items = [it for it in predicted_order if it in true_rank]
    n = len(items)
    if n == 0:
        return 0.0
    rel = {it: (n - true_rank[it] + 1) for it in items}  # rank 1 -> gain n

    def dcg(order: List[str]) -> float:
        return sum(rel[it] / math.log2(idx + 2) for idx, it in enumerate(order))

    ideal_order = sorted(items, key=lambda it: true_rank[it])
    idcg = dcg(ideal_order)
    return dcg(items) / idcg if idcg else 0.0


def precision_recall_f1(predicted: Sequence[str], gold: Sequence[str]) -> Dict[str, float]:
    """Set-based precision / recall / F1 (case-insensitive)."""
    pred = {p.strip().lower() for p in predicted if p and p.strip()}
    gold_set = {g.strip().lower() for g in gold if g and g.strip()}
    if not pred and not gold_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    inter = len(pred & gold_set)
    precision = inter / len(pred) if pred else 0.0
    recall = inter / len(gold_set) if gold_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def score_stability(score_runs: List[List[float]]) -> Dict[str, float]:
    """Given per-item scores across N runs, report score variability.

    score_runs[k] is the list of item scores from run k (same item order each
    run). Returns the mean and max population std-dev across items. Low = stable.
    """
    if not score_runs or len(score_runs) < 2:
        return {"meanStdev": 0.0, "maxStdev": 0.0}
    n_items = len(score_runs[0])
    stdevs: List[float] = []
    for i in range(n_items):
        per_item = [run[i] for run in score_runs if i < len(run)]
        stdevs.append(pstdev(per_item) if len(per_item) > 1 else 0.0)
    mean_sd = sum(stdevs) / len(stdevs) if stdevs else 0.0
    return {"meanStdev": round(mean_sd, 4), "maxStdev": round(max(stdevs), 4) if stdevs else 0.0}


if __name__ == "__main__":
    # Offline self-tests (no API needed).
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1.0
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1.0
    assert abs(ndcg(["a", "b", "c"], {"a": 1, "b": 2, "c": 3}) - 1.0) < 1e-9
    assert ndcg(["c", "b", "a"], {"a": 1, "b": 2, "c": 3}) < 1.0
    pr = precision_recall_f1(["Java", "React"], ["java", "python"])
    assert pr["precision"] == 0.5 and pr["recall"] == 0.5
    st = score_stability([[80.0, 60.0], [80.0, 60.0]])
    assert st["maxStdev"] == 0.0
    st2 = score_stability([[80.0], [70.0]])
    assert st2["maxStdev"] > 0.0
    print("metrics self-test: PASS")
