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
    def __init__(self, person):
        self.person = person

    def __str__(self):
        ret = "This is a match history for \"" + self.person.name + "\""

        return ret

    def retrieve_matches(self):
        print("retrieving matches")

    def print_matches(self):
        print("printing matches")


class Config():
    def __init__(self, api_key):
        self.api_key = api_key
        print("created Config")   

class RiotProxy():
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_key_url = "?api_key=" + api_key

    def get_summoner(self, accountName):
        r = requests.get(self.get_summoner_url() + accountName + self.api_key_url)
        res = r.json()
        print(res)
        return res

    def get_summoner_url(self):
        return "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"

def set_up_code():
    API_KEY = os.getenv('RIOT_API_KEY_APP')
    riotProxy = RiotProxy(API_KEY)

    rbg = Profile(riotProxy, "rbgcanpegme")
    print(rbg)

    matches = MatchHistory(rbg)
    print(matches)







