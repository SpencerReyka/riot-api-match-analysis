from django.db import models

# Create your models here.
class RiotAccount(models.Model):
    accountId = models.CharField(max_length=50)
    puuid = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    profileIconId = models.CharField(max_length=50)
    revisionDate = models.CharField(max_length=50)