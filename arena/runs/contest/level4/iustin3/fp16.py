"""Halve an ONNX file: store big float32 initializers as float16 and Cast them back to float32 in the graph.
usage: fp16.py IN.onnx OUT.onnx"""
import sys, numpy as np, onnx
from onnx import helper, numpy_helper, TensorProto

m = onnx.load(sys.argv[1]); g = m.graph
casts, keep = [], []
for init in g.initializer:
    a = numpy_helper.to_array(init)
    if a.dtype == np.float32 and a.size >= 256:
        h = numpy_helper.from_array(a.astype(np.float16), init.name + "_h")
        keep.append(h)
        casts.append(helper.make_node("Cast", [h.name], [init.name], to=TensorProto.FLOAT))
    else:
        keep.append(init)
del g.initializer[:]; g.initializer.extend(keep)
nodes = list(g.node); del g.node[:]; g.node.extend(casts + nodes)
onnx.checker.check_model(m); onnx.save(m, sys.argv[2])
print("saved", sys.argv[2], len(casts), "casts")
