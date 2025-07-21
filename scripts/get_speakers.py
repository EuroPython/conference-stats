import json
import sys
import argparse
from typing import Any
from datetime import datetime

import requests


def get_response_data_from_url(url: str) -> dict[str, Any]:
    try:
        response = requests.get(url, headers={"Authorization": TOKEN})
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    return data


def get_pretalx_submission_types(conference_url: str) -> dict[str, str]:
    url: str | None = f"{conference_url}/submission-types"
    submission_types: dict[str, str] = {}

    while url:
        data: dict[str, Any] = get_response_data_from_url(url)

        for stype in data["results"]:
            if stype["id"] not in submission_types:
                submission_types[stype["id"]] = stype["name"]

        url = data.get("next")

    return submission_types


def get_pretalx_submissions(conference_url: str, all_speakers: dict[str, str]) -> dict[str, dict]:
    url: str | None = f"{conference_url}/submissions"
    confirmed_submissions = {}

    submissions_types = get_pretalx_submission_types(conference_url)

    while url:
        data: dict[str, Any] = get_response_data_from_url(url)

        for submission in data["results"]:

            if submission["state"] == "confirmed":

                submission_code = submission["code"]
                submission_speakers = submission["speakers"]
                submission_type = submissions_types[submission["submission_type"]]
                if isinstance(submission_type, dict):
                    try:
                        # Search for 'en' default language
                        # otherwise, the first one
                        submission_type = submission_type["en"]
                    except KeyError:
                        for k, v in submission_type.items():
                            submission_type = v
                            break

                for speaker_code in submission_speakers:

                    speaker_name = all_speakers[speaker_code]
                    confirmed_submissions[f"{submission_code}-{speaker_code}"] = {
                        "fullname": speaker_name,
                        "title": submission["title"],
                        "type": submission_type,
                    }

        url = data.get("next")

    return confirmed_submissions


def get_pretalx_speakers(conference_url: str) -> dict[str, str]:
    url: str | None = f"{conference_url}/speakers"
    speakers = {}

    while url:
        data: dict[str, Any] = get_response_data_from_url(url)

        for speaker in data["results"]:
            code = speaker["code"]
            if code not in speakers:
                speakers[code] = speaker["name"]

        url = data.get("next")

    return speakers


def get_event_year(conference_url: str) -> int:
    data: dict[str, Any] = get_response_data_from_url(conference_url)
    date = data["date_from"]
    year: int = 2025
    try:
        date_from = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: couldn't parse date '{date}'. Falling back to 2025")
        return year

    return date_from.year


if __name__ == "__main__":
    # This URL can be a custom URL or pretalx.com/ one depending on the event configuration
    CONFERENCE_URL = ""
    TOKEN = ""  # Not necessary, but in case of private events it's required

    parser = argparse.ArgumentParser()
    parser.add_argument('--url')
    parser.add_argument('--output')
    args = parser.parse_args()

    # Check command-line arguments
    if args.url is not None:
        if CONFERENCE_URL:
            print(f"-- WARNING: Overriding url '{CONFERENCE_URL}' "
                  f"with command line value '{args.url}'")
        print(f"-- Using event url: '{args.url}'")
        CONFERENCE_URL = args.url

    if args.output is not None:
        if not args.output.endswith(".json"):
            print(f"ERROR: file '{args.output}' is not a JSON file")
            sys.exit(1)

    year = get_event_year(CONFERENCE_URL)
    speakers = get_pretalx_speakers(CONFERENCE_URL)
    submission_data = get_pretalx_submissions(CONFERENCE_URL, speakers)

    data: dict[str, Any] = {}

    if submission_data:

        data["year"] = year
        data["speakers"] = []
        for _, entry in submission_data.items():
            data["speakers"].append(
                {
                    "fullname": entry["fullname"],
                    "type": entry["type"],
                    "title": entry["title"],
                }
            )

        if args.output is not None:
            with open(args.output, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"-- Written file: '{args.output}'")
        else:
            print(json.dumps(data, indent=4))
    else:
        print("Failed to fetch speakers data")
