"""Write heuristic.DEFAULT as an allow-listed ONNX model (opset 17, dynamic batch)."""
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

sys.path.insert(0, str(Path(__file__).resolve().parent))
from heuristic import CAP0, CENT, DEFAULT, GUARD0, HANG0, RING, VAL0


def build(path, p=None):
    p = p or DEFAULT
    inits, nodes = [], []

    def C(name, arr, dtype=None):
        a = np.asarray(arr if dtype is None else np.asarray(arr, dtype))
        inits.append(numpy_helper.from_array(a, name))
        return name

    def N(op, ins, out, **kw):
        nodes.append(helper.make_node(op, ins, [out], **kw))
        return out

    def sl(src, out, axis, start, end):
        s, e, ax = C(out + "_s", [start], np.int64), C(out + "_e", [end], np.int64), C(out + "_a", [axis], np.int64)
        return N("Slice", [src, s, e, ax], out)

    C("k3", np.ones((1, 1, 3, 3), np.float32))
    C("k5", np.ones((1, 1, 5, 5), np.float32))
    C("ring", RING.reshape(1, 1, 8, 8))
    C("cent64", CENT.reshape(1, 1, 64))
    cent88 = C("cent88", CENT.reshape(1, 1, 8, 8))
    diag = np.zeros((1, 1, 8, 8), np.float32)
    for i in range(4):
        diag[0, 0, i, i] = 1
    C("diag", diag)
    e00 = np.zeros((1, 1, 8, 8), np.float32); e00[0, 0, 0, 0] = 1
    C("e00", e00)
    one = C("one", np.array([1], np.float32))
    axes23 = C("ax23", np.array([2, 3], np.int64))
    C("sh_b", np.array([-1], np.int64))
    C("sh_b64", np.array([-1, 64], np.int64))
    C("sh_b641", np.array([-1, 64, 1], np.int64))
    C("sh_b164", np.array([-1, 1, 64], np.int64))
    C("sh_b4096", np.array([-1, 4096], np.int64))
    C("sh_b111", np.array([-1, 1, 1, 1], np.int64))

    def box(x, rad, name):
        w = "k3" if rad == 1 else "k5"
        return N("Conv", [x, w], name, pads=[rad, rad, rad, rad])

    def rsum(x, name):
        y = N("ReduceSum", [x, axes23], name, keepdims=0)
        return N("Reshape", [y, "sh_b"], name + "v")

    own, enemy = [], []
    for i in range(6):
        own.append(sl("observation", f"own{i}", 1, i, i + 1))
        enemy.append(sl("observation", f"en{i}", 1, 6 + i, 7 + i))
    locked = sl("observation", "locked", 1, 12, 13)
    urg_p = sl("observation", "urgp", 1, 14, 15)
    side_p = sl("observation", "sidep", 1, 15, 16)

    depth_m = N("Mul", [locked, "diag"], "depthm")
    depth_s = N("ReduceSum", [depth_m, axes23], "depths", keepdims=1)
    depth = N("Reshape", [depth_s, "sh_b111"], "depth")
    diff = N("Abs", [N("Sub", ["ring", depth], "rdiff")], "adiff")
    burn = N("Sub", [C("ones88", np.ones((1, 1, 8, 8), np.float32)), N("Min", [diff, C("one88", np.ones((1, 1, 8, 8), np.float32))], "mdiff")], "burn")

    def add_planes(planes, name):
        acc = planes[0]
        for i, pl in enumerate(planes[1:], 1):
            acc = N("Add", [acc, pl], f"{name}{i}")
        return acc

    own_any = add_planes(own, "oa")
    enemy_any = add_planes(enemy, "ea")
    own_k, enemy_k = own[5], enemy[5]

    # value
    val = VAL0.copy(); val[5] = p["v_k"]
    mat = None
    for i in range(6):
        d = N("Sub", [own[i], enemy[i]], f"md{i}")
        s = rsum(d, f"ms{i}")
        term = N("Mul", [s, C(f"vw{i}", np.array([val[i]], np.float32))], f"mt{i}")
        mat = term if mat is None else N("Add", [mat, term], f"mat{i}")
    ck = N("Mul", [own_k, cent88], "ck")
    ek = N("Mul", [enemy_k, cent88], "ek")
    cent = N("Sub", [rsum(ck, "cks"), rsum(ek, "eks")], "cent")
    ob = rsum(N("Mul", [own_k, burn], "okb"), "okbs")
    eb = rsum(N("Mul", [enemy_k, burn], "ekb"), "ekbs")
    urg = rsum(N("Mul", [urg_p, "e00"], "urgm"), "urg")
    burn_term = N("Mul", [urg, N("Sub", [ob, eb], "bd")], "bt")
    ice_z = box(enemy[4], 2, "icez")
    dae_z = box(enemy[1], 1, "daez")
    zone_g = N("Greater", [N("Add", [ice_z, dae_z], "zd"), C("z0", np.zeros((1, 1, 8, 8), np.float32))], "zg")
    zone = N("Mul", [N("Cast", [zone_g], "zf", to=TensorProto.FLOAT),
                     N("Sub", [C("ones88b", np.ones((1, 1, 8, 8), np.float32)),
                               N("Min", [enemy_any, C("one88c", np.ones((1, 1, 8, 8), np.float32))], "eac")], "empty_e")], "zone")
    hung = None
    for i in range(6):
        s = rsum(N("Mul", [own[i], zone], f"hz{i}"), f"hs{i}")
        term = N("Mul", [s, C(f"hv{i}", np.array([val[i]], np.float32))], f"ht{i}")
        hung = term if hung is None else N("Add", [hung, term], f"hung{i}")
    side = rsum(N("Mul", [side_p, "e00"], "sidem"), "side")
    v = mat
    v = N("Add", [v, N("Mul", [cent, C("vc", np.array([p["v_cent"]], np.float32))], "vcv")], "v1")
    v = N("Sub", [v, N("Mul", [burn_term, C("vb", np.array([p["v_burn"]], np.float32))], "vbv")], "v2")
    v = N("Sub", [v, N("Mul", [hung, C("vh", np.array([p["v_hang"]], np.float32))], "vhv")], "v3")
    v = N("Sub", [v, N("Mul", [side, C("vs", np.array([0.05], np.float32))], "vsv")], "v4")
    value = N("Reshape", [N("Tanh", [v], "vt"), "sh_b"], "value")

    # policy
    cap = CAP0 * p["cap"]; cap[5] = p["kcap"]
    cap_map = None
    for i in range(6):
        term = N("Mul", [enemy[i], C(f"cp{i}", np.array([[[[cap[i]]]]], np.float32))], f"cm{i}")
        cap_map = term if cap_map is None else N("Add", [cap_map, term], f"cap{i}")
    guard = None
    for i in range(6):
        term = N("Mul", [own[i], C(f"gw{i}", np.array([[[[GUARD0[i]]]]], np.float32))], f"gg{i}")
        guard = term if guard is None else N("Add", [guard, term], f"guard{i}")
    hang = None
    for i in range(6):
        term = N("Mul", [own[i], C(f"hw{i}", np.array([[[[HANG0[i]]]]], np.float32))], f"hh{i}")
        hang = term if hang is None else N("Add", [hang, term], f"hang{i}")

    def flat64(x, name):
        return N("Reshape", [x, "sh_b64"], name)

    f = N("Reshape", [flat64(own_any, "f64"), "sh_b641"], "f")
    ok = N("Reshape", [flat64(own_k, "ok64"), "sh_b641"], "ok")
    nonk = N("Reshape", [flat64(N("Clip", [N("Sub", [own_any, own_k], "nk0"), C("c0", np.array([0], np.float32)), C("c1", np.array([1], np.float32))], "nonk"), "nk64"), "sh_b641"], "nonkv")
    bf = N("Reshape", [flat64(burn, "bf64"), "sh_b641"], "bf")
    bt = N("Reshape", [flat64(burn, "bto64"), "sh_b164"], "bto")
    u = N("Reshape", [urg, C("sh_b11", np.array([-1, 1, 1], np.int64))], "u3")
    capf = N("Reshape", [flat64(cap_map, "cap64"), "sh_b164"], "capf")
    pol = N("Mul", [f, N("Mul", ["cent64", C("cw", np.array([p["center"]], np.float32))], "cwv")], "pol0")
    pol = N("Add", [pol, N("Mul", [f, capf], "polcap")], "pol1")
    esc = N("Mul", [N("Add", [C("e04", np.array([0.4], np.float32)), u], "e04u"), C("escw", np.array([p["escape"]], np.float32))], "esc")
    pol = N("Add", [pol, N("Mul", [ok, N("Mul", [bf, N("Mul", [N("Sub", [one, bt], "nbt"), esc], "esc2")], "esc3")], "esc4")], "pol2")
    ent = N("Mul", [u, C("entw", np.array([p["enter"]], np.float32))], "ent")
    pol = N("Add", [pol, N("Mul", [ok, N("Mul", [bt, ent], "ent2")], "ent3")], "pol3")
    pol = N("Add", [pol, N("Mul", [nonk, N("Mul", [bf, N("Mul", [N("Sub", [C("one2", np.array([1], np.float32)), bt], "nbt2"),
                                                                           N("Mul", [u, C("e35", np.array([p["escape"] * 0.35], np.float32))], "e35u")], "nk2")], "nk3")], "nk4")], "pol4")
    nk_own = N("Sub", [box(own_k, 1, "boxok"), own_k], "nkown")
    nk_en = N("Sub", [box(enemy_k, 1, "boxek"), enemy_k], "nken")
    pol = N("Add", [pol, N("Mul", [N("Reshape", [flat64(guard, "g64"), "sh_b641"], "gv"),
                                   N("Mul", [N("Reshape", [flat64(nk_own, "no64"), "sh_b164"], "nov"), C("gg", np.array([p["guard"]], np.float32))], "ggv")], "gmul")], "pol5")
    cap_pos = N("Cast", [N("Greater", [cap_map, C("cz", np.zeros((1, 1, 8, 8), np.float32))], "cposb")], "cpos", to=TensorProto.FLOAT)
    nk_pos = N("Cast", [N("Greater", [nk_en, C("nz", np.zeros((1, 1, 8, 8), np.float32))], "nposb")], "npos", to=TensorProto.FLOAT)
    pol = N("Add", [pol, N("Mul", [f, N("Mul", [N("Reshape", [flat64(cap_pos, "cp64"), "sh_b164"], "cpv"),
                                                N("Mul", [N("Reshape", [flat64(nk_pos, "np64"), "sh_b164"], "npv"), C("st", np.array([p["strike"]], np.float32))], "stv")], "stm")], "stm2")], "pol6")
    empty = N("Sub", [C("ones88d", np.ones((1, 1, 8, 8), np.float32)),
                      N("Min", [N("Add", [own_any, enemy_any], "occ"), C("one88d", np.ones((1, 1, 8, 8), np.float32))], "occ1")], "empty")
    hot = N("Mul", [N("Add", [N("Add", [box(enemy[4], 2, "hotice"), box(enemy[1], 1, "hotdae")], "hot1"), nk_en], "hot2"), empty], "hot")
    pol = N("Sub", [pol, N("Mul", [N("Reshape", [flat64(hang, "h64"), "sh_b641"], "hv"),
                                   N("Mul", [N("Reshape", [flat64(hot, "hot64"), "sh_b164"], "hotv"), C("dg", np.array([p["danger"]], np.float32))], "dgv")], "dgm")], "policy3")
    policy = N("Reshape", [pol, "sh_b4096"], "policy")

    g = helper.make_graph(
        nodes, "gurita",
        [helper.make_tensor_value_info("observation", TensorProto.FLOAT, ["batch", 16, 8, 8])],
        [helper.make_tensor_value_info("policy", TensorProto.FLOAT, ["batch", 4096]),
         helper.make_tensor_value_info("value", TensorProto.FLOAT, ["batch"])],
        inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 9
    onnx.checker.check_model(m)
    onnx.save(m, path)
    return path


if __name__ == "__main__":
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("gurita.onnx"))
    build(dest)
    import onnxruntime as ort
    from heuristic import evaluate
    rng = np.random.default_rng(1)
    obs = np.zeros((2, 16, 8, 8), np.float32)
    obs[0, 5, 7, 0] = 1
    obs[0, 4, 6, 1] = 1
    obs[0, 1, 7, 2] = 1
    obs[0, 11, 0, 7] = 1
    obs[0, 10, 1, 6] = 1
    obs[0, 7, 0, 5] = 1
    obs[0, 14] = 0.875
    obs[1, 5, 3, 3] = 1
    obs[1, 11, 4, 4] = 1
    obs[1, 12, 0, :] = 1
    obs[1, 12, :, 0] = 1
    obs[1, 12, 7, :] = 1
    obs[1, 12, :, 7] = 1
    obs[1, 14] = 1
    obs[1, 15] = 1
    lp, lv = evaluate(obs)
    sess = ort.InferenceSession(str(dest), providers=["CPUExecutionProvider"])
    tp, tv = sess.run(None, {"observation": obs})
    print("policy", float(np.max(np.abs(tp - lp))), "value", float(np.max(np.abs(tv - lv))))
    print("ops", sorted({n.op_type for n in onnx.load(str(dest)).graph.node}))
    print("wrote", dest, dest.stat().st_size)
