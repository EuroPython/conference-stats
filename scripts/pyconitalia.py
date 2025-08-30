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


class Sponsor(TypedDict):
    name: str
    website: str
    level: str


class SponsorsData(TypedDict):
    year: int
    levels: dict[str, int]
    sponsors: list[Sponsor]


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


def save_to_json(data: SponsorsData, output_file: Path) -> None:
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
        description="Fetch sponsors data from PyCon Italia GraphQL API"
    )
    parser.add_argument(
        "--conference-code", required=True, help="Conference code (e.g., pycon12)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output JSON file path (optional, defaults to "
            "data/sponsors/PyConIt/{year}.json)"
        ),
    )

    args = parser.parse_args()

    logger.info("Fetching sponsors data for conference: %s", args.conference_code)

    # Fetch raw data from GraphQL API
    raw_data = get_pycon_sponsors(args.conference_code)

    if not raw_data:
        logger.error("No data received from the API")
        sys.exit(1)

    # Format the data
    formatted_data = format_sponsors_data(raw_data)

    # Output or save data
    output_path = (
        args.output
        if args.output
        else (Path("data/sponsors/PyConItalia") / f"{formatted_data['year']}.json")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_to_json(formatted_data, output_path)


if __name__ == "__main__":
    main()
