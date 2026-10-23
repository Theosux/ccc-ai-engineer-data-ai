"""Linear handcrafted/learnable model.
value  = tanh(flat . W + b)                         W: (1024,)
policy[f*64+t] = sum_p own[p,f] * A[p,t] + sum_q obs[q,t] * Bt[q]   (piece-dest preference + target bonus)"""
import sys, json, numpy as np, onnx
from onnx import helper, TensorProto, numpy_helper

VAL = np.array([15, 45, 25, 30, 50, 0], np.float32)   # ping daemon exploit trace ice kernel
CENT = np.array([[3.5 - max(abs(r - 3.5), abs(c - 3.5)) for c in range(8)] for r in range(8)], np.float32)  # 0.5 edge .. 3.5 centre


def default_params(scale=0.03, center=0.05, kcenter=0.1, pol_center=0.3, cap=0.1):
    W = np.zeros((16, 64), np.float32)
    for p in range(6):
        W[p] = VAL[p] * scale + center * CENT.ravel()
        W[6 + p] = -(VAL[p] * scale + center * CENT.ravel())
    W[5] += kcenter * CENT.ravel()
    W[11] -= kcenter * CENT.ravel()
    A = np.zeros((16, 64), np.float32)
    A[:6] = pol_center * CENT.ravel()
    Bt = np.zeros(16, np.float32)
    Bt[6:12] = cap * VAL
    Bt[11] = 10.0
    return dict(W=W, b=np.zeros(1, np.float32), A=A, Bt=Bt)


def build(path, P):
    W = P["W"].reshape(1024, 1).astype(np.float32)
    inits = [numpy_helper.from_array(W, "W"), numpy_helper.from_array(P["b"].astype(np.float32).reshape(1), "b"),
             numpy_helper.from_array(P["A"].astype(np.float32), "A"),
             numpy_helper.from_array(P["Bt"].astype(np.float32).reshape(1, 16), "Bt"),
             numpy_helper.from_array(np.array([-1], np.int64), "s1"),
             numpy_helper.from_array(np.array([-1, 16, 64], np.int64), "s3"),
             numpy_helper.from_array(np.array([-1, 4096], np.int64), "s4")]
    nodes = [
        helper.make_node("Flatten", ["observation"], ["flat"], axis=1),
        helper.make_node("Gemm", ["flat", "W", "b"], ["v1"]),
        helper.make_node("Tanh", ["v1"], ["v2"]),
        helper.make_node("Reshape", ["v2", "s1"], ["value"]),
        helper.make_node("Reshape", ["observation", "s3"], ["o3"]),          # (B,16,64)
        helper.make_node("Transpose", ["o3"], ["o3t"], perm=[0, 2, 1]),      # (B,64,16)
        helper.make_node("MatMul", ["o3t", "A"], ["pf"]),                    # (B,64from,64to)
        helper.make_node("MatMul", ["Bt", "o3"], ["pt"]),                    # (B,1,64to)
        helper.make_node("Add", ["pf", "pt"], ["pl"]),
        helper.make_node("Reshape", ["pl", "s4"], ["policy"]),
    ]
    g = helper.make_graph(nodes, "colony", [helper.make_tensor_value_info("observation", TensorProto.FLOAT, ["batch", 16, 8, 8])],
                          [helper.make_tensor_value_info("policy", TensorProto.FLOAT, ["batch", 4096]),
                           helper.make_tensor_value_info("value", TensorProto.FLOAT, ["batch"])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 9
    onnx.checker.check_model(m)
    onnx.save(m, path)


if __name__ == "__main__":
    kw = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    build(sys.argv[1], default_params(**kw))
