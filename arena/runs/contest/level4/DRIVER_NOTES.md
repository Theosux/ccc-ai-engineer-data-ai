- 16:17:29 L4 tournament: seat holds v1.onnx (level4/env4/build4.py linear model, beats L3 model 32/40). Upload = colony/upload4.py model.onnx (POST /colony-api/model-upload). Training AlphaZero-lite: env4/selfplay.py + net.py (torch). Teammate: ideas welcome via note, do NOT upload.
- 17:02:59 L4: AlphaZero-lite loop working. n1 (48x4 conv, trained on linear-model selfplay) beat linear 95/100, rating 1865 rank 6 at 13:51 UTC. n2 beat n1 87/100; n2b (64x6) beat n2 66/100, uploaded ~13:56. Loop: env4/selfplay.py -> net.py (MPS) -> match.py -> colony/upload4.py.
- 19:07:27 L4 seat n10b (96x6) since 16:07 UTC; chain n8b (71% vs n7c) -> n9b (66.7%) -> n10b (69%). Cloud data gc1..gc4 + second Mac + strategy session feed env4/data.
- 19:46 RO (16:46 UTC, iustin / autopilot-speed-update): FINAL DECISION: the seat stays **n11c** (uploaded 19:19 by the
  driver, 107/150 = 71% vs n10b, MAGENTA 56/75). Every remaining candidate was gated vs n11c on Modal (152 games each, both
  colours): n13b 78, n13a 77, n13c 75, n13d 71 (H100 fine-tunes of n11c/n12h), n12h 79, n12i 76, n12j 75, n12g 68,
  soups s2 81 / s1 69, n11b 51, n10b 43. None reached 60%, so no new model was uploaded.
  The user ran a same-model re-upload test (n11c only, about every 35 s from 19:29 to 19:45, about 20 uploads): it did not
  raise the game rate (about 0.7 to 0.8 games/min either way) but made the rating swing hard (2242 -> 1897 -> 2178 -> 1970
  -> 2143). Last upload 19:45:00; nothing after that. Gate log: level4/iustin2/tlogs/final_gates.txt.
