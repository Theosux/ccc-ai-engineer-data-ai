"""Level 4 shadow model. Not a stdin solver: the deliverable is gurita.onnx.

Build:  python export_model.py
Match:  python match_vs_linear.py 16
The graph is the firewall / hanging-piece evaluator in heuristic.py.
Do not upload unless it beats the linear seat model by a clear margin.
"""


def check(data, out):
    return True, "level 4 is a model upload; no text answer"
