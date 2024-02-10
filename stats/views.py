from django.http import HttpResponse
from stats.losses.core import StatsService
from json.decoder import JSONDecodeError
from rest_framework import viewsets
from stats.django_models import RiotAccount
from stats.serializer import RiotAccountSerializer
import json

statsService = StatsService()

def index(request):
    print(request.body)

    #set_up_code()

    return HttpResponse("Hello, world. You're at the polls index.")


def calculate(request):

    try:
        body = json.loads(request.body)
        content = body['usernames']
    
        dps_threats = statsService.calculate_dps_threats(content)

        res = "DPS Threat Ratio:\n"

        for i, dps_threat in enumerate(dps_threats):
            res += f"{content[i]}: {dps_threat}\n"


        return HttpResponse(res, status=200)
    except ValueError or JSONDecodeError:
        return HttpResponse("Malformed data!", 400)

class RiotAccountViewSet(viewsets.ModelViewSet):
    queryset = RiotAccount.objects.all()
    serializer_class = RiotAccountSerializer