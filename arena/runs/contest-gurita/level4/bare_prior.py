"""Subtract a hard penalty from policy logits in the bare-kernel endgame.

The endgame is decided at the end of the turn: Chebyshev distance <= 2 means
the side that just moved loses. 100-sim search still walks into that ball
(driver match 3980, moves 65-66) because the blunder is the second action of
the turn and the prior likes stepping toward the enemy kernel. The penalty
is zero whenever any non-kernel piece is on the board, so the opening is
unchanged. Capturing the enemy kernel is not penalised.

usage: python3 bare_prior.py in.onnx out.onnx [penalty]
"""
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

HERE = Path(__file__).resolve().parent


def wrap(src, dst, penalty=25.0):
    m = onnx.load(src)
    for node in m.graph.node:
        node.output[:] = ["policy_raw" if o == "policy" else o for o in node.output]
    f = np.float32
    inits = [
        numpy_helper.from_array(np.array([0], np.int64), "bp_p0"),
        numpy_helper.from_array(np.array([12], np.int64), "bp_p1"),
        numpy_helper.from_array(np.array([1], np.int64), "bp_ax1"),
        numpy_helper.from_array(np.array([5], np.int64), "bp_k0"),
        numpy_helper.from_array(np.array([6], np.int64), "bp_k1"),
        numpy_helper.from_array(np.array([11], np.int64), "bp_e0"),
        numpy_helper.from_array(np.array([12], np.int64), "bp_e1"),
        numpy_helper.from_array(np.ones((1, 1, 5, 5), f), "bp_k55"),
        numpy_helper.from_array(np.array([-1, 64, 1], np.int64), "bp_sown"),
        numpy_helper.from_array(np.array([-1, 1, 64], np.int64), "bp_sdng"),
        numpy_helper.from_array(np.array([-1, 4096], np.int64), "bp_s4"),
        numpy_helper.from_array(np.array([1, 2, 3], np.int64), "bp_axes"),
        numpy_helper.from_array(np.array([1], np.int64), "bp_uax"),
        numpy_helper.from_array(np.array(0.0, f), "bp_zero"),
        numpy_helper.from_array(np.array(1.0, f), "bp_one"),
        numpy_helper.from_array(np.array(penalty, f), "bp_pen"),
    ]
    nodes = [
        helper.make_node("Slice", ["observation", "bp_k0", "bp_k1", "bp_ax1"], ["bp_own"], name="bp_slice_own"),
        helper.make_node("Slice", ["observation", "bp_e0", "bp_e1", "bp_ax1"], ["bp_ek"], name="bp_slice_ek"),
        helper.make_node("Slice", ["observation", "bp_p0", "bp_p1", "bp_ax1"], ["bp_pcs"], name="bp_slice_pcs"),
        helper.make_node("ReduceSum", ["bp_pcs", "bp_axes"], ["bp_psum"], keepdims=0, name="bp_psum"),
        helper.make_node("ReduceSum", ["bp_own", "bp_axes"], ["bp_osum"], keepdims=0, name="bp_osum"),
        helper.make_node("ReduceSum", ["bp_ek", "bp_axes"], ["bp_esum"], keepdims=0, name="bp_esum"),
        helper.make_node("Sub", ["bp_psum", "bp_osum"], ["bp_tmp"], name="bp_sub1"),
        helper.make_node("Sub", ["bp_tmp", "bp_esum"], ["bp_cnt"], name="bp_sub2"),
        helper.make_node("Clip", ["bp_cnt", "bp_zero", "bp_one"], ["bp_clipped"], name="bp_clip"),
        helper.make_node("Sub", ["bp_one", "bp_clipped"], ["bp_gate0"], name="bp_gate"),
        helper.make_node("Unsqueeze", ["bp_gate0", "bp_uax"], ["bp_gate"], name="bp_unsq"),
        helper.make_node("Conv", ["bp_ek", "bp_k55"], ["bp_near"], pads=[2, 2, 2, 2], name="bp_conv"),
        helper.make_node("Sub", ["bp_near", "bp_ek"], ["bp_ball"], name="bp_ball"),
        helper.make_node("Relu", ["bp_ball"], ["bp_danger"], name="bp_relu"),
        helper.make_node("Reshape", ["bp_own", "bp_sown"], ["bp_own3"], name="bp_rown"),
        helper.make_node("Reshape", ["bp_danger", "bp_sdng"], ["bp_dng3"], name="bp_rdng"),
        helper.make_node("MatMul", ["bp_own3", "bp_dng3"], ["bp_outer"], name="bp_mm"),
        helper.make_node("Reshape", ["bp_outer", "bp_s4"], ["bp_flat"], name="bp_rflat"),
        helper.make_node("Mul", ["bp_flat", "bp_gate"], ["bp_gated"], name="bp_mulg"),
        helper.make_node("Mul", ["bp_gated", "bp_pen"], ["bp_sub"], name="bp_mulp"),
        helper.make_node("Sub", ["policy_raw", "bp_sub"], ["policy"], name="bp_subp"),
    ]
    m.graph.initializer.extend(inits)
    m.graph.node.extend(nodes)
    onnx.checker.check_model(m)
    onnx.save(m, dst)
    return dst


def _check():
    import onnxruntime as ort
    sys.path.insert(0, str(HERE.parents[1] / "contest" / "level4" / "env4"))
    from colony_one import constants
    from colony_one.board import Board
    from colony_one.env import ColonyOneEnv
    from colony_one.pieces import Piece, PieceType

    src = HERE / "driver_linear.onnx"
    dst = HERE / "gurita_bare.onnx"
    wrap(src, dst)
    lin = ort.InferenceSession(str(src), providers=["CPUExecutionProvider"])
    bare = ort.InferenceSession(str(dst), providers=["CPUExecutionProvider"])

    env = ColonyOneEnv()
    x = env.observation()[None]
    a, b = lin.run(["policy"], {"observation": x})[0], bare.run(["policy"], {"observation": x})[0]
    print("opening max |dpolicy|", float(np.max(np.abs(a - b))))

    board = Board()
    for r in range(8):
        for c in range(8):
            board.grid[r][c] = None
            board.locked[r][c] = False
    board.grid[7][0] = Piece(PieceType.KERNEL, constants.CYAN)
    board.grid[4][3] = Piece(PieceType.KERNEL, constants.MAGENTA)
    env.board = board
    x = env.observation()[None]
    lp = lin.run(["policy"], {"observation": x})[0][0]
    bp = bare.run(["policy"], {"observation": x})[0][0]
    # own kernel is at canonical (7,0) for cyan = square 56
    own = 7 * 8 + 0
    changed = np.where(np.abs(lp - bp) > 1)[0]
    tos = sorted({int(i % 64) for i in changed})
    print("penalised destinations", tos, "n", len(changed), "delta", float((lp - bp).max()))


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        wrap(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 25.0)
        print("wrote", sys.argv[2])
    else:
        _check()
