"""Local, free, deterministic embeddings (feature hashing). No network, no paid API.
Swap for sentence-transformers/pgvector later behind the same two functions."""
import hashlib
import math
import re

DIM = 256
_STOP = set("the a an and or of to in on for is are was were be by with at as it this that from we you i".split())
_Q_STOP = _STOP | set("what whats how why who whom when where which do does did done have has had can could should would our your about there any "
                      "tell me us please service services api".split())


def tokens(text: str):
    ws = [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if w not in _STOP]
    return ws + [f"{a}_{b}" for a, b in zip(ws, ws[1:])]


def embed(text: str):
    v = [0.0] * DIM
    for t in tokens(text):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 8) % 2 == 0 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 5) for x in v]


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) if a and b else 0.0


def overlap(q: str, t: str) -> float:
    qs, ts = set(re.findall(r"[a-z0-9_]+", q.lower())) - _Q_STOP, set(re.findall(r"[a-z0-9_]+", t.lower()))
    return len(qs & ts) / len(qs) if qs else 0.0
