from __future__ import annotations
import argparse
import json
import math
import random
from pathlib import Path

TAU = 2.0 * math.pi

def wrap_pi(x: float) -> float:
    # wrap to (-pi, pi]
    y = (x + math.pi) % TAU - math.pi
    # optional: map -pi to +pi for consistency
    return math.pi if y == -math.pi else y

def compute_S(theta_n_tang: float, theta_p_tang: float, theta_q_tang: float) -> tuple[float, float, float]:
    dp = abs(wrap_pi(theta_n_tang - theta_p_tang))
    dq = abs(wrap_pi(theta_n_tang - theta_q_tang))
    return dp + dq, dp, dq

def quantile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    xs_sorted = sorted(xs)
    idx = int(round((len(xs_sorted) - 1) * q))
    return xs_sorted[max(0, min(idx, len(xs_sorted) - 1))]

def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")

def std(xs: list[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(v)

def corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return float("nan")
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)

def load_angles(jsonl_path: Path, max_rows: int = 0) -> tuple[list[float], list[float], list[float]]:
    tn, tp, tq = [], [], []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_rows and i >= max_rows:
                break
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            # tolerate alternative key names if needed
            tn.append(float(obj["theta_n_tang"]))
            tp.append(float(obj["theta_p_tang"]))
            tq.append(float(obj["theta_q_tang"]))
    return tn, tp, tq

def summarize(name: str, S: list[float], dp: list[float], dq: list[float]) -> dict:
    e = [s - math.pi for s in S]
    out = {
        "name": name,
        "N": len(S),
        "mean_S": mean(S),
        "std_S": std(S),
        "q05_S": quantile(S, 0.05),
        "q50_S": quantile(S, 0.50),
        "q95_S": quantile(S, 0.95),
        "mean_abs_err_S_minus_pi": mean([abs(x) for x in e]),
        "mean_dp": mean(dp),
        "mean_dq": mean(dq),
        "corr_dp_dq": corr(dp, dq),
    }
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input pendulum_triplets JSONL path")
    ap.add_argument("--tag", default="", help="label for this dataset in output")
    ap.add_argument("--max_rows", type=int, default=0, help="optional cap for quick tests (0 = all)")
    ap.add_argument("--permute", action="store_true", help="also run permutation null model")
    ap.add_argument("--perm_seed", type=int, default=0, help="seed for permutation")
    ap.add_argument("--out_json", default="", help="optional output JSON path")
    args = ap.parse_args()

    inp = Path(args.inp)
    tag = args.tag or inp.stem

    tn, tp, tq = load_angles(inp, max_rows=args.max_rows)

    S, dp, dq = [], [], []
    for a, b, c in zip(tn, tp, tq):
        s, dpp, dqq = compute_S(a, b, c)
        S.append(s); dp.append(dpp); dq.append(dqq)

    res = {"dataset": summarize(tag, S, dp, dq)}

    if args.permute:
        rng = random.Random(args.perm_seed)
        idx = list(range(len(tp)))
        rng.shuffle(idx)
        tp_perm = [tp[i] for i in idx]
        tq_perm = [tq[i] for i in idx]

        S2, dp2, dq2 = [], [], []
        for a, b, c in zip(tn, tp_perm, tq_perm):
            s, dpp, dqq = compute_S(a, b, c)
            S2.append(s); dp2.append(dpp); dq2.append(dqq)

        res["permutation"] = summarize(f"{tag}__perm_seed{args.perm_seed}", S2, dp2, dq2)

    text = json.dumps(res, indent=2, sort_keys=True)
    print(text)

    if args.out_json:
        Path(args.out_json).write_text(text, encoding="utf-8")

if __name__ == "__main__":
    main()
