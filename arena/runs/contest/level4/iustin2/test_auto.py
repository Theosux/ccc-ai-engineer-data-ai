"""Smoke test for autoloop's gate pieces (no upload). usage (cwd env4): .venv/bin/python ../iustin2/test_auto.py"""
import sys, time
sys.path.insert(0, "../iustin2")
import autoloop as A

if __name__ == "__main__":
    t = time.time(); print("arch", A.arch(A.ENV / "n2b.pt"), A.arch(A.ENV / "n2.pt"))
    print("validate", A.validate(A.ENV / "n2b.onnx"), f"{time.time() - t:.0f}s", flush=True)
    t = time.time(); print("match n2b vs n2 (10)", A.match(A.ENV / "n2b.onnx", A.ENV / "n2.onnx", 10), f"{time.time() - t:.0f}s", flush=True)
    t = time.time(); print("greedy n2b (1/colour)", A.greedy(A.ENV / "n2b.onnx", 1), f"{time.time() - t:.0f}s", flush=True)
    print("datasets", [d.split("/")[-1] for d in A.datasets()[:4]])
    print("driver alive", A.driver_alive())
