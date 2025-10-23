import json

from collections.abc import Generator
from typing import Any

import requests

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

import os

SERP_API_URL = "https://serpapi.com/search"


def get_file_path(filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


# Load valid country codes from google-countries.json
def load_valid_countries(filename: str) -> set:
    with open(filename) as file:
        countries = json.load(file)
        return {country['country_code'] for country in countries}


# Load valid language codes from google-languages.json
def load_valid_languages(filename: str) -> set:
    with open(filename) as file:
        languages = json.load(file)
        return {language['language_code'] for language in languages}


VALID_COUNTRIES = load_valid_countries(get_file_path("google-countries.json"))
VALID_LANGUAGES = load_valid_languages(get_file_path("google-languages.json"))


class GoogleScholarSearchTool(Tool):
    def _parse_response(self, response: dict) -> dict:
        result = {}
        if "organic_results" in response:
            result["organic_results"] = [
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "publication_info": {
                        "summary": item.get("publication_info", {}).get("summary", ""),
                        "authors": [
                            {
                                **{"name": author.get("name", "")},
                                **({"author_id": author["author_id"]} if "author_id" in author else {})
                            }
                            for author in item.get("publication_info", {}).get("authors", [])
                        ]
                    },
                    "resources": item.get("resources", []),
                    "cited_count": item.get("inline_links", {}).get("cited_by", {}).get("total",""),
                }
                for item in response["organic_results"]
            ]
        return result

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        hl = tool_parameters.get("hl", "en")
        gl = tool_parameters.get("gl", "us")
        as_ylo = tool_parameters.get("as_ylo", "")
        as_yhi = tool_parameters.get("as_yhi", "")

        # Validate 'hl' (language) code
        if hl not in VALID_LANGUAGES:
            yield self.create_text_message(
                f"Invalid 'hl' parameter: {hl}. Please refer to https://serpapi.com/google-languages for a list of valid language codes.")

        # Validate 'gl' (country) code
        if gl not in VALID_COUNTRIES:
            yield self.create_text_message(
                f"Invalid 'gl' parameter: {gl}. Please refer to https://serpapi.com/google-countries for a list of valid country codes.")

        params = {
            "api_key": self.runtime.credentials["serpapi_api_key"],
            "q": tool_parameters["query"],
            "engine": "google_scholar",
            "gl": gl,
            "hl": hl
        }
        if as_ylo:
            if not as_ylo.isdigit():
                yield self.create_text_message(
                "'as_ylo' should be a numeric year (e.g., 2024).")
            params["as_ylo"] = as_ylo
        if as_yhi:
            if not as_ylo.isdigit():
                yield self.create_text_message(
                "'as_yhi' should be a numeric year (e.g., 2024).")
            params["as_yhi"] = as_yhi
        try:
            response = requests.get(url=SERP_API_URL, params=params)
            response.raise_for_status()
            valuable_res = self._parse_response(response.json())
            yield self.create_json_message(valuable_res)
        except requests.exceptions.RequestException as e:
            yield self.create_text_message(
                f"An error occurred while invoking the tool: {str(e)}. Please refer to https://serpapi.com/locations-api for the list of valid locations.")
