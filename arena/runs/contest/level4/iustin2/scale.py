"""Wrap a model: policy *= alpha, value = tanh(beta * atanh(value)) (beta=1 -> unchanged).
usage: scale.py in.onnx out.onnx alpha beta"""
import sys
import numpy as np, onnx
from onnx import helper, numpy_helper

src, dst, alpha, beta = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
m = onnx.load(src)
g = m.graph
for node in g.node:
    node.output[:] = [{"policy": "policy_raw", "value": "value_raw"}.get(o, o) for o in node.output]
g.initializer.extend([numpy_helper.from_array(np.array(alpha, np.float32), "alpha_s"),
                      numpy_helper.from_array(np.array(beta, np.float32), "beta_s"),
                      numpy_helper.from_array(np.array(0.999, np.float32), "clip_s"),
                      numpy_helper.from_array(np.array(-0.999, np.float32), "nclip_s"),
                      numpy_helper.from_array(np.array(1.0, np.float32), "one_s"),
                      numpy_helper.from_array(np.array(0.5, np.float32), "half_s")])
nodes = [helper.make_node("Mul", ["policy_raw", "alpha_s"], ["policy"])]
if beta == 1.0:
    nodes.append(helper.make_node("Identity", ["value_raw"], ["value"]))
else:  # atanh(x) = 0.5 * log((1+x)/(1-x))
    nodes += [helper.make_node("Clip", ["value_raw", "nclip_s", "clip_s"], ["vc"]),
              helper.make_node("Add", ["one_s", "vc"], ["vp"]), helper.make_node("Sub", ["one_s", "vc"], ["vm"]),
              helper.make_node("Div", ["vp", "vm"], ["vr"]), helper.make_node("Log", ["vr"], ["vl"]),
              helper.make_node("Mul", ["vl", "half_s"], ["va"]), helper.make_node("Mul", ["va", "beta_s"], ["vb"]),
              helper.make_node("Tanh", ["vb"], ["value"])]
g.node.extend(nodes)
onnx.checker.check_model(m)
onnx.save(m, dst)
print("wrote", dst)
