# ToDo


## High Priority TO-DO
- Add serializer
- Make the Models more like data contracts/DBO, referencing this [comment](https://github.com/SpencerReyka/riot-api-match-analysis/pull/5#discussion_r1482350383)
- Standardize/Compartmentalize configuration, this [github comment](https://github.com/SpencerReyka/riot-api-match-analysis/pull/4#discussion_r1480017890) is a good start
- Naming schemas for privates
- Move the migration functionality from Pyway to Django 
- Go file by file and just double check everything looks good (formatting, code, following convention)
- Look into swagger, and into endpoint documentaton (in Readme?)
- Figure out stats/losses/core code, currently a class in the views
- Figure out how to create and close a connection for the dps threat lookup
- DTO stuff, figure out 
- Create Project folder, and app (project is riot-api, app is stats?)
- Probably remove the Runner code
- Seems like Django might want to handle the database, so might want to look into changing from Pyway migration to django-based


## TO DO 
- Backing off instead of proactive but just use the time from the rate-limited response 
- Look into figuring out how to rate limit across threads 
- Look into Typing helpers
- Add logging (and error handling?) [middleware](https://medium.com/@techWithAditya/middleware-magic-how-to-use-django-middleware-for-advanced-error-handling-and-exception-management-78573a27204e#:~:text=Django%20provides%20a%20default%20error,middleware%20can%20be%20very%20useful.)
- add a data proxy "interface" that caches and retrieves data 
- add a databse proxy and a flat file proxy 
- add a docker file in the folder that will spin up 
- add a script to run the dockerfile 
- add some sort of flow where no matter how it ends, certain stuff happens, honestly probably just put the main in a try block, and have FINALLY after to make sure things are closed
(related to LIMITER, we should have like a shut off event, which writes the limiter data to db or flat file)
- add ability to go through pagination (ugh)
- add a logging type of thing, where we i run it in debug, it logs, else it ignores log 
- Create a set_up.py script that creates all necessary config files, so we don't have to have double

## COMPLETED 
- Added Django


# Errors and Bugs 

1) Add more error checking during the Riot api usage

```bash
Internal Server Error: /stats/calculate/
Traceback (most recent call last):
  File "/Users/spencerreyka/venvs/riot_stats/lib/python3.10/site-packages/django/core/handlers/exception.py", line 55, in inner
    response = get_response(request)
  File "/Users/spencerreyka/venvs/riot_stats/lib/python3.10/site-packages/django/core/handlers/base.py", line 197, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "/Users/spencerreyka/development/riot_api/stats_losses/stats/views.py", line 22, in calculate
    dps_threats = statsService.calculate_dps_threats(content)
  File "/Users/spencerreyka/development/riot_api/stats_losses/stats/losses/core.py", line 20, in calculate_dps_threats
    res = [self.calculate_dps_threat(x) for x in names]
  File "/Users/spencerreyka/development/riot_api/stats_losses/stats/losses/core.py", line 20, in <listcomp>
    res = [self.calculate_dps_threat(x) for x in names]
  File "/Users/spencerreyka/development/riot_api/stats_losses/stats/losses/core.py", line 32, in calculate_dps_threat
    matches.retrieve_matches()
  File "/Users/spencerreyka/development/riot_api/stats_losses/stats/models/match_history.py", line 20, in retrieve_matches
    if match_data["info"]["gameMode"] == "ARAM":
KeyError: 'info'
```



limiter 

UPDATE THIS DOC TO BE ACCURATE

WE DO NOT HANDLE ERROR RETURNS - MUST FIX TODO 

SAVE REQUESTS in memory THEN BATCH save TO DB 

database readme section


## WORK IN PROGRESS
add some sort of user reference to the match_data
need to add database to cache results (once i get a match, should never need to pull that again)
add calls to the database 
add a setup script, so like have --run, and --start database
add documentation for this (like in the Readme )
add a limiter to when you open the file, it should cache the start time and count, so that subsequent runs can continue the limiter
see if you can be more granular with the rate limiter