
"""Day 4: utility vs per-session leakage budget under an IMPOSED 0/1/3-bit policy.
These costs are an experimental policy, not capacities implied by the FIDES taxonomy.
Counts = FIDES Table 2 percentages x suite size (40/20/16/21 = 97 user tasks; suite sizes inferred)."""
import csv, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COUNTS = {"workspace": (19, 19, 2), "travel": (0, 18, 2), "banking": (3, 6, 7), "slack": (4, 8, 9)}  # (DI, DIQ, DD)
SIZE = {"workspace": 40, "travel": 20, "banking": 16, "slack": 21}
for k in COUNTS:
    assert sum(COUNTS[k]) == SIZE[k]
COUNTS["all (97 tasks)"] = tuple(sum(COUNTS[s][i] for s in SIZE) for i in range(3))
SIZE["all (97 tasks)"] = 97
POLICY = (0, 1, 3)          # bits per session for DI, DIQ, DD
SECRET_BITS = 40

def allowed_fraction(suite, budget):
    return sum(c for c, cost in zip(COUNTS[suite], POLICY) if cost <= budget) / SIZE[suite]

def sessions_to_recover(secret_bits, per_session_bits):
    return math.inf if per_session_bits == 0 else math.ceil(secret_bits / per_session_bits)

budgets = [0, 1, 3]
rows = [(s, b, round(100 * allowed_fraction(s, b), 1), sessions_to_recover(SECRET_BITS, b))
        for s in COUNTS for b in budgets]
with open("utility_curve.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "budget_bits", "utility_pct_oracle", "sessions_to_recover_40bit"]); w.writerows(rows)

fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4))
for s in COUNTS:
    a.step(budgets, [100 * allowed_fraction(s, x) for x in budgets], where="post", marker="o",
           lw=3 if s.startswith("all") else 1.2, label=s)
a.set_xlabel("per-session budget (bits)"); a.set_ylabel("tasks allowed (%)"); a.set_xticks(budgets)
a.set_title("Oracle utility under imposed 0/1/3-bit policy", fontsize=10); a.legend(fontsize=8)
xs = [1, 2, 3, 4, 6, 8]
b.plot(xs, [sessions_to_recover(SECRET_BITS, x) for x in xs], "o-")
b.set_xlabel("bits leaked per session (tight channel)"); b.set_ylabel(f"sessions to recover {SECRET_BITS}-bit secret")
b.set_title("Worst-case sessions to compromise", fontsize=10)
plt.tight_layout(); plt.savefig("utility_curve.png", dpi=150)
for r in rows: print(r)
