import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from lib.ml import read_csv, clean_numeric, fmt_space

# Popularity: warmer first; same temperature -> lower humidity; tie -> lower BOP id.
# Trap: numbers written as words ("seventeen") -> clean_numeric.
df = clean_numeric(read_csv())
df = df.sort_values(["temperature", "humidity", "bop"], ascending=[False, True, True])
print(fmt_space(df.bop))
