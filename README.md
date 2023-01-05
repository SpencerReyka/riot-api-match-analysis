# riot-api-match-analysis

# TO DO 
need to add database to cache results (once i get a match, should never need to pull that again)
add a data proxy "interface" that caches and retrieves data 
add a databse proxy and a flat file proxy 
add a postgres database 
add a docker file in the folder that will spin up 
add a script to run the dockerfile 




docker run --name loca-riot-psql -v local_riot_psql_data:/var/lib/postgresql/data -p 54320:5432 -e POSTGRES_PASSWORD=my_password -d postgres