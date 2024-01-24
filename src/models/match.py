class Match():
    def __init__(self, username, match_data):
        self.id = match_data["metadata"]["matchId"]
        self.username = username
        self.match_data = match_data
        self.dps = 0
        self.win = False
        for participant in self.match_data["info"]["participants"]:
            if participant["summonerName"] == username:
                self.dps = participant["challenges"]["damagePerMinute"]
                self.win = participant["win"]

        self.dps_threat = True if self.dps > 1800 else False
        
    def __str__(self):
        return self.username + " did " + str(self.dps) + " damage, and dps threat is " + str(self.dps_threat)