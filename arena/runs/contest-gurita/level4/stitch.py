"""Linear policy (exact seat prior) plus the conv net's value head.

One-shot nets lose because their policy is a blurry copy of a prior the
referee MCTS barely leaves. Keeping the linear logits and swapping only the
value is the change that can still move search.
"""
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

HERE = Path(__file__).resolve().parent
ENV = HERE.parents[1] / "contest" / "level4" / "env4"


def _prefix(model, prefix):
    def ren(name):
        if not name or name == "observation":
            return name
        return prefix + name

    for init in model.graph.initializer:
        init.name = ren(init.name)
    for vi in list(model.graph.value_info) + list(model.graph.output):
        vi.name = ren(vi.name)
    for i, node in enumerate(model.graph.node):
        node.name = f"{prefix}{i}_{node.op_type}"
        node.input[:] = [ren(x) for x in node.input]
        node.output[:] = [ren(x) for x in node.output]
    return model


def stitch(scale=1.0, mix_linear=0.0, out=None, net_path=None):
    """policy = linear. value = scale * ((1-mix)*net + mix*linear)."""
    lin = _prefix(onnx.load(HERE / "driver_linear.onnx"), "L")
    net = _prefix(onnx.load(net_path or (HERE / "gurita_net.onnx")), "N")
    nodes = list(lin.graph.node) + list(net.graph.node)
    inits = list(lin.graph.initializer) + list(net.graph.initializer)
    # Lvalue, Nvalue, Lpolicy
    inits.append(numpy_helper.from_array(np.array(scale * (1.0 - mix_linear), np.float32), "wn"))
    inits.append(numpy_helper.from_array(np.array(scale * mix_linear, np.float32), "wl"))
    nodes.append(helper.make_node("Mul", ["Nvalue", "wn"], ["vn"]))
    nodes.append(helper.make_node("Mul", ["Lvalue", "wl"], ["vl"]))
    nodes.append(helper.make_node("Add", ["vn", "vl"], ["value"]))
    nodes.append(helper.make_node("Identity", ["Lpolicy"], ["policy"]))
    g = helper.make_graph(
        nodes,
        "stitch",
        [helper.make_tensor_value_info("observation", TensorProto.FLOAT, ["batch", 16, 8, 8])],
        [
            helper.make_tensor_value_info("policy", TensorProto.FLOAT, ["batch", 4096]),
            helper.make_tensor_value_info("value", TensorProto.FLOAT, ["batch"]),
        ],
        inits,
    )
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 9
    onnx.checker.check_model(m)
    out = Path(out or HERE / "gurita_stitch.onnx")
    onnx.save(m, out)
    return out


def value_stats():
    import onnxruntime as ort
    d = np.load(HERE / "distill.npz")
    x = d["P"].astype(np.float32)
    z = d["Z"].astype(np.float32)
    sess = ort.InferenceSession(str(HERE / "gurita_net.onnx"), providers=["CPUExecutionProvider"])
    # batch in chunks
    vs = []
    for i in range(0, len(x), 256):
        v = sess.run(["value"], {"observation": x[i:i + 256]})[0]
        vs.append(v)
    v = np.concatenate(vs)
    acc = ((v > 0) == (z > 0)).mean()
    print(f"net value sign {acc:.3f} |v| {np.abs(v).mean():.3f} corr {np.corrcoef(v, z)[0,1]:.3f} n {len(z)}")


if __name__ == "__main__":
    value_stats()
    p = stitch(scale=float(sys.argv[1]) if len(sys.argv) > 1 else 1.0,
               mix_linear=float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
    print("wrote", p, p.stat().st_size)
