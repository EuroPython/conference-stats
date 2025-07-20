import json
import requests

# Configuration variables:
# This URL can be a custom URL or pretalx.com/ one depending on the event configuration
CONFERENCE_URL = "https://programme.europython.eu/api/events/europython-2025"
TOKEN = ""  # Not necessary, but in case of private events it's required
YEAR = 2025  # Some events will not have it in the URL so we do it manually


def get_pretalx_submission_types():
    url = f"{CONFERENCE_URL}/submission-types"
    submission_types = {}

    while url:
        try:
            response = requests.get(url, headers={"Authorization": TOKEN})
            data = response.json()

            for stype in data["results"]:
                if stype["id"] not in submission_types:
                    submission_types[stype["id"]] = stype["name"]

            url = data.get("next")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching submission types: {e}")
            return None

    return submission_types


def get_pretalx_submissions(all_speakers):
    url = f"{CONFERENCE_URL}/submissions"
    confirmed_submissions = {}

    submissions_types = get_pretalx_submission_types()

    while url:
        try:
            response = requests.get(url, headers={"Authorization": TOKEN})

            data = response.json()

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

                    for speaker_code in submission["speakers"]:

                        speaker_name = all_speakers[speaker_code]
                        confirmed_submissions[f"{submission_code}-{speaker_code}"] = {
                            "fullname": speaker_name,
                            "title": submission["title"],
                            "type": submission_type,
                        }

            url = data.get("next")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching submissions: {e}")
            return None

    return confirmed_submissions


def get_pretalx_speakers():
    url = f"{CONFERENCE_URL}/speakers"
    speakers = {}

    while url:
        try:
            response = requests.get(url, headers={"Authorization": TOKEN})
            data = response.json()

            for speaker in data["results"]:
                code = speaker["code"]
                if code not in speakers:
                    speakers[code] = speaker["name"]

            url = data.get("next")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching speakers: {e}")
            return None

    return speakers


if __name__ == "__main__":
    speakers = get_pretalx_speakers()

    data = get_pretalx_submissions(speakers)
    d = {}

    if data:

        d["year"] = YEAR
        d["speakers"] = []
        for _, entry in data.items():
            d["speakers"].append(
                {
                    "fullname": entry["fullname"],
                    "type": entry["type"],
                    "title": entry["title"],
                    "level": "",  # TODO: each conference will have this as a custom question
                }
            )

        print(json.dumps(d, indent=4))

    else:
        print("Failed to fetch speakers data")
