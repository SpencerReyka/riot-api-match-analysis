from unittest import TestCase

import requests

from stats.riot import RiotAPIError, RiotClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self.payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class RiotClientTests(TestCase):
    def test_uses_header_and_encodes_riot_id(self):
        session = FakeSession(
            [FakeResponse(payload={"puuid": "p1", "gameName": "A Name", "tagLine": "NA1"})]
        )
        client = RiotClient("RGAPI-test", session=session)

        account = client.account_by_riot_id("A Name", "N/A")

        self.assertEqual(session.headers["X-Riot-Token"], "RGAPI-test")
        self.assertNotIn("RGAPI-test", session.calls[0][0])
        self.assertIn("/A%20Name/N%2FA", session.calls[0][0])
        self.assertEqual(account.puuid, "p1")

    def test_match_ids_request_aram_queue(self):
        session = FakeSession([FakeResponse(payload=["NA1_1", "NA1_2"])])
        client = RiotClient("key", session=session)

        ids = client.aram_match_ids("p/id", count=12)

        self.assertEqual(ids, ["NA1_1", "NA1_2"])
        self.assertIn("queue=450&start=0&count=12", session.calls[0][0])
        self.assertIn("p%2Fid", session.calls[0][0])

    def test_uses_retry_after_for_rate_limit(self):
        sleeps = []
        session = FakeSession(
            [
                FakeResponse(429, headers={"Retry-After": "2.5"}),
                FakeResponse(payload=["NA1_1"]),
            ]
        )
        client = RiotClient("key", session=session, sleep=sleeps.append)

        self.assertEqual(client.aram_match_ids("p1"), ["NA1_1"])
        self.assertEqual(sleeps, [2.5])
        self.assertEqual(len(session.calls), 2)

    def test_maps_expired_key_to_safe_error(self):
        client = RiotClient("key", session=FakeSession([FakeResponse(403)]))

        with self.assertRaisesRegex(RiotAPIError, "expired") as caught:
            client.account_by_riot_id("Player", "NA1")

        self.assertEqual(caught.exception.status_code, 403)

    def test_retries_network_error_then_succeeds(self):
        sleeps = []
        session = FakeSession(
            [requests.ConnectionError("offline"), FakeResponse(payload={"metadata": {}})]
        )
        client = RiotClient("key", session=session, sleep=sleeps.append)

        self.assertEqual(client.match("NA1_1"), {"metadata": {}})
        self.assertEqual(sleeps, [1])
