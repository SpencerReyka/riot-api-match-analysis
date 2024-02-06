from django.db import models

class Profile(models.Model):
    def __init__(self, riotProxy, accountName):
        self.riotProxy = riotProxy
        res = riotProxy.get_summoner(accountName)
        print(res)

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