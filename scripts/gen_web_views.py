# /// script
# dependencies = [
#   "jinja2",
#   "numpy",
#   "pandas",
# ]
# ///

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parents[0]
DEST = BASE / ".." / "public"
DATA = BASE / ".." / "data"

environment = Environment(loader=FileSystemLoader(str(BASE)))


def escape_for_script_tag(json_text):
    """Prevent a literal `</script>` inside the JSON payload from closing the tag early."""
    return json_text.replace("</", "<\\/")


def read_json(path):
    """Read a JSON file, tolerating files that were saved with a non-UTF-8 encoding."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        print(f"[WARN] {path} is not valid UTF-8, falling back to latin-1", file=sys.stderr)
        text = raw.decode("latin-1")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("[ERROR] Failed to parse", path)
        sys.exit(1)


# Conference programs use inconsistent labels for the same session format
# (casing varies by year, and some events split out "long session" or
# "in-person & remote" variants). Map every raw label we've seen onto a
# small canonical set so the speakers page can offer a clean type filter.
TYPE_ALIASES = {
    "talk": "Talk",
    "talk (long session)": "Talk",
    "sponsored": "Sponsored",
    "sponsored talk": "Sponsored",
    "tutorial": "Workshop",
    "conference workshop": "Workshop",
    "special workshop": "Workshop",
    "free workshop": "Workshop",
    "panel": "Panel",
    "panel [in-person & remote]": "Panel",
    "keynote": "Keynote",
    "poster": "Poster",
    "summit": "Summit",
    "mentored sprints": "Mentored Sprints",
    "documentary and q&a": "Documentary and Q&A",
    "announcements": "Announcements",
    "open space": "Open Space",
}


def normalize_type(raw_type):
    if not raw_type:
        return "Other"
    canonical = TYPE_ALIASES.get(raw_type.strip().lower())
    if canonical is None:
        print(f"[WARN] Unrecognized speaker type {raw_type!r}, add it to TYPE_ALIASES", file=sys.stderr)
        return raw_type.strip()
    return canonical


def parse_amount(value):
    """Sponsorship levels are sometimes recorded as numeric strings (e.g. "29000")
    or as non-monetary labels (e.g. "Unknown", "custom"); only the former convert."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def build_sponsors_context():
    dfs = []
    for datafile in sorted((DATA / "sponsors").glob("**/*.json")):
        data = read_json(datafile)
        df = pd.DataFrame(data["sponsors"])
        df["amount"] = df["level"].apply(lambda x: parse_amount(data["levels"].get(x, np.nan)))
        df["conference"] = datafile.parents[0].stem
        df["year"] = int(datafile.stem)
        dfs.append(df)

    sponsors = pd.concat(dfs, ignore_index=True)

    grouped = (
        sponsors.groupby("name")
        .agg(total=("amount", "sum"), website=("website", "first"))
        .reset_index()
        .sort_values("total", ascending=False)
    )

    all_sponsors = sponsors[["year", "conference", "name", "website", "amount"]].sort_values(
        ["year", "conference", "amount"], ascending=[False, True, False]
    )

    return {
        "title": "Sponsors",
        "description": "Historical data from European Conferences",
        "active": "sponsors",
        "grouped_json": escape_for_script_tag(grouped.to_json(orient="records")),
        "all_json": escape_for_script_tag(all_sponsors.to_json(orient="records")),
    }


def build_speakers_context():
    rows = []
    for datafile in sorted((DATA / "speakers").glob("**/*.json")):
        data = read_json(datafile)
        conference = datafile.parents[0].stem
        year = int(datafile.stem)
        for speaker in data["speakers"]:
            rows.append(
                {
                    "year": year,
                    "conference": conference,
                    "fullname": speaker.get("fullname"),
                    "type": normalize_type(speaker.get("type")),
                    "title": speaker.get("title"),
                    "url": speaker.get("url"),
                }
            )

    speaker_types = sorted({row["type"] for row in rows})

    return {
        "title": "Speakers",
        "description": "Historical speaker data from European Conferences",
        "active": "speakers",
        "speaker_types": speaker_types,
        "speakers_json": escape_for_script_tag(json.dumps(rows, ensure_ascii=False)),
    }


def render(template_name, out_name, context):
    template = environment.get_template(str(Path("templates") / template_name))
    out = DEST / out_name
    with open(out, mode="w", encoding="utf-8") as f:
        f.write(template.render(context))


render("base_sponsors.html", "sponsors.html", build_sponsors_context())
render("base_speakers.html", "speakers.html", build_speakers_context())
