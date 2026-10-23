import capi, engine as E
SC = ["00006000-6767-0000-0070-676700000000","00006700-6767-0006-7670-676706706700","06706700-6767-6706-7670-676706706767"]

def magenta_can_kill(b):
    if E.kernel(b, "C") is None: return True
    for a in E.actions(b, "M"):
        b1 = E.apply(b, a)
        if E.kernel(b1, "C") is None: return True
        for a2 in E.actions(b1, "M"):
            if E.kernel(E.apply(b1, a2), "C") is None: return True
    return False

for sc in SC:
    st = capi.new_game(sc)["state"]
    b = E.parse_render(st["render"])
    srv = sorted(x["notation"] for x in st["legal_actions"])
    mine = sorted(f"{E.sq(f)} -> {E.sq(t)}" for _, f, t in E.actions(b, "C"))
    assert srv == mine, (srv, mine)
    safe = set()
    for a in E.actions(b, "C"):
        b1 = E.apply(b, a)
        for a2 in E.actions(b1, "C"):
            b2 = E.apply(b1, a2)
            if E.kernel(b2, "M") is None or not magenta_can_kill(b2):
                safe.add(E.sq(E.kernel(b2, "C")))
    print(sc, sorted(safe))
