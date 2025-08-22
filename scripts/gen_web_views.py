# /// script
# dependencies = [
#   "jinja2",
#   "numpy",
#   "pandas",
# ]
# ///

import sys
import jinja2
import json
import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

BASE = Path(__file__).parents[0]
DEST = BASE / ".." / "public"
DATA = BASE / ".." / "data"

environment = Environment(
    loader=FileSystemLoader(str(BASE))
)

out = DEST / "sponsors.html"
base_html = environment.get_template(str(Path("templates") / "base_sponsors.html"))

# Read data
dfs = []
sponsor_dir = DATA / "sponsors"
for datafile in sponsor_dir.glob("**/*.json"):
    data = None
    with open(datafile) as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            print("[ERROR] Failed to parse", datafile)
            sys.exit(1)

    df = pd.DataFrame(data["sponsors"])
    df["level"] = df["level"].apply(lambda x : data["levels"][x] if x in data["levels"] else np.nan)
    df["conference"] = datafile.parents[0].stem
    df["year"] = data["year"]
    dfs.append(df)

sponsors = pd.concat(dfs)
grouped = sponsors.drop(["conference", "year"], axis=1).groupby("name").sum().sort_values("level", ascending=False)

# End read data

context = {
    "title": "Sponsors",
    "description": "Historical data from European Conferences",
    "sponsors": sponsors,
    "grouped": grouped,
}

with open(out, mode="w", encoding="utf-8") as f:
    f.write(base_html.render(context))
