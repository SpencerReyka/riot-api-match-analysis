import requests
import os


class Profile():
    def __init__(self, riotProxy, accountName):
        self.riotProxy = riotProxy
        res = riotProxy.get_summoner(accountName)

        self.id = res["id"]
        self.accountId = res["accountId"]
        self.puuid = res["puuid"]
        self.name = res["name"]
        self.profileIconId = res["profileIconId"]
        self.revisionDate = res["revisionDate"]

    def __str__(self):
        ret = "\nName: " + self.name + "\n"
        ret += "\nId: " + self.id + "\n"
        ret += "\nAccountId: " + self.accountId + "\n"
        ret += "\nPUUID: " + self.puuid + "\n"
        ret += "\nRevision Date: " + str(self.revisionDate) + "\n"
        ret += "\nProfile Icon Id: " + str(self.profileIconId) + "\n"

        return ret

class MatchHistory():
    def __init__(self, riotProxy, person):
        self.riotProxy = riotProxy
        self.person = person

    def __str__(self):
        ret = "This is a match history for \"" + self.person.name + "\""

        return ret

    def retrieve_matches(self):
        self.matches = []
        matches_ids = self.riotProxy.get_matches(self.person.puuid)
        for match_id in matches_ids:
            match_data = self.riotProxy.get_match(match_id)
            if match_data["info"]["gameMode"] == "ARAM":
                self.matches.append(Match(self.person.name, match_data))

    def calculate_dps_ratio(self):
        total_games = 0 
        dps_threats = 0
        for match in self.matches:
            if match.dps_threat:
                dps_threats += 1
            total_games += 1

        return dps_threats/total_games

    def print_matches(self):
        for match in self.matches:
            print(match)

class Match():
    def __init__(self, username, match_data):
        self.username = username
        self.match_data = match_data
        self.dps = 0
        for participant in self.match_data["info"]["participants"]:
            if participant["summonerName"] == username:
                self.dps = participant["challenges"]["damagePerMinute"]

        self.dps_threat = True if self.dps > 1800 else False
        
    def __str__(self):
        return self.username + " did " + str(self.dps) + " damage, and dps threat is " + str(self.dps_threat)

class Config():
    def __init__(self, api_key):
        self.api_key = api_key
        print("created Config")   

class RiotProxy():
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_key_url = "?api_key=" + api_key

    def get_summoner_url(self):
        return "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"

    def get_matches_url(self, puuid):
        return "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids"

    def get_matches_path_url(self): 
        return "&type=normal&start=0&count=40"

    def get_match_url(self):
        return "https://americas.api.riotgames.com/lol/match/v5/matches/"

    def get_summoner(self, accountName):
        r = requests.get(self.get_summoner_url() + accountName + self.api_key_url)
        res = r.json()
        print(res)
        return res

    def get_matches(self, puuid):
        r = requests.get(self.get_matches_url(puuid) + self.api_key_url + self.get_matches_path_url())
        res = r.json()
        return res

    def get_match(self, match_id):
        r = requests.get(self.get_match_url() + match_id + self.api_key_url)
        res = r.json()
        return res


def set_up_code():
    API_KEY = os.getenv('RIOT_API_KEY_APP')
    riotProxy = RiotProxy(API_KEY)

    rbg = Profile(riotProxy, "rbgcanpegme")
    print(rbg)

    mcbad = Profile(riotProxy, "MądBcBąd") 
    print(mcbad)

    rbg_matches = MatchHistory(riotProxy, rbg)
    print(rbg_matches)

    mcbad_matches = MatchHistory(riotProxy, mcbad)
    print(mcbad_matches)

    rbg_matches.retrieve_matches()
    print("Ratio of DPS threats is: " + str(rbg_matches.calculate_dps_ratio()))

    mcbad_matches.retrieve_matches()
    print("Ratio of DPS threats is: " + str(mcbad_matches.calculate_dps_ratio()))









