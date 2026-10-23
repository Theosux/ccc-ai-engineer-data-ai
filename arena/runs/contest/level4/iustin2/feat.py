"""Hand-built value features for Colony: One, written twice: numpy (fit) and ONNX (build.py). Side-to-move view.
planes: 0-5 own Ping Daemon Exploit Trace Ice Kernel, 6-11 enemy, 12 locked, 13 actions_left/2, 14 urgency, 15 magenta."""
import numpy as np

RING = np.array([[min(r, c, 7 - r, 7 - c) for c in range(8)] for r in range(8)], np.float32)   # 0 outer .. 3 centre
RINGK = np.stack([(RING == k).astype(np.float32) for k in range(4)])                            # (4,8,8)
RSIZE = RINGK.reshape(4, -1).sum(1)                                                             # 28 20 12 4


def box(p, rad):
    """Sum over a (2rad+1)^2 window (zero padded), p: (N,8,8)."""
    out = np.zeros_like(p)
    pp = np.pad(p, ((0, 0), (rad, rad), (rad, rad)))
    for dr in range(2 * rad + 1):
        for dc in range(2 * rad + 1):
            out += pp[:, dr:dr + 8, dc:dc + 8]
    return out


NAMES = []


def features(P):
    """P: (N,16,8,8) float -> (N,F) float32."""
    P = P.astype(np.float32)
    own, enm = P[:, 0:5], P[:, 6:11]
    oK, eK = P[:, 5], P[:, 11]
    oN, eN = own.sum(1), enm.sum(1)
    locked, urg, mag, al = P[:, 12], P[:, 14].mean((1, 2)), P[:, 15].mean((1, 2)), P[:, 13].mean((1, 2))
    rl = (locked[:, None] * RINGK[None]).sum((2, 3)) / RSIZE        # (N,4) fraction locked per ring (0/1)
    nl = rl.sum(1)                                                   # rings locked
    nxt = sum(RINGK[k][None] * np.maximum(0, 1 - np.abs(nl - k))[:, None, None] for k in range(4))  # next ring to lock
    f = {}
    for i, n in enumerate("ping daemon exploit trace ice".split()):
        f[f"own_{n}"] = own[:, i].sum((1, 2))
        f[f"enm_{n}"] = enm[:, i].sum((1, 2))
    for side, K, N, X in (("own", oK, oN, eN), ("enm", eK, eN, oN)):
        g = (box(K, 1) * N).sum((1, 2))                              # bodyguards next to the Kernel
        f[f"{side}_guard"] = g
        f[f"{side}_guard1"] = np.minimum(g, 1)
        f[f"{side}_guard2"] = np.minimum(g, 2)
        f[f"{side}_threat2"] = (box(K, 2) * X).sum((1, 2))          # enemy pieces within distance 2 of the Kernel
        f[f"{side}_threat1"] = (box(K, 1) * X).sum((1, 2))
        kr = (K * RING).sum((1, 2))
        margin = kr - nl                                             # 0 = Kernel stands on the next ring to lock
        f[f"{side}_kmargin"] = margin
        f[f"{side}_kedge_urg"] = np.maximum(0, 1 - margin) * urg
        f[f"{side}_kedge"] = np.maximum(0, 1 - margin)
        f[f"{side}_doomed_urg"] = (N * nxt).sum((1, 2)) * urg         # pieces about to be destroyed by the firewall
    f["mag"] = mag
    f["al"] = al
    f["urg"] = urg
    NAMES[:] = list(f)
    return np.stack([f[k] for k in NAMES], 1).astype(np.float32)
