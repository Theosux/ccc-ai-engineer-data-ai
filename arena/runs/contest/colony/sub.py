import sys, pathlib, json, capi, ccc
lvl, fid, text = int(sys.argv[1]), sys.argv[2], sys.argv[3]
d = pathlib.Path(__file__).resolve().parent.parent / f"level{lvl}" / "out"; d.mkdir(parents=True, exist_ok=True)
p = d / f"{fid}.txt"; p.write_text(text.replace("\\n", "\n"))
print(ccc.submit_one(ccc.active_run(), lvl, fid, p))
