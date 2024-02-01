import requests
import os
from src.data_access.postgres import PostgresProxy
from src.data_access.riot import RiotProxy
from src.models.profile import Profile
from src.models.match_history import MatchHistory

class Config():
    def __init__(self, api_key):
        self.api_key = api_key
        print("created Config")  

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









