# riot-api-match-analysis

# TO DO 
- add a data proxy "interface" that caches and retrieves data 
- add a databse proxy and a flat file proxy 
- add a docker file in the folder that will spin up 
- add a script to run the dockerfile 
- add some sort of flow where no matter how it ends, certain stuff happens, honestly probably just put the main in a try block, and have FINALLY after to make sure things are closed
(related to LIMITER, we should have like a shut off event, which writes the limiter data to db or flat file)
- add ability to go through pagination (ugh)
- add a logging type of thing, where we i run it in debug, it logs, else it ignores log 

# COMPLETED 
limiter 


# WORK IN PROGRESS
add some sort of user reference to the match_data table 
need to add database to cache results (once i get a match, should never need to pull that again)
add a postgres database 
add a limiter to when you open the file, it should cache the start time and count, so that subsequent runs can continue the limiter


docker run --name loca-riot-psql -v local_riot_psql_data:/var/lib/postgresql/data -p 54320:5432 -e POSTGRES_PASSWORD=my_password -d postgres
