
"""Why a fixed-N attack success rate misleads: Beta-mixture of per-task success probabilities.
Population ASR(N) = 1 - E[(1-p)^N] = 1 - B(a, b+N)/B(a, b) ~ 1 - Gamma(a+b)/Gamma(b) * N^(-a).
Sampling-based attacks only (independent attempts); adaptive optimization attackers are NOT covered."""
import csv
import numpy as np
from scipy.special import betaln, gammaln
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(2026)
DEF = {"A (light tail, a=2)": (2.0, 98.0), "B (heavy tail, a=0.2)": (0.2, 9.8)}   # both mean 0.02
NS = [1, 10, 100, 1000, 10000, 100000]

def asr(a, b, N):
    return 1 - np.exp(betaln(a, b + N) - betaln(a, b))

def coef(a, b):
    return np.exp(gammaln(a + b) - gammaln(b))

def fit_bb(k, n):
    vals, cnt = np.unique(k, return_counts=True)
    def nll(th):
        a, b = np.exp(th)
        return -np.sum(cnt * (betaln(vals + a, n - vals + b) - betaln(a, b)))
    best = None
    for st in [(0.0, 3.0), (-1.5, 2.0), (1.0, 4.5)]:
        r = minimize(nll, st, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 400})
        if best is None or r.fun < best.fun:
            best = r
    return np.exp(best.x)

M, n, REPS, PRED = 300, 20, 100, [100, 1000, 10000]
res = {}
for name, (a, b) in DEF.items():
    mle = {N: [] for N in PRED}; hom = {N: [] for N in PRED}; a_hat = []
    for _ in range(REPS):
        p = rng.beta(a, b, size=M); k = rng.binomial(n, p)
        ah, bh = fit_bb(k, n); a_hat.append(ah)
        ph = k.sum() / (M * n)
        for N in PRED:
            mle[N].append(asr(ah, bh, N)); hom[N].append(1 - (1 - ph) ** N)
    res[name] = (mle, hom, np.array(a_hat))

rows = []
for name, (a, b) in DEF.items():
    mle, hom, a_hat = res[name]
    print(name, "1-ASR ~ %.3g * N^-%.2g" % (coef(a, b), a), "| a_hat median %.2f [5,95]=%s" % (np.median(a_hat), np.round(np.percentile(a_hat, [5, 95]), 2)))
    for N in PRED:
        t = asr(a, b, N); q = np.percentile(mle[N], [5, 50, 95]); h = np.percentile(hom[N], [5, 50, 95])
        print(f"  N={N:>6}: truth {t:.3f} | MLE {q[1]:.3f} [{q[0]:.3f},{q[2]:.3f}] | homogeneous {h[1]:.3f} [{h[0]:.3f},{h[2]:.3f}]")
        rows.append((name, N, round(t, 4), round(q[1], 4), round(q[0], 4), round(q[2], 4), round(h[1], 4), round(h[0], 4), round(h[2], 4)))
    print("  curve:", {N: round(float(asr(a, b, N)), 3) for N in NS})
with open("heavy_tail_results.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["defense", "N", "true_ASR", "mle_median", "mle_p5", "mle_p95", "homog_median", "homog_p5", "homog_p95"]); w.writerows(rows)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
Ns = np.logspace(0, 5, 60)
for name, (a, b) in DEF.items():
    ax1.semilogx(Ns, asr(a, b, Ns), label=name)
ax1.set_xlabel("attempts per task N"); ax1.set_ylabel("population ASR(N)")
ax1.set_title("Same ASR(1)=2%, very different growth", fontsize=10); ax1.legend(fontsize=8)
data, labs, i = [], [], 0
for name, (a, b) in DEF.items():
    mle, hom, _ = res[name]
    data += [mle[10000], hom[10000]]; short = name.split(" (")[0]
    labs += [short + "\nMLE", short + "\nhomog."]
    ax2.hlines(asr(a, b, 10000), i + 0.5, i + 2.5, colors="k", linestyles="--", lw=1); i += 2
ax2.boxplot(data, showfliers=False)
ax2.set_xticks(range(1, len(labs) + 1))
ax2.set_xticklabels(labs)
ax2.set_ylabel("predicted ASR at N=10,000"); ax2.set_ylim(0, 1.02)
ax2.set_title("Predicting from 300 tasks x 20 attempts (dashes = truth)", fontsize=10)
plt.tight_layout(); plt.savefig("heavy_tail.png", dpi=150)
