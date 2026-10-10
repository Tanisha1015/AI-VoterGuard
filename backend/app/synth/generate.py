"""Synthetic voter-roll generator for the fictional constituency "Demo Nagar (Synthetic)".

Usage (from backend/):
    python -m app.synth.generate --out data/synthetic --seed 42

Writes draft_roll.csv, final_roll.csv, asdd.csv, truth.json and demo_voters.json. All values come
from one seeded numpy generator, so the same seed always yields byte-identical files. The data is
entirely fictional: EPIC numbers start with VGX and no real person or place is represented.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

from app.synth import plant
from app.synth.names import AC_NO, COLUMNS, SURNAMES, Row, draw_ages, make_people

AC_NAME = "Demo Nagar (Synthetic)"
N_BOOTHS = 60
MIN_VOTERS, MAX_VOTERS = 700, 900
DEAD_AGE_WEIGHT = 50.0  # DEAD removals strongly favour ages 60+
DEAD_MIN_AGE = 31  # normal booths record no DEAD removals at ages 18-30 (P5 plants those)

REMARKS = {
    "ABSENT": "Not found at address during visit",
    "SHIFTED": "Reported moved to another address",
    "DEAD": "Death reported by household",
    "DUPLICATE": "Matches another entry",
}


def epic_stream(rng: np.random.Generator) -> Iterator[str]:
    """Yield unique synthetic EPIC numbers: "VGX" followed by 7 digits."""
    values = rng.choice(9_000_000, size=80_000, replace=False) + 1_000_000
    return (f"VGX{int(v):07d}" for v in values)


def house_no(rng: np.random.Generator) -> str:
    """Return a house number such as "12", "12-B" or "7/3"."""
    base, u = int(rng.integers(1, 400)), float(rng.random())
    if u < 0.70:
        return str(base)
    if u < 0.85:
        return f"{base}-{chr(65 + int(rng.integers(0, 5)))}"
    return f"{base}/{int(rng.integers(1, 10))}"


def make_households(rng: np.random.Generator, n: int) -> tuple[list[str], list[str]]:
    """Return per-voter house numbers and household surnames for ``n`` voters (1-6 per household)."""
    houses: list[str] = []
    surnames: list[str] = []
    used: set[str] = set()
    while len(houses) < n:
        size = int(rng.choice(6, p=[0.10, 0.20, 0.25, 0.25, 0.15, 0.05])) + 1
        house = house_no(rng)
        if house in used:
            continue
        used.add(house)
        surname = SURNAMES[int(rng.integers(0, len(SURNAMES)))]
        houses += [house] * size
        surnames += [surname] * size
    return houses[:n], surnames[:n]


def build_draft(part_no: int, rng: np.random.Generator, epics: Iterator[str]) -> plant.Booth:
    """Build one booth's draft roll (700-900 voters) with a booth-specific gender mix."""
    n = int(rng.integers(MIN_VOTERS, MAX_VOTERS + 1))
    female_share = float(rng.uniform(0.46, 0.50))
    houses, surnames = make_households(rng, n)
    rows = make_people(rng, epics, part_no, draw_ages(rng, n), female_share, houses, surnames)
    for serial, row in enumerate(rows, start=1):
        row["serial_no"] = serial
    return plant.Booth(part_no=part_no, female_share=female_share, draft=rows)


def _counts(mix: dict[str, float], total: int) -> dict[str, int]:
    """Split ``total`` across reasons by largest-remainder rounding (sums exactly to ``total``)."""
    raw = {r: mix[r] * total for r in plant.REASONS}
    out = {r: int(v) for r, v in raw.items()}
    leftover = total - sum(out.values())
    for r in sorted(plant.REASONS, key=lambda x: raw[x] - out[x], reverse=True)[:leftover]:
        out[r] += 1
    return out


def _dead_weight(age: int) -> float:
    """Relative chance that a voter of this age is a DEAD removal in a normal booth."""
    if age >= 60:
        return DEAD_AGE_WEIGHT
    return 1.0 if age >= DEAD_MIN_AGE else 0.0


def choose_removals(booth: plant.Booth, rng: np.random.Generator) -> None:
    """Pick removed voters for a booth and assign a reason to each (fills ``booth.removed``)."""
    plan = plant.plan_for(booth.part_no, rng)
    n = len(booth.draft)
    k = round(plan.rate * n)
    if plan.female_share is None:
        chosen = [int(i) for i in rng.choice(n, size=k, replace=False)]
    else:
        female = [i for i, r in enumerate(booth.draft) if r["gender"] == "F"]
        other = [i for i, r in enumerate(booth.draft) if r["gender"] != "F"]
        k_f = round(plan.female_share * k)
        chosen = [int(i) for i in rng.choice(female, size=k_f, replace=False)]
        chosen += [int(i) for i in rng.choice(other, size=k - k_f, replace=False)]
    counts = _counts(plan.reason_mix, k)
    weights = np.array([_dead_weight(booth.draft[i]["age"]) for i in chosen])
    dead = {chosen[int(j)] for j in rng.choice(k, size=counts["DEAD"], replace=False, p=weights / weights.sum())}
    rest = [chosen[int(j)] for j in rng.permutation(k) if chosen[int(j)] not in dead]
    for i in dead:
        booth.removed[i] = "DEAD"
    start = 0
    for reason in ("ABSENT", "SHIFTED", "DUPLICATE"):
        for i in rest[start:start + counts[reason]]:
            booth.removed[i] = reason
        start += counts[reason]


def add_normal_voters(booth: plant.Booth, rng: np.random.Generator, epics: Iterator[str]) -> None:
    """Add 1-3% new voters (age 18-25 skew) that appear only in the final roll."""
    n_add = round(float(rng.uniform(0.01, 0.03)) * len(booth.draft))
    houses: list[str] = []
    surnames: list[str] = []
    for pick in rng.integers(0, len(booth.draft), n_add):
        if float(rng.random()) < 0.7:  # join an existing household
            base = booth.draft[int(pick)]
            houses.append(base["house_no"])
            surnames.append(base["relative_name"].split(" ")[-1])
        else:
            houses.append(house_no(rng))
            surnames.append(SURNAMES[int(rng.integers(0, len(SURNAMES)))])
    booth.additions.extend(make_people(rng, epics, booth.part_no, draw_ages(rng, n_add, young=True),
                                       booth.female_share, houses, surnames))


def set_demo_voters(booth: plant.Booth) -> dict[str, Row]:
    """Rewrite three real rows of booth 17 so the demo has known REMOVED / PRESENT / ADDED voters.

    Must run after removals and additions exist and before the final roll is built.
    """
    removed_row = next(booth.draft[i] for i in sorted(booth.removed)
                       if booth.removed[i] == "SHIFTED" and booth.draft[i]["gender"] == "F")
    removed_row.update(name="Sunita Devi", relative_name="Ramesh Kumar", relation_type="HUSBAND", age=34, gender="F")
    present_row = next(r for i, r in enumerate(booth.draft) if i not in booth.removed and r["gender"] == "F")
    present_row.update(name="Meena Kumari", relative_name="Hari Kumar", relation_type="FATHER", age=40, gender="F")
    added_row = booth.additions[0]
    added_row.update(name="Ananya Singh", relative_name="Mohan Singh", relation_type="FATHER", age=22, gender="F")
    return {"removed": removed_row, "present": present_row, "added": added_row}


def finalize_booth(booth: plant.Booth) -> None:
    """Build the final roll: surviving draft voters first, then additions, renumbered from 1."""
    survivors = [dict(r) for i, r in enumerate(booth.draft) if i not in booth.removed]
    booth.final = survivors + booth.additions
    for serial, row in enumerate(booth.final, start=1):
        row["serial_no"] = serial


def build_rolls(seed: int) -> tuple[dict[int, plant.Booth], dict[str, Any], dict[str, Any]]:
    """Build every booth with all planted anomalies. Returns (booths, truth, demo_voters)."""
    rng = np.random.default_rng(seed)
    epics = epic_stream(rng)
    booths = {p: build_draft(p, rng, epics) for p in range(1, N_BOOTHS + 1)}
    for booth in booths.values():
        choose_removals(booth, rng)
    p5 = plant.plant_p5(booths[plant.P5_BOOTH], rng)
    for booth in booths.values():
        add_normal_voters(booth, rng, epics)
    plant.sanitize_houses(booths[plant.P3_BOOTH])
    p3 = plant.plant_p3(booths[plant.P3_BOOTH], rng, epics, SURNAMES)
    p4 = plant.plant_p4(booths, rng, epics)
    demo = set_demo_voters(booths[plant.P1_BOOTH])
    p1 = plant.removal_truth(
        booths[plant.P1_BOOTH], "P1",
        "Unusual removal pattern: about 22% of the booth's draft voters were removed, mostly with reason SHIFTED, "
        "and most of those removed are female; worth verifying with a field check.")
    p2 = plant.removal_truth(
        booths[plant.P2_BOOTH], "P2",
        "Unusual removal pattern: about 14% of the booth's draft voters were removed, almost all with reason "
        "ABSENT; worth verifying with a field check.")
    for booth in booths.values():
        finalize_booth(booth)
    p6 = plant.plant_p6(booths, rng)
    truth = {"ac_no": AC_NO, "ac_name": AC_NAME, "seed": seed, "anomalies": [p1, p2, p3, p4, p5, p6]}
    demo_json = {key: {**row, "status": status} for (key, row), status in
                 zip(demo.items(), ("REMOVED", "PRESENT", "ADDED"))}
    demo_json["removed"]["reason"] = "SHIFTED"
    return booths, truth, demo_json


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Write a CSV with Unix line endings so output bytes are identical on every platform."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    """Write stable, human-readable JSON (sorted keys, trailing newline)."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_outputs(out: Path, booths: dict[int, plant.Booth], truth: dict[str, Any],
                  demo: dict[str, Any], seed: int) -> None:
    """Write draft_roll.csv, final_roll.csv, asdd.csv, truth.json and demo_voters.json to ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    ordered = [booths[p] for p in sorted(booths)]
    write_csv(out / "draft_roll.csv", COLUMNS, [[r[c] for c in COLUMNS] for b in ordered for r in b.draft])
    write_csv(out / "final_roll.csv", COLUMNS, [[r[c] for c in COLUMNS] for b in ordered for r in b.final])
    remark_rng = np.random.default_rng(seed + 1)
    asdd: list[list[Any]] = []
    for booth in ordered:
        for idx in sorted(booth.removed):
            if idx in booth.missing_asdd:
                continue
            reason = booth.removed[idx]
            remark = REMARKS[reason] if remark_rng.random() < 0.5 else ""
            asdd.append([booth.draft[idx]["epic_no"], booth.part_no, reason, remark])
    write_csv(out / "asdd.csv", ["epic_no", "part_no", "reason", "remark"], asdd)
    write_json(out / "truth.json", truth)
    write_json(out / "demo_voters.json", demo)


def generate(out: Path, seed: int) -> None:
    """Generate all five synthetic files into ``out`` for the given seed."""
    booths, truth, demo = build_rolls(seed)
    write_outputs(out, booths, truth, demo, seed)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: python -m app.synth.generate --out data/synthetic --seed 42."""
    parser = argparse.ArgumentParser(description="Generate the synthetic Demo Nagar voter rolls.")
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"), help="output directory")
    parser.add_argument("--seed", type=int, default=42, help="random seed (same seed => identical files)")
    args = parser.parse_args(argv)
    generate(args.out, args.seed)
    print(f"Wrote synthetic rolls to {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()

