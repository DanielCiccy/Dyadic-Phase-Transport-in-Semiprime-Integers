from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import gmpy2
from gmpy2 import mpz

# -----------------------------
# Constants / helpers
# -----------------------------
def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def build_out_path(out_dir: Path, prefix: str, bits_n: int, prime_bits: int, n_rows: int, seed: int, ext: str) -> Path:
    ts = now_tag()
    return out_dir / f"{prefix}__BN{bits_n}__p{prime_bits}__N{n_rows}__seed{seed}__{ts}.{ext}"


def rand_odd_bits(rng: random.Random, bits: int, msb_mode: str = "top1") -> mpz:
    """
    Random odd integer with exact bit-length.
    msb_mode:
      - top1: force MSB only (classic)
      - top2: force MSB and 2nd MSB (push into upper quarter)
             This strongly reduces (often eliminates) bits_n carry-down for balanced products.
    """
    x = rng.getrandbits(bits)
    x |= (1 << (bits - 1))  # force top bit
    if msb_mode == "top2":
        x |= (1 << (bits - 2))  # force second top bit
    x |= 1  # odd
    return mpz(x)


def rand_prime_bits(rng: random.Random, bits: int, msb_mode: str = "top1") -> mpz:
    """Random prime with exact bit-length (via next_prime), loop (no recursion)."""
    while True:
        x = rand_odd_bits(rng, bits, msb_mode=msb_mode)
        p = gmpy2.next_prime(x)
        if p.bit_length() == bits:
            return mpz(p)


def bitlen(x: mpz) -> int:
    return int(x.bit_length())


def k_of(x: mpz) -> int:
    return bitlen(x) - 1


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate balanced high-bit semiprimes in streaming CSV (and optional JSONL)."
    )
    ap.add_argument("--out_dir", default="phase_transport/data/raw", help="Output directory")
    ap.add_argument("--n_rows", type=int, required=True, help="Number of semiprimes")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")

    ap.add_argument("--target_bits_n", type=int, required=True,
                    help="Target bit-length of n (e.g. 1024, 2048). Must be even for balanced p,q.")
    ap.add_argument("--prime_bits", type=int, default=0,
                    help="Optional override for prime bit-length. Default = target_bits_n//2.")

    ap.add_argument("--msb_mode", default="top2", choices=["top1", "top2"],
                    help="How to place p,q in their bit-range. top2 recommended for large tiers.")
    ap.add_argument("--ensure_bits_n", action="store_true",
                    help="Reject samples whose bits_n != target_bits_n (safety filter).")
    ap.add_argument("--write_jsonl", action="store_true",
                    help="Also write a JSONL stream with the same core fields (no angles).")

    ap.add_argument("--flush_every", type=int, default=10000, help="Flush outputs every N rows")
    ap.add_argument("--progress_every", type=int, default=10000, help="Print progress every N rows")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    bits_n = int(args.target_bits_n)
    if bits_n % 2 != 0:
        raise ValueError("--target_bits_n must be even for balanced generation (p_bits = n_bits//2).")

    p_bits = int(args.prime_bits) if int(args.prime_bits) > 0 else (bits_n // 2)
    if 2 * p_bits != bits_n:
        # allow non-perfect balance, but warn in filename + meta
        pass

    rng = random.Random(args.seed)

    out_csv = build_out_path(out_dir, "semiprimes_balanced_high", bits_n, p_bits, args.n_rows, args.seed, "csv")
    out_jsonl: Optional[Path] = None
    jf = None

    if args.write_jsonl:
        out_jsonl = build_out_path(out_dir, "semiprimes_balanced_high", bits_n, p_bits, args.n_rows, args.seed, "jsonl")

    # Streaming writers
    with out_csv.open("w", newline="", encoding="utf-8") as cf:
        cw = csv.writer(cf)
        cw.writerow([
            "n_hex", "p_hex", "q_hex",
            "bits_n", "bits_p", "bits_q",
            "k_n", "k_p", "k_q",
            "p_is_min",
            "msb_mode",
            "target_bits_n",
        ])

        if out_jsonl is not None:
            jf = out_jsonl.open("w", encoding="utf-8")

        count = 0
        rejects_bits = 0
        rejects_equal = 0

        while count < args.n_rows:
            p = rand_prime_bits(rng, p_bits, msb_mode=args.msb_mode)
            q = rand_prime_bits(rng, p_bits, msb_mode=args.msb_mode)
            if p == q:
                rejects_equal += 1
                continue

            # canonical ordering
            p_is_min = 1 if p < q else 0
            pmin = p if p_is_min else q
            qmax = q if p_is_min else p

            n = pmin * qmax

            bn = bitlen(n)
            if args.ensure_bits_n and bn != bits_n:
                rejects_bits += 1
                continue

            bp = bitlen(pmin)
            bq = bitlen(qmax)

            row = [
                hex(int(n)),
                hex(int(pmin)),
                hex(int(qmax)),
                bn, bp, bq,
                bn - 1, bp - 1, bq - 1,
                p_is_min,
                args.msb_mode,
                bits_n,
            ]
            cw.writerow(row)

            if jf is not None:
                obj = {
                    "n_hex": row[0],
                    "p_hex": row[1],
                    "q_hex": row[2],
                    "bits_n": bn,
                    "bits_p": bp,
                    "bits_q": bq,
                    "k_n": bn - 1,
                    "k_p": bp - 1,
                    "k_q": bq - 1,
                    "p_is_min": int(p_is_min),
                    "msb_mode": args.msb_mode,
                    "target_bits_n": bits_n,
                    "seed": int(args.seed),
                }
                jf.write(json.dumps(obj) + "\n")

            count += 1

            if args.flush_every > 0 and (count % args.flush_every == 0):
                cf.flush()
                if jf is not None:
                    jf.flush()

            if args.progress_every > 0 and (count % args.progress_every == 0):
                print(f"[PROGRESS] {count}/{args.n_rows} rows | rejects_equal={rejects_equal} rejects_bits={rejects_bits}")

        if jf is not None:
            jf.flush()
            jf.close()

    print(f"[DONE] wrote CSV : {out_csv}")
    if out_jsonl is not None:
        print(f"[DONE] wrote JSONL: {out_jsonl}")


if __name__ == "__main__":
    main()
