"""Firewall-aware handcrafted evaluator for the level-4 referee.

The driver's seat model is linear material + centre. This one adds the ring that
is about to lock, bodyguard placement, and a penalty for stepping onto an empty
square an enemy Ice or Daemon can take. `evaluate(obs, p)` is the numpy form;
`build_onnx` writes the same function as a tournament model.
"""
import numpy as np

RING = np.array([[min(r, c, 7 - r, 7 - c) for c in range(8)] for r in range(8)], np.float32)
CENT = np.array([[3.5 - max(abs(r - 3.5), abs(c - 3.5)) for c in range(8)] for r in range(8)], np.float32)
# ping daemon exploit trace ice kernel — capture logits before the kernel override
CAP0 = np.array([1.5, 4.5, 2.5, 3.0, 5.0, 0.0], np.float32)
VAL0 = np.array([0.45, 1.35, 0.75, 0.90, 1.50, 0.0], np.float32)
HANG0 = np.array([1.5, 4.5, 2.5, 3.0, 5.0, 20.0], np.float32)
GUARD0 = np.array([2.0, 0.6, 1.4, 0.8, 0.2, 0.0], np.float32)

# Tuned against the driver's linear seat model (build4.default_params).
# High danger / kernel-capture, modest centre bias, hanging-piece value.
DEFAULT = dict(center=0.266, cap=1.420, kcap=33.27, escape=8.0, enter=-8.75,
               guard=1.24, strike=5.25, danger=2.639, v_cent=0.08, v_burn=0.88,
               v_k=2.2, v_hang=0.5)


def _box(plane, rad):
    p = np.pad(plane, ((0, 0), (rad, rad), (rad, rad)))
    acc = np.zeros_like(plane)
    k = 2 * rad + 1
    for dr in range(k):
        for dc in range(k):
            acc += p[:, dr:dr + plane.shape[1], dc:dc + plane.shape[2]]
    return acc


def evaluate(obs, p=None):
    p = {**DEFAULT, **(p or {})}
    obs = np.asarray(obs, np.float32)
    single = obs.ndim == 3
    if single:
        obs = obs[None]
    own, enemy = obs[:, 0:6], obs[:, 6:12]
    locked = obs[:, 12]
    urg = obs[:, 14, 0, 0]
    depth = locked[:, 0, 0] + locked[:, 1, 1] + locked[:, 2, 2] + locked[:, 3, 3]
    burn = (np.abs(RING[None] - depth[:, None, None]) < 0.5).astype(np.float32)
    own_k, enemy_k = own[:, 5], enemy[:, 5]
    b = obs.shape[0]

    val = VAL0.copy(); val[5] = p["v_k"]
    mat = sum((own[:, i] - enemy[:, i]).sum((1, 2)) * val[i] for i in range(6))
    cent = (own_k * CENT).sum((1, 2)) - (enemy_k * CENT).sum((1, 2))
    burn_term = urg * ((own_k * burn).sum((1, 2)) - (enemy_k * burn).sum((1, 2)))
    # Own material already standing where an enemy Ice (Chebyshev 2) or Daemon (shot) reaches.
    zone = ((_box(enemy[:, 4], 2) + _box(enemy[:, 1], 1)) > 0).astype(np.float32)
    zone = zone * (enemy.sum(1) == 0)
    hung = sum((own[:, i] * zone).sum((1, 2)) * val[i] for i in range(6))
    value = np.tanh(mat + p["v_cent"] * cent - p["v_burn"] * burn_term - p["v_hang"] * hung
                    - 0.05 * obs[:, 15, 0, 0]).astype(np.float32)

    cap = CAP0 * p["cap"]; cap[5] = p["kcap"]
    cap_map = sum(enemy[:, i] * cap[i] for i in range(6))
    own_any = own.sum(1)
    own_guard = sum(own[:, i] * GUARD0[i] for i in range(6))
    f = own_any.reshape(b, 64, 1)
    ok = own_k.reshape(b, 64, 1)
    nonk = np.clip(own_any - own_k, 0, 1).reshape(b, 64, 1)
    bf, bt = burn.reshape(b, 64, 1), burn.reshape(b, 1, 64)
    u = urg.reshape(b, 1, 1)
    pol = f * CENT.reshape(1, 1, 64) * p["center"]
    pol = pol + f * cap_map.reshape(b, 1, 64)
    pol = pol + ok * bf * (1.0 - bt) * (p["escape"] * (0.4 + u))
    pol = pol + ok * bt * u * p["enter"]
    pol = pol + nonk * bf * (1.0 - bt) * u * (p["escape"] * 0.35)
    nk_own = _box(own_k, 1) - own_k
    nk_enemy = _box(enemy_k, 1) - enemy_k
    pol = pol + own_guard.reshape(b, 64, 1) * nk_own.reshape(b, 1, 64) * p["guard"]
    pol = pol + f * (cap_map.reshape(b, 1, 64) > 0) * (nk_enemy.reshape(b, 1, 64) > 0) * p["strike"]
    enemy_any = enemy.sum(1)
    empty = 1.0 - np.clip(own_any + enemy_any, 0, 1)
    hot = (_box(enemy[:, 4], 2) + _box(enemy[:, 1], 1) + (_box(enemy_k, 1) - enemy_k)) * empty
    hang = sum(own[:, i] * HANG0[i] for i in range(6))
    pol = pol - hang.reshape(b, 64, 1) * hot.reshape(b, 1, 64) * p["danger"]
    logits = pol.reshape(b, 4096).astype(np.float32)
    if single:
        return logits[0], value[0]
    return logits, value
