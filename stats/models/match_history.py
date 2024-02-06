from stats.models.match import Match
from django.db import models

class MatchHistory(models.Model):
    def __init__(self, riotProxy, postgresProxy, person):
        self.riotProxy = riotProxy
        self.person = person
        self.postgres_layer = postgresProxy

    def __str__(self):
        ret = "This is a match history for \"" + self.person.name + "\""

        return ret

    def retrieve_matches(self):
        self.matches = []
        matches_ids = self.riotProxy.get_matches(self.person.puuid)
        for match_id in matches_ids:
            match_data = self.riotProxy.get_match(match_id)
            if 'status' in match_data:
                raise Exception("Probably Rate limited! Exact error is: ", match_data)
            if match_data != None and match_data["info"]["gameMode"] == "ARAM":
                temp_match = Match(self.person.name, match_data)
                self.postgres_layer.add_match(temp_match.id, temp_match.win, temp_match.dps_threat, match_data)

                self.matches.append(temp_match)

    def calculate_dps_ratio(self):
        total_games = 0 
        dps_threats = 0
        for match in self.matches:
            if match.dps_threat:
                dps_threats += 1
            total_games += 1

        return dps_threats/total_games

    def calculate_win_ratio(self):
        total_games = 0 
        win = 0
        for match in self.matches:
            if match.win:
                win += 1
            total_games += 1

        return win/total_games

    def print_matches(self):
        for match in self.matches:
            print(match)