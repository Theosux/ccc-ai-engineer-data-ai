"""Handcrafted policy/value ONNX: value = tanh(w . obs + b), policy = obs_flat @ P (positional bias)."""
import sys, numpy as np, onnx
from onnx import helper, TensorProto, numpy_helper

VAL = {0: 15, 1: 45, 2: 25, 3: 30, 4: 50, 5: 0}   # ping daemon exploit trace ice kernel


def build(path, scale=0.03, center=0.0, kcenter=0.0, pol_center=0.0):
    W = np.zeros((16, 8, 8), np.float32)
    cent = np.array([[3.5 - max(abs(r - 3.5), abs(c - 3.5)) for c in range(8)] for r in range(8)], np.float32)  # 0 edge .. 3 centre
    for p, v in VAL.items():
        W[p] = v * scale + center * cent
        W[6 + p] = -v * scale - center * cent
    W[5] += kcenter * cent
    W[11] -= kcenter * cent
    W = W.reshape(1024, 1)
    C = np.array([[pol_center * cent[t // 8, t % 8] for f in range(64) for t in range(64)]], np.float32)
    inits = [numpy_helper.from_array(W, "W"), numpy_helper.from_array(np.zeros(1, np.float32), "b"),
             numpy_helper.from_array(C, "C"), numpy_helper.from_array(np.zeros((1024, 1), np.float32), "Z"),
             numpy_helper.from_array(np.array([-1], np.int64), "shp")]
    nodes = [
        helper.make_node("Flatten", ["observation"], ["flat"], axis=1),
        helper.make_node("Gemm", ["flat", "W", "b"], ["v1"]),
        helper.make_node("Tanh", ["v1"], ["v2"]),
        helper.make_node("Reshape", ["v2", "shp"], ["value"]),
        helper.make_node("MatMul", ["flat", "Z"], ["z"]),
        helper.make_node("Add", ["z", "C"], ["policy"]),
    ]
    g = helper.make_graph(nodes, "colony", [helper.make_tensor_value_info("observation", TensorProto.FLOAT, ["batch", 16, 8, 8])],
                          [helper.make_tensor_value_info("policy", TensorProto.FLOAT, ["batch", 4096]),
                           helper.make_tensor_value_info("value", TensorProto.FLOAT, ["batch"])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 9
    onnx.checker.check_model(m)
    onnx.save(m, path)


if __name__ == "__main__":
    build(sys.argv[1], *map(float, sys.argv[2:]))
