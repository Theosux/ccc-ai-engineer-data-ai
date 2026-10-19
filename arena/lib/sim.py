"""Simulation helpers: skip huge step counts by cycle detection."""


def find_cycle(state, step, key=lambda s: s, max_steps=10**7):
    """Iterate state=step(state) until a key repeats. Returns (mu, lam, history):
    first repeated state index mu, cycle length lam, history = states[0..mu+lam-1]."""
    seen = {}
    hist = []
    i = 0
    while i < max_steps:
        k = key(state)
        if k in seen:
            mu = seen[k]
            return mu, i - mu, hist
        seen[k] = i
        hist.append(state)
        state = step(state)
        i += 1
    raise RuntimeError("no cycle within max_steps")


def state_at(state, step, n, key=lambda s: s):
    """State after n steps (n can be 10**18) using cycle detection. States must be hashable via key."""
    mu, lam, hist = find_cycle(state, step, key)
    if n < len(hist):
        return hist[n]
    return hist[mu + (n - mu) % lam]
