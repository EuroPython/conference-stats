f# Conference Stats

The goal of this repository is to gather the public conference information
from the many Python events we have in Europe, so new ones can have a good
understanding of who to contact for future events for sponsorship possibilities
but also for speaking opportunities.

The data will also highlight the companies/organizations that are helping the
most in Python conferences, similarly to the most active speakers.

> **Have an idea?** If you believe more data can be added, or new insights can
> be extracted, please open an Issue!

# List of Conferences

* EuroPython: 2025
* PyCon Italy:
* PyCon Greece:

# How to contribute?

For each missing conference in the JSON file, find the information by visiting official 
websites, archives, and past event pages. For each year, document the sponsorship tiers 
and costs in a `levels` object (e.g., `"Gold": 10000`), then create an array under that 
year listing all sponsors with their name, website, and sponsorship level. Find this 
information from conference websites, sponsor pages, event programs (often PDFs), social 
media posts, and press releases. Ensure accuracy of sponsor names and URLs, verify 
sponsorship levels match the documented tiers for that specific year, and maintain 
consistent formatting as shown in the existing `sponsors.json` structure.

Remember to submit a Pull Request with the information and adding the
conference and year to this README.

**Not enough time?**
You can open new issues by providing a URL for the conference,
sponsorship packages details and list of sponsors, so others can extract
the information. This would be helpful as well!
