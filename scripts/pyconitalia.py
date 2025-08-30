import json
import sys
import argparse
from pathlib import Path
from typing import Any, TypedDict

import requests
import logging

logger = logging.getLogger(__name__)


class GraphQLPayload(TypedDict):
    query: str
    variables: dict[str, str]


class GraphQLResponse(TypedDict):
    data: dict[str, dict[str, Any]]
    errors: list[dict[str, Any]] | None


def fetch_graphql_data(query: str, variables: dict[str, str]) -> GraphQLResponse:
    """
    Fetch data from the PyCon Italia GraphQL endpoint.
    """
    headers = {
        "Content-Type": "application/json",
    }

    payload: GraphQLPayload = {
        "query": query,
        "variables": variables,
    }

    try:
        response = requests.post(
            "https://pycon.it/graphql", json=payload, headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        logger.exception("Error fetching data:")
        sys.exit(1)


def get_pycon_sponsors(conference_code: str) -> GraphQLResponse:
    """
    Fetch sponsors data from PyCon Italia GraphQL API.
    """

    query = """
    query GetSponsors($code: String!) {
      conference(code: $code) {
        sponsorsByLevel {
          level
          sponsors {
            name
            link
          }
        }
        sponsorLevels {
          name
          price
        }
        start
      }
    }
    """

    variables = {"code": conference_code}

    return fetch_graphql_data(query, variables)


def get_pycon_speakers(conference_code: str) -> GraphQLResponse:
    """
    Fetch speakers data from PyCon Italia GraphQL API.
    """

    query = """
    query GetSpeakers($code: String!) {
      conference(code: $code) {
        start
        days {
          slots {
            items {
              title
              speakers {
                fullName
              }
              type
            }
          }
        }
      }
    }
    """

    variables = {"code": conference_code}

    return fetch_graphql_data(query, variables)


class Sponsor(TypedDict):
    name: str
    website: str
    level: str


class SponsorsData(TypedDict):
    year: int
    levels: dict[str, int]
    sponsors: list[Sponsor]


class Speaker(TypedDict):
    fullname: str
    type: str
    title: str


class SpeakersData(TypedDict):
    year: int
    speakers: list[Speaker]


def format_sponsors_data(raw_data: GraphQLResponse) -> SponsorsData:
    """
    Format the raw GraphQL response into a structured format.
    """
    if "errors" in raw_data and raw_data["errors"]:
        raise ValueError(f"GraphQL errors: {raw_data['errors']}")

    conference_data = raw_data["data"]["conference"]
    sponsors_by_level = conference_data["sponsorsByLevel"]
    sponsor_levels = conference_data["sponsorLevels"]
    start_date = conference_data["start"]

    # Extract year from start date
    year = int(start_date.split("-")[0])

    # Create levels dictionary
    levels_dict: dict[str, int] = {}
    for level_data in sponsor_levels:
        name = level_data["name"]
        price_str = level_data["price"]
        # Convert price string to integer (e.g., "15000.00" -> 15000)
        try:
            price = int(float(price_str))
        except (ValueError, TypeError):
            price = 0  # fallback for invalid prices
        levels_dict[name] = price

    # Create sponsors list in the format you specified
    sponsors_list: list[Sponsor] = []
    for level_data in sponsors_by_level:
        level = level_data["level"]
        sponsors = level_data["sponsors"]

        for sponsor in sponsors:
            sponsors_list.append(
                {"name": sponsor["name"], "website": sponsor["link"], "level": level}
            )

    return {"year": year, "levels": levels_dict, "sponsors": sponsors_list}


def format_speakers_data(raw_data: GraphQLResponse) -> SpeakersData:
    """
    Format the raw GraphQL response into a structured speakers format.
    """
    if "errors" in raw_data and raw_data["errors"]:
        raise ValueError(f"GraphQL errors: {raw_data['errors']}")

    conference_data = raw_data["data"]["conference"]
    days = conference_data["days"]
    start_date = conference_data["start"]

    # Create speakers list
    speakers_list: list[Speaker] = []
    
    # Track processed items to avoid duplicates
    
    # Extract year from start date
    year = int(start_date.split("-")[0])
    
    for day in days:
        for slot in day["slots"]:
            for item in slot["items"]:
                # Only process training, talk, and keynote items
                if item["type"] not in ["training", "talk", "keynote"]:
                    continue
                
                title = item["title"]
                item_type = item["type"]
                speakers = item["speakers"]
                
                # If no speakers, skip this item
                if not speakers:
                    continue
                
                # Add one entry per speaker
                for speaker in speakers:
                    speakers_list.append({
                        "fullname": speaker["fullName"],
                        "type": item_type.title(),  # Capitalize first letter
                        "title": title
                    })

    return {"year": year, "speakers": speakers_list}


def save_to_json(data: SponsorsData | SpeakersData, output_file: Path) -> None:
    """
    Save data to a JSON file.
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info("Data saved to: %s", output_file)
    except IOError as e:
        logger.error("Error saving file: %s", e)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch data from PyCon Italia GraphQL API"
    )
    parser.add_argument(
        "--conference-code", required=True, help="Conference code (e.g., pycon12)"
    )
    args = parser.parse_args()

    logger.info(
        "Fetching data for conference: %s", args.conference_code
    )

    raw_data = get_pycon_speakers(args.conference_code)
    formatted_data = format_speakers_data(raw_data)
    output_path = Path("data/speakers/PyConItalia") / f"{formatted_data['year']}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_to_json(formatted_data, output_path)

    raw_data = get_pycon_sponsors(args.conference_code)
    formatted_data = format_sponsors_data(raw_data)
    output_path = Path("data/sponsors/PyConItalia") / f"{formatted_data['year']}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_to_json(formatted_data, output_path)

    if not raw_data:
        logger.error("No data received from the API")
        sys.exit(1)
    


if __name__ == "__main__":
    main()
