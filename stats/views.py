from django.http import HttpResponse
from stats.losses.core import StatsService
import json

statsService = StatsService()

def index(request):
    print(request.body)

    #set_up_code()

    return HttpResponse("Hello, world. You're at the polls index.")


def calculate(request):
    statsService
    body = json.loads(request.body.decode('utf-8'))
    print(body)
    content = body['usernames']
    
    dps_threats = statsService.calculate_dps_threats(content)

    res = "DPS Threat Ratio:\n"

    for i, dps_threat in enumerate(dps_threats):
        res += f"{content[i]}: {dps_threat}"


    return HttpResponse(res)