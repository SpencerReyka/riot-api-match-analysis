# ToDo


## High Priority TO-DO
- Figure out stats/losses/core code, currently a class in the views
- Figure out how to create and close a connection for the dps threat lookup
- DTO stuff, figure out 
- Create Project folder, and app (project is riot-api, app is stats?)
- Probably remove the Runner code
- Add to readme about endpoint? Maybe look into swagger too.


## TO DO 
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