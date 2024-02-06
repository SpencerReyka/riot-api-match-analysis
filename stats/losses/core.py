import requests
import os
from stats.data_access.postgres import PostgresProxy
from stats.data_access.riot import RiotProxy
from stats.models.profile import Profile
from stats.models.match_history import MatchHistory

class Config():
    def __init__(self, api_key):
        self.api_key = api_key
        print("created Config")  

class StatsService():

    def __init__(self):
        API_KEY = os.getenv('RIOT_API_KEY_APP')
        self.riotProxy = RiotProxy(API_KEY)

    def calculate_dps_threats(self, names):
        res = []

        for name in names:
            dps_threat = self.calculate_dps_threat(name)
            res.append(dps_threat)

        return res

    def calculate_dps_threat(self, name):

        postgresProxy = PostgresProxy()

        profile = Profile(self.riotProxy, name)

        matches = MatchHistory(self.riotProxy, postgresProxy, profile)

        matches.retrieve_matches()

        postgresProxy.close()

        return matches.calculate_dps_ratio()

def set_up_code():
    API_KEY = os.getenv('RIOT_API_KEY_APP')
    riotProxy = RiotProxy(API_KEY)
    print(riotProxy.get_me())

    postgresProxy = PostgresProxy()

    rbg = Profile(riotProxy, "RBG can peg me ")
    print(rbg)

    mcbad = Profile(riotProxy, "MądBcBąd") 
    print(mcbad)

    # currently match history creates a postgres layer, but we need this to be passed in 
    rbg_matches = MatchHistory(riotProxy, postgresProxy, rbg)
    #print(rbg_matches)

    mcbad_matches = MatchHistory(riotProxy, postgresProxy, mcbad)
    #print(mcbad_matches)

    rbg_matches.retrieve_matches()
    print("Ratio of DPS threats for " + rbg_matches.person.name + " is: " + str(rbg_matches.calculate_dps_ratio()))
    print("Ratio of wins for " + rbg_matches.person.name + " is: " + str(rbg_matches.calculate_win_ratio()))

    # mcbad_matches.retrieve_matches()
    # print("Ratio of DPS threats for " + mcbad_matches.person.name + " is: " + str(mcbad_matches.calculate_dps_ratio()))
    # print("Ratio of wins for " + mcbad_matches.person.name + " is: " + str(mcbad_matches.calculate_win_ratio()))

    postgresProxy.close()













