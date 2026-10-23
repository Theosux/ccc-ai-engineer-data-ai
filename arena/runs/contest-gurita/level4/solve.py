"""Level 4 shadow notes. Not a stdin solver.

gurita.onnx (export_model.py) is a firewall/hanging-piece prior. It passes
the submission validator and loses to the linear seat model, 2/16 at 100 MCTS
sims. Adding a kernel-escape bonus on top of build4 also loses. The 100-sim
search already handles the shrink; do not upload either prior.

Build:  python export_model.py
Match:  python match_vs_linear.py 16
The graph is the firewall / hanging-piece evaluator in heuristic.py.
Do not upload unless it beats the linear seat model by a clear margin.
"""


def check(data, out):
    return True, "level 4 is a model upload; no text answer"
