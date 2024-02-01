import requests
import urllib.parse
from stats.data_access.rate_limit import RateLimit

class RiotProxy():
    
    def __init__(self, api_key):
        self.rate_limiter = RateLimit()
        self.api_key = api_key
        self.api_key_url = "?api_key=" + api_key

    def get_summoner_url(self):
        return "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"

    def get_matches_url(self, puuid):
        return "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/" + puuid + "/ids"

    def get_matches_path_url(self): 
        return "&type=normal&start=0&count=100"

    def get_match_url(self):
        return "https://americas.api.riotgames.com/lol/match/v5/matches/"

    def get_me_url(self):
        return "https://na1.api.riotgames.com/lol/summoner/v4/summoners/me"

    def request_url(self, url):
        self.rate_limiter.check_and_sleep()
        r = requests.get(url)
        res = r.json()
        return res

    def get_summoner(self, accountName):
        parsed_name = urllib.parse.quote(accountName)
        print(parsed_name)
        return self.request_url(self.get_summoner_url() + parsed_name + self.api_key_url)

    def get_me(self):
        return self.request_url(self.get_me_url() + self.api_key_url)

    def get_matches(self, puuid):
        return self.request_url(self.get_matches_url(puuid) + self.api_key_url + self.get_matches_path_url())

    def get_match(self, match_id):
        return self.request_url(self.get_match_url() + match_id + self.api_key_url)