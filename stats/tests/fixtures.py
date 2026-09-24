from stats.riot import RiotAccountData


def match_payload(match_id="NA1_1", puuid="player-puuid", dpm=1900.5, win=True):
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "queueId": 450,
            "gameMode": "ARAM",
            "gameStartTimestamp": 1_725_000_000_000,
            "gameDuration": 1200,
            "participants": [
                {
                    "puuid": puuid,
                    "riotIdGameName": "Damage Dealer",
                    "riotIdTagline": "NA1",
                    "summonerName": "Legacy Name",
                    "win": win,
                    "challenges": {"damagePerMinute": dpm},
                    "totalDamageDealtToChampions": int(dpm * 20),
                },
                {
                    "puuid": "someone-else",
                    "riotIdGameName": "Teammate",
                    "riotIdTagline": "NA1",
                    "summonerName": "Teammate",
                    "win": win,
                    "challenges": {"damagePerMinute": 900},
                    "totalDamageDealtToChampions": 18000,
                },
            ],
        },
    }


class FakeRiotClient:
    def __init__(self, *, match_ids=None, payloads=None):
        self.match_ids = match_ids or ["NA1_1"]
        self.payloads = payloads or {match_id: match_payload(match_id) for match_id in self.match_ids}
        self.match_calls = []
        self.requested_count = None

    def account_by_riot_id(self, game_name, tag_line):
        return RiotAccountData("player-puuid", game_name, tag_line)

    def aram_match_ids(self, puuid, *, count=20):
        self.requested_count = count
        return self.match_ids

    def match(self, match_id):
        self.match_calls.append(match_id)
        return self.payloads[match_id]
