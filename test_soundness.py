
import random, math
import pytest
from core import *

N, U = 8, range(4)

def rand_leaf(rng):
    t = rng.random()
    if t < 0.4:
        d = rng.randint(2, 4); tab = [rng.randrange(d) for _ in range(N)]
        return Emit("net", lambda s, u, tab=tab: tab[s], True, d)
    if t < 0.6:
        return Emit("net", lambda s, u: ("c", u % 2), False, None)
    if t < 0.8:
        return Halt()
    return Skip()

def rand_prog(rng, depth):
    if depth == 0:
        return rand_leaf(rng)
    t = rng.random()
    if t < 0.3:
        return Seq(rand_prog(rng, depth - 1), rand_prog(rng, depth - 1))
    if t < 0.6:
        if rng.random() < 0.6:
            tab = [rng.random() < 0.5 for _ in range(N)]
            return If(lambda s, u, tab=tab: tab[s], rand_prog(rng, depth - 1), rand_prog(rng, depth - 1), True)
        return If(lambda s, u: u % 2 == 0, rand_prog(rng, depth - 1), rand_prog(rng, depth - 1), False)
    n = rng.randint(1, 3)
    if rng.random() < 0.6:
        tab = [rng.randint(0, n) for _ in range(N)]
        return Loop(lambda s, u, tab=tab: tab[s], n, rand_prog(rng, depth - 1), True)
    return Loop(lambda s, u, n=n: u % (n + 1), n, rand_prog(rng, depth - 1), False)

CMP = If(lambda s, u: s >= u, Emit("net", lambda s, u: "ping", False), Skip(), True)

def test_theorem1_soundness_random_programs():
    rng = random.Random(7)
    for _ in range(3000):
        p = rand_prog(rng, rng.randint(0, 3))
        for tv in (True, False):
            for u in U:
                assert len(trace_set(p, range(N), u, tv)) <= K(p)

def test_random_programs_pass_validator():
    rng = random.Random(11)
    for _ in range(500):
        validate_annotations(rand_prog(rng, rng.randint(0, 3)), range(N), U)

def test_hand_examples():
    loop = Loop(lambda s, u: s, 9, Emit("net", lambda s, u: "cat.jpg", False), True)
    assert K(loop) == 10
    exc = If(lambda s, u: s == 3, Halt(), Emit("net", lambda s, u: "x", False), True)
    assert K(exc) == 2
    assert K(Seq(loop, exc)) == 20

def test_exception_needs_terminal_marker():
    exc = If(lambda s, u: s == 3, Halt(), Skip(), True)
    assert len(trace_set(exc, range(N), 0, True)) == 2
    assert len(trace_set(exc, range(N), 0, False)) == 1

def test_theorem2_optimal_attacker_never_exceeds_product():
    for q in range(1, 5):
        assert optimal_leaves(CMP, range(16), range(16), q) <= min(16, K(CMP) ** q)

def test_theorem3_tightness_binary_search():
    for d in range(1, 5):
        n = 2 ** d
        assert optimal_leaves(CMP, range(n), range(n), d) == n

def test_validator_catches_mislabeled_dependency():
    with pytest.raises(ValueError):
        validate_annotations(Emit("net", lambda s, u: s, secret_dep=False), range(4), range(2))

def test_validator_catches_domain_violation():
    with pytest.raises(ValueError):
        validate_annotations(Emit("net", lambda s, u: s, True, 2), range(4), range(2))

def test_loop_certificate_enforced():
    p = Loop(lambda s, u: s, 2, Skip(), True)
    with pytest.raises(ValueError):
        obs(p, 5, 0)
    with pytest.raises(ValueError):
        validate_annotations(p, range(6), range(1))

def test_zero_sessions_and_generators():
    assert bound_bits(math.inf, 0, 8) == 0.0
    assert optimal_leaves(CMP, range(8), range(8), 0) == 1
    assert optimal_leaves(CMP, (x for x in range(8)), (x for x in range(8)), 3) == 8
