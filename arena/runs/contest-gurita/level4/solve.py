"""Level 4 shadow notes. Not a stdin solver.

gurita.onnx (export_model.py) is a firewall/hanging-piece prior. It passes
the submission validator and loses to the linear seat model, 2/16 at 100 MCTS
sims. Adding a kernel-escape bonus on top of build4 also loses. The 100-sim
search already handles the shrink; do not upload either prior.

Build:  python export_model.py
Match:  python match_vs_linear.py 16
The graph is the firewall / hanging-piece evaluator in heuristic.py.
Do not upload unless it beats the linear seat model by a clear margin.

Later checks, also not uploads: stitching a better value onto the linear
policy loses (outcome value 6/16 at 80 sims, search-Q value 7/32 at 100).
A hard penalty on bare-kernel steps into Chebyshev 2 does not change
100-sim play. The seat to beat is the driver's conv net, not v1.
"""


def check(data, out):
    return True, "level 4 is a model upload; no text answer"
