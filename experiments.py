
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from core import *

ping = Emit("net", lambda s, u: "ping", False)
chan = {
 "1. compare\n(K=2, N=16)": (If(lambda s,u: s>=u, ping, Skip(), True), 16, 16, True),
 "2. loop count\n(K=10, N=10)": (Loop(lambda s,u: s, 9, Emit("net", lambda s,u: "cat.jpg", False), True), 10, 1, True),
 "3. windowed loop\n(K=4, N=16)": (Loop(lambda s,u: min(max(s-u,0),3), 3, Emit("net", lambda s,u: "cat.jpg", False), True), 16, 16, True),
 "4. exception,\nHALT visible (K=2, N=16)": (If(lambda s,u: s>=u, Halt(), Skip(), True), 16, 16, True),
 "5. exception,\nHALT hidden (K=2, N=16)": (If(lambda s,u: s>=u, Halt(), Skip(), True), 16, 16, False),
}
rows, Q = [], range(1, 5)
fig, axs = plt.subplots(1, len(chan), figsize=(4 * len(chan), 3.6), sharey=True)
for ax, (name, (p, n, nu, tv)) in zip(axs, chan.items()):
    validate_annotations(p, range(n), range(nu))
    k = K(p)
    emp = [leakage_bits(optimal_leaves(p, range(n), range(nu), q, tv)) for q in Q]
    bnd = [bound_bits(k, q, n) for q in Q]
    for q, e, b in zip(Q, emp, bnd):
        assert e <= b + 1e-9
        rows.append((name.replace("\n", " "), q, round(e, 3), round(b, 3)))
    ax.plot(list(Q), bnd, "k--", label="static bound")
    ax.plot(list(Q), emp, "o-", label="optimal attacker")
    ax.set_title(name, fontsize=9); ax.set_xlabel("sessions q"); ax.set_xticks(list(Q))
axs[0].set_ylabel("bits leaked"); axs[0].legend(fontsize=8)
plt.tight_layout(); plt.savefig("leakage_vs_bound.png", dpi=150)
with open("results.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["channel", "q", "empirical_bits", "bound_bits"]); w.writerows(rows)
for r in rows: print(r)
