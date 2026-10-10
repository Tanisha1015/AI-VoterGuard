"""Fictional names, spelling variants and person-row builders for the synthetic roll.

All names are written in Latin script and are drawn uniformly at random, independently of
booth, gender mix, age or any planted anomaly. The lists are a broad mix of common given names
and surnames and carry no meaning in this project. Nothing here (or anywhere downstream) infers
religion, caste or citizenship from a name. Only gender and age bands are ever analysed.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

import numpy as np

Row = dict[str, Any]

COLUMNS: list[str] = [
    "epic_no", "ac_no", "part_no", "serial_no", "name",
    "relative_name", "relation_type", "house_no", "age", "gender",
]

AC_NO = 999

MALE_FIRST: tuple[str, ...] = (
    "Ramesh", "Suresh", "Mahesh", "Rajesh", "Dinesh", "Mukesh", "Naresh", "Ganesh", "Anil", "Sunil",
    "Vijay", "Ajay", "Sanjay", "Manoj", "Vinod", "Pramod", "Ashok", "Deepak", "Rakesh", "Rohit",
    "Amit", "Sumit", "Nitin", "Pankaj", "Arun", "Varun", "Kiran", "Mohan", "Gopal", "Krishna",
    "Hari", "Shyam", "Ravi", "Prakash", "Subhash", "Sandeep", "Sachin", "Rahul", "Vivek", "Abhishek",
    "Anand", "Arvind", "Bharat", "Chetan", "Devendra", "Girish", "Harish", "Jagdish", "Jitendra",
    "Kamal", "Lalit", "Manish", "Narendra", "Satish", "Tarun", "Umesh", "Yogesh", "Vikram", "Vishal",
    "Pradeep", "Rajendra", "Surendra", "Mahendra", "Lokesh", "Naveen", "Pavan", "Raghav", "Sagar",
    "Tushar", "Uday", "Venkat", "Srinivas", "Imran", "Farhan", "Salim", "Irfan", "Javed", "Arif",
    "Joseph", "Thomas", "Daniel", "Samuel", "Gurpreet", "Harpreet", "Jaspreet",
)

FEMALE_FIRST: tuple[str, ...] = (
    "Sunita", "Anita", "Savita", "Kavita", "Mamta", "Meena", "Seema", "Reena", "Rekha", "Geeta",
    "Sita", "Radha", "Lakshmi", "Saraswati", "Parvati", "Durga", "Kamla", "Vimla", "Shanti", "Usha",
    "Asha", "Nisha", "Pooja", "Priya", "Neha", "Sneha", "Anjali", "Sapna", "Swati", "Rani",
    "Poonam", "Sarita", "Sangeeta", "Kiran", "Jyoti", "Manju", "Madhu", "Renu", "Babita", "Suman",
    "Sushila", "Shobha", "Lata", "Mala", "Nirmala", "Pushpa", "Kusum", "Champa", "Gauri", "Indira",
    "Padma", "Revathi", "Sunanda", "Divya", "Deepa", "Archana", "Bhavna", "Chitra", "Hema", "Jaya",
    "Komal", "Nandini", "Pallavi", "Rashmi", "Shweta", "Tanvi", "Vandana", "Yamini", "Ayesha",
    "Shabnam", "Nasreen", "Farida", "Rukhsar", "Mary", "Grace", "Jasleen", "Ananya", "Aarti",
)

SURNAMES: tuple[str, ...] = (
    "Kumar", "Singh", "Sharma", "Verma", "Gupta", "Yadav", "Mishra", "Pandey", "Tiwari", "Dubey",
    "Chauhan", "Thakur", "Joshi", "Bhatt", "Mehta", "Shah", "Patel", "Desai", "Trivedi", "Pillai",
    "Nair", "Menon", "Iyer", "Reddy", "Naidu", "Rao", "Das", "Bose", "Sen", "Ghosh",
    "Roy", "Dutta", "Mondal", "Biswas", "Sarkar", "Bora", "Gogoi", "Hazarika", "Patil", "Jadhav",
    "Pawar", "Shinde", "Kulkarni", "Deshmukh", "More", "Naik", "Shetty", "Kamath", "Hegde",
    "Gowda", "Khan", "Ansari", "Qureshi", "Sheikh", "Mirza", "Fernandes", "Mathew", "Joseph",
    "Gill", "Sandhu", "Arora", "Kapoor", "Malhotra", "Chopra", "Saini", "Jain", "Agarwal",
    "Bansal", "Goyal", "Mittal",
)

# Full names used by demo_voters.json; the random builder never produces them for other voters.
RESERVED_NAMES: frozenset[str] = frozenset({"Sunita Devi", "Meena Kumari", "Ananya Singh"})

# (low age, high age, probability) bands for the general and the new-voter distributions.
_GENERAL_BANDS = ((18, 25, 0.15), (26, 35, 0.22), (36, 45, 0.20), (46, 60, 0.23), (61, 80, 0.17), (81, 95, 0.03))
_YOUNG_BANDS = ((18, 25, 0.70), (26, 40, 0.30))

_O_SHARE = 0.002  # share of gender "O" (rare)

# Transliteration-style spelling swaps used to build near-copies.
_SWAPS: tuple[tuple[str, str], ...] = (
    ("ee", "i"), ("i", "ee"), ("oo", "u"), ("u", "oo"), ("sh", "s"), ("s", "sh"),
    ("v", "w"), ("w", "v"), ("aa", "a"), ("a", "aa"), ("th", "t"), ("t", "th"),
)


def draw_ages(rng: np.random.Generator, n: int, young: bool = False) -> np.ndarray:
    """Draw ``n`` integer ages (18-95) from the general or the new-voter distribution."""
    bands = _YOUNG_BANDS if young else _GENERAL_BANDS
    probs = np.array([b[2] for b in bands])
    which = rng.choice(len(bands), size=n, p=probs / probs.sum())
    lows = np.array([b[0] for b in bands])[which]
    highs = np.array([b[1] for b in bands])[which]
    return rng.integers(lows, highs + 1)


def spelling_variant(text: str, rng: np.random.Generator) -> str:
    """Return a close spelling variant of a Title-Case name; it always differs from ``text``."""
    tokens = text.split(" ")
    options: list[tuple[int, int, str, str]] = []
    for t_idx, token in enumerate(tokens):
        low = token.lower()
        for old, new in _SWAPS:
            pos = low.find(old)
            if pos > 0:  # never change the first letter
                options.append((t_idx, pos, old, new))
    if not options:
        tokens[0] = tokens[0] + "h"
        return " ".join(tokens)
    t_idx, pos, old, new = options[int(rng.integers(0, len(options)))]
    low = tokens[t_idx].lower()
    tokens[t_idx] = (low[:pos] + new + low[pos + len(old):]).capitalize()
    return " ".join(tokens)


def _relation(gender: str, age: int, u: float) -> str:
    """Pick relation_type for one voter from a uniform draw ``u`` in [0, 1)."""
    if gender == "F" and age >= 21:
        cuts = (("HUSBAND", 0.72), ("FATHER", 0.94), ("MOTHER", 0.97), ("OTHER", 1.01))
    elif gender == "M":
        cuts = (("FATHER", 0.92), ("MOTHER", 0.96), ("OTHER", 1.01))
    else:
        cuts = (("FATHER", 0.85), ("MOTHER", 0.95), ("OTHER", 1.01))
    return next(rel for rel, cut in cuts if u < cut)


def _pick(pool: tuple[str, ...], idx: int, last: str) -> str:
    """Return ``pool[idx]`` (or the next entry) such that the full name is not a reserved demo name."""
    while f"{pool[idx % len(pool)]} {last}" in RESERVED_NAMES:
        idx += 1
    return pool[idx % len(pool)]


def make_people(
    rng: np.random.Generator,
    epics: Iterator[str],
    part_no: int,
    ages: Sequence[int],
    female_share: float,
    house_nos: Sequence[str],
    surnames: Sequence[str],
) -> list[Row]:
    """Build one roll row per age; house_no and household surname are given per voter.

    ``serial_no`` is set to 0 here and assigned when the booth roll is finalised.
    """
    n = len(ages)
    u_gender, u_rel, u_misc = rng.random(n), rng.random(n), rng.random(n)
    first_m = rng.integers(0, len(MALE_FIRST), n)
    first_f = rng.integers(0, len(FEMALE_FIRST), n)
    rel_m = rng.integers(0, len(MALE_FIRST), n)
    rel_f = rng.integers(0, len(FEMALE_FIRST), n)
    rows: list[Row] = []
    for i in range(n):
        age, sur = int(ages[i]), surnames[i]
        if u_gender[i] < _O_SHARE:
            gender = "O"
        elif u_gender[i] < _O_SHARE + female_share:
            gender = "F"
        else:
            gender = "M"
        relation = _relation(gender, age, float(u_rel[i]))
        last = sur
        if gender == "F" and relation == "HUSBAND" and u_misc[i] < 0.35:
            last = "Devi"
        elif gender == "F" and relation == "FATHER" and u_misc[i] < 0.15:
            last = "Kumari"
        use_female = gender == "F" or (gender == "O" and u_misc[i] < 0.5)
        first = _pick(FEMALE_FIRST, int(first_f[i]), last) if use_female else _pick(MALE_FIRST, int(first_m[i]), last)
        rel_first = FEMALE_FIRST[int(rel_f[i])] if relation == "MOTHER" else MALE_FIRST[int(rel_m[i])]
        rows.append({
            "epic_no": next(epics), "ac_no": AC_NO, "part_no": part_no, "serial_no": 0,
            "name": f"{first} {last}", "relative_name": f"{rel_first} {sur}",
            "relation_type": relation, "house_no": house_nos[i], "age": age, "gender": gender,
        })
    return rows

