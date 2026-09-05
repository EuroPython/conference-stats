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
    "talk (long)": "Talk",
    "talk (15 mins + q&a)": "Talk",
    "talk (25 mins + q&a)": "Talk",
    "talk (30min + 5min q&a)": "Talk",
    "talk (30min + 5min questions & answers)": "Talk",
    "talk (35min + 5min questions & answers)": "Talk",
    "charla": "Talk",
    "guest talk": "Talk",
    "invited talk": "Talk",
    "lightning talks": "Talk",
    "lightning talk session": "Talk",
    "main stage event": "Talk",
    "lecture room event": "Talk",
    "maintainer track": "Talk",
    "maintainer track long": "Talk",
    "sponsored": "Sponsored",
    "sponsored talk": "Sponsored",
    "sponsored talk (long)": "Sponsored",
    "sponsored talk (keystone)": "Sponsored",
    "sponsor (diamond)": "Sponsored",
    "tutorial": "Workshop",
    "tutorial (1,5 hours)": "Workshop",
    "conference workshop": "Workshop",
    "special workshop": "Workshop",
    "free workshop": "Workshop",
    "workshop": "Workshop",
    "workshop (long)": "Workshop",
    "workshop (short)": "Workshop",
    "workshop (90min)": "Workshop",
    "workshop (90min + 10min presentation/final discussion)": "Workshop",
    "kids workshop": "Workshop",
    "young coders event": "Workshop",
    "classroom event": "Workshop",
    "interactive workshop or collaborative session": "Workshop",
    "panel": "Panel",
    "panel [in-person & remote]": "Panel",
    "panels": "Panel",
    "round table event": "Panel",
    "keynote": "Keynote",
    "poster": "Poster",
    "poster session": "Poster",
    "summit": "Summit",
    "mentored sprints": "Mentored Sprints",
    "documentary and q&a": "Documentary and Q&A",
    "announcements": "Announcements",
    "open space": "Open Space",
    "other": "Other",
    "something else": "Other",
    # One-off session formats specific to a single conference/year that don't
    # cleanly match any of the canonical categories above; left as-is rather
    # than forced into a bad fit.
    "assambly": "Assambly",
    "freestyle": "Freestyle",
    "freestyle template": "Freestyle Template",
    "talk template": "Talk Template",
    "organization": "Organization",
}


def normalize_type(raw_type):
    if not raw_type:
        return "Other"
    canonical = TYPE_ALIASES.get(raw_type.strip().lower())
    if canonical is None:
        print(f"[WARN] Unrecognized speaker type {raw_type!r}, add it to TYPE_ALIASES", file=sys.stderr)
        return raw_type.strip()
    return canonical


# Data directories are named per-conference, but casing has drifted between the
# sponsors/ and speakers/ trees for the same event (e.g. "pyladiescon" vs
# "PyLadiesCon"). Map every raw folder name we've seen onto one canonical
# display name so the "Included Conferences" overview merges them into a
# single row instead of listing the same conference twice.
CONFERENCE_ALIASES = {
    "pyladiescon": "PyLadiesCon",
}


def normalize_conference(raw_name):
    return CONFERENCE_ALIASES.get(raw_name.lower(), raw_name)


# Sponsorship amounts are recorded in whatever currency the conference itself
# published (see the optional "currency" field on each sponsors/*.json file;
# it defaults to EUR when absent, which covers the vast majority of files).
# These are static, approximate rates - not looked up live - so that
# regenerating the site later doesn't change historical totals depending on
# the exchange rate of the day. Good enough given the amounts themselves are
# already estimates (see the disclaimer on the sponsors page).
FX_TO_EUR = {
    "EUR": 1.0,
    "CZK": 0.040,
    "PLN": 0.23,
    "SEK": 0.088,
}


def parse_amount(value, currency="EUR"):
    """Sponsorship levels are sometimes recorded as numeric strings (e.g. "29000")
    or as non-monetary labels (e.g. "Unknown", "custom"); only the former convert.
    Non-EUR amounts are converted to EUR using a static approximate rate so
    they can be meaningfully compared/summed across conferences."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return np.nan
    rate = FX_TO_EUR.get(currency)
    if rate is None:
        print(f"[WARN] Unknown currency {currency!r}, treating amount as EUR", file=sys.stderr)
        rate = 1.0
    return amount * rate


def build_sponsors_context():
    dfs = []
    for datafile in sorted((DATA / "sponsors").glob("**/*.json")):
        data = read_json(datafile)
        currency = data.get("currency", "EUR")
        df = pd.DataFrame(data["sponsors"])
        df["amount"] = df["level"].apply(lambda x: parse_amount(data["levels"].get(x, np.nan), currency))
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


def format_years(years):
    """Render a sorted list of years as a plain comma-separated list, e.g.
    [2017,2018,2019,2022] -> "2017, 2018, 2019, 2022"."""
    return ", ".join(str(year) for year in years)


def collect_conferences():
    """List every conference found in data/, with the years we have sponsors
    and/or speakers data for, one row per conference for the homepage overview."""
    sponsor_years = {}
    speaker_years = {}
    for years_by_conference, root in (
        (sponsor_years, DATA / "sponsors"),
        (speaker_years, DATA / "speakers"),
    ):
        for datafile in root.glob("*/*.json"):
            name = normalize_conference(datafile.parents[0].stem)
            years_by_conference.setdefault(name, set()).add(int(datafile.stem))

    names = sorted(set(sponsor_years) | set(speaker_years))
    conferences = [
        {
            "conference": name,
            "sponsor_years": format_years(sorted(sponsor_years.get(name, []))),
            "speaker_years": format_years(sorted(speaker_years.get(name, []))),
        }
        for name in names
    ]
    return conferences


def render(template_name, out_name, context):
    template = environment.get_template(str(Path("templates") / template_name))
    out = DEST / out_name
    with open(out, mode="w", encoding="utf-8") as f:
        f.write(template.render(context))


def build_index_context():
    return {
        "title": "Welcome",
        "description": "Historical sponsor and speaker data from European Python conferences",
        "active": "home",
        "repo_url": "https://github.com/europython/conference-stats",
        "conferences": collect_conferences(),
    }


render("base_sponsors.html", "sponsors.html", build_sponsors_context())
render("base_speakers.html", "speakers.html", build_speakers_context())
# GitHub Pages has no directory listing/auto-index, so `/` 404s without this.
render("base_index.html", "index.html", build_index_context())
