
"""Toy typed-plan IR, static trace-capacity accountant K(P), annotation validator,
and exact optimal adaptive attacker (DP over candidate sets).

Scope: deterministic plans, one persistent secret, uniform prior, pure callables of (s, u).
No mutable cross-session agent memory. The accountant TRUSTS the annotations
(secret_dep, domain, n_max); use validate_annotations to test them on small domains.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Hashable

class Node: ...

@dataclass(frozen=True)
class Skip(Node): ...

@dataclass(frozen=True)
class Halt(Node):
    """Uncaught exception / early termination."""

@dataclass(frozen=True)
class Emit(Node):
    sink: str
    value: Callable[[int, int], Hashable]
    secret_dep: bool = True
    domain: int | None = None          # |tau|; None means unbounded (string)

@dataclass(frozen=True)
class Seq(Node):
    a: Node
    b: Node

@dataclass(frozen=True)
class If(Node):
    cond: Callable[[int, int], bool]
    then: Node
    els: Node
    secret_dep: bool = True

@dataclass(frozen=True)
class Loop(Node):
    count: Callable[[int, int], int]
    n_max: int
    body: Node
    secret_dep: bool = True

def _run(p: Node, s: int, u: int, tr: list) -> bool:
    """Execute p, append visible events to tr, return True if halted."""
    if isinstance(p, Skip):
        return False
    if isinstance(p, Halt):
        return True
    if isinstance(p, Emit):
        tr.append((p.sink, p.value(s, u)))
        return False
    if isinstance(p, Seq):
        return _run(p.a, s, u, tr) or _run(p.b, s, u, tr)
    if isinstance(p, If):
        return _run(p.then if p.cond(s, u) else p.els, s, u, tr)
    if isinstance(p, Loop):
        m = p.count(s, u)
        if not 0 <= m <= p.n_max:
            raise ValueError("loop-count certificate violated")
        for _ in range(m):
            if _run(p.body, s, u, tr):
                return True
        return False
    raise TypeError(p)

def obs(p: Node, s: int, u: int, terminal_visible: bool = True) -> tuple:
    tr: list = []
    halted = _run(p, s, u, tr)
    if halted and terminal_visible:
        tr.append(("HALT",))
    return tuple(tr)

def K(p: Node) -> float:
    """Static bound on |{obs(p,s,u): s}| valid for every fixed u."""
    if isinstance(p, (Skip, Halt)):
        return 1
    if isinstance(p, Emit):
        if not p.secret_dep:
            return 1
        return math.inf if p.domain is None else p.domain
    if isinstance(p, Seq):
        return K(p.a) * K(p.b)
    if isinstance(p, If):
        k1, k2 = K(p.then), K(p.els)
        return k1 + k2 if p.secret_dep else max(k1, k2)
    if isinstance(p, Loop):
        kb = K(p.body)
        if not p.secret_dep:
            return kb ** p.n_max
        return p.n_max + 1 if kb == 1 else sum(kb ** m for m in range(p.n_max + 1))
    raise TypeError(p)

def trace_set(p: Node, secrets, u: int, terminal_visible=True) -> set:
    return {obs(p, s, u, terminal_visible) for s in secrets}

def optimal_leaves(p: Node, secrets, inputs, q: int, terminal_visible=True) -> int:
    """Max number of distinct transcripts over all deterministic adaptive q-session attackers.
    Restriction: the same plan p is used in every session (the theorem allows P_j to vary)."""
    secrets, inputs = tuple(secrets), tuple(inputs)
    if not secrets or not inputs or q < 0:
        raise ValueError("need nonempty secrets/inputs and q >= 0")
    if q == 0:
        return 1
    table = {(s, u): obs(p, s, u, terminal_visible) for s in secrets for u in inputs}

    @lru_cache(maxsize=None)
    def go(cands: frozenset, rounds: int) -> int:
        if rounds == 0 or len(cands) == 1:
            return 1
        best = 1
        for u in inputs:
            blocks: dict = {}
            for s in cands:
                blocks.setdefault(table[(s, u)], []).append(s)
            best = max(best, sum(go(frozenset(b), rounds - 1) for b in blocks.values()))
        return best

    return go(frozenset(secrets), q)

def leakage_bits(leaves: int) -> float:
    return math.log2(leaves)

def bound_bits(k: float, q: int, n: int) -> float:
    if n < 1 or q < 0:
        raise ValueError("need n >= 1 and q >= 0")
    if q == 0:
        return 0.0
    return min(math.log2(n), q * math.log2(k))

def _check(cond, msg: str):
    if not cond:
        raise ValueError(msg)

def validate_annotations(p: Node, secrets, inputs) -> None:
    """Executable proof obligations on small domains: declared domains, secret_dep=False
    independence, loop certificates, parameters. Callables are treated as pure functions."""
    secrets, inputs = tuple(secrets), tuple(inputs)
    _check(secrets and inputs, "empty secret or input domain")
    if isinstance(p, (Skip, Halt)):
        return
    if isinstance(p, Emit):
        if p.domain is not None:
            _check(p.domain >= 1, "domain must be >= 1")
        for u in inputs:
            vals = {p.value(s, u) for s in secrets}
            if not p.secret_dep:
                _check(len(vals) == 1, f"Emit({p.sink}) marked secret_dep=False but depends on s")
            elif p.domain is not None:
                _check(len(vals) <= p.domain, f"Emit({p.sink}) exceeds declared domain {p.domain}")
    elif isinstance(p, Seq):
        validate_annotations(p.a, secrets, inputs)
        validate_annotations(p.b, secrets, inputs)
    elif isinstance(p, If):
        if not p.secret_dep:
            for u in inputs:
                _check(len({bool(p.cond(s, u)) for s in secrets}) == 1,
                       "If marked secret_dep=False but guard depends on s")
        validate_annotations(p.then, secrets, inputs)
        validate_annotations(p.els, secrets, inputs)
    elif isinstance(p, Loop):
        _check(p.n_max >= 0, "n_max must be >= 0")
        for u in inputs:
            counts = {p.count(s, u) for s in secrets}
            _check(all(0 <= m <= p.n_max for m in counts), "loop-count certificate violated")
            if not p.secret_dep:
                _check(len(counts) == 1, "Loop marked secret_dep=False but count depends on s")
        validate_annotations(p.body, secrets, inputs)
