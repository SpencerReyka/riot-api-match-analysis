import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


class RiotAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RiotAccountData:
    puuid: str
    game_name: str
    tag_line: str


class RiotClient:
    def __init__(
        self,
        api_key: str,
        *,
        routing_region: str = "americas",
        platform_region: str = "na1",
        session: requests.Session | None = None,
        sleep=time.sleep,
        timeout: tuple[float, float] = (3.05, 15),
        max_retries: int = 2,
    ):
        if not api_key:
            raise RiotAPIError("Riot API key is not configured.")
        self.routing_region = routing_region
        self.platform_region = platform_region
        self.session = session or requests.Session()
        self.session.headers.update(
            {"X-Riot-Token": api_key, "User-Agent": "SpencerRiotAnalysis/2.0"}
        )
        self.sleep = sleep
        self.timeout = timeout
        self.max_retries = max_retries

    def _request(self, url: str) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RiotAPIError("Riot API could not be reached.") from exc
                self.sleep(2**attempt)
                continue

            if response.status_code == 429:
                if attempt == self.max_retries:
                    raise RiotAPIError("Riot API rate limit reached. Try again shortly.", 429)
                try:
                    retry_after = float(response.headers.get("Retry-After", "1"))
                except ValueError:
                    retry_after = 1
                self.sleep(max(0, min(retry_after, 30)))
                continue

            if response.status_code >= 500:
                if attempt == self.max_retries:
                    raise RiotAPIError(
                        "Riot API is temporarily unavailable.", response.status_code
                    )
                self.sleep(2**attempt)
                continue

            if response.status_code == 404:
                raise RiotAPIError("That Riot ID was not found.", 404)
            if response.status_code in {401, 403}:
                raise RiotAPIError(
                    "The Riot API key is missing, expired, or unauthorized.",
                    response.status_code,
                )

            try:
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                raise RiotAPIError(
                    "Riot API returned an unexpected response.", response.status_code
                ) from exc

        raise AssertionError("unreachable")

    def account_by_riot_id(self, game_name: str, tag_line: str) -> RiotAccountData:
        game = quote(game_name, safe="")
        tag = quote(tag_line, safe="")
        data = self._request(
            f"https://{self.routing_region}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/{game}/{tag}"
        )
        try:
            return RiotAccountData(
                puuid=data["puuid"],
                game_name=data.get("gameName", game_name),
                tag_line=data.get("tagLine", tag_line),
            )
        except (KeyError, TypeError) as exc:
            raise RiotAPIError("Riot API returned invalid account data.") from exc

    def aram_match_ids(self, puuid: str, *, count: int = 20) -> list[str]:
        safe_puuid = quote(puuid, safe="")
        data = self._request(
            f"https://{self.routing_region}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{safe_puuid}/ids"
            f"?queue=450&start=0&count={count}"
        )
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise RiotAPIError("Riot API returned an invalid match list.")
        return data

    def match(self, match_id: str) -> dict[str, Any]:
        safe_match_id = quote(match_id, safe="")
        data = self._request(
            f"https://{self.routing_region}.api.riotgames.com"
            f"/lol/match/v5/matches/{safe_match_id}"
        )
        if not isinstance(data, dict):
            raise RiotAPIError("Riot API returned invalid match data.")
        return data

    def platform_status(self) -> dict[str, Any]:
        data = self._request(
            f"https://{self.platform_region}.api.riotgames.com"
            "/lol/status/v4/platform-data"
        )
        if not isinstance(data, dict):
            raise RiotAPIError("Riot API returned invalid platform data.")
        return data
