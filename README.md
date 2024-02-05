# riot-api-match-analysis

# High Priority TO-DO
- add Django 
- DTO stuff, figure out 
- Create Project folder, and app (project is riot-api, app is stats?)


# TO DO 
- add a data proxy "interface" that caches and retrieves data 
- add a databse proxy and a flat file proxy 
- add a docker file in the folder that will spin up 
- add a script to run the dockerfile 
- add some sort of flow where no matter how it ends, certain stuff happens, honestly probably just put the main in a try block, and have FINALLY after to make sure things are closed
(related to LIMITER, we should have like a shut off event, which writes the limiter data to db or flat file)
- add ability to go through pagination (ugh)
- add a logging type of thing, where we i run it in debug, it logs, else it ignores log 
- Create a set_up.py script that creates all necessary config files, so we don't have to have double

# COMPLETED 
limiter 

UPDATE THIS DOC TO BE ACCURATE

WE DO NOT HANDLE ERROR RETURNS - MUST FIX TODO 

SAVE REQUESTS in memory THEN BATCH save TO DB 

database readme section


# WORK IN PROGRESS
add some sort of user reference to the match_data
need to add database to cache results (once i get a match, should never need to pull that again)
add calls to the database 
add a setup script, so like have --run, and --start database
add documentation for this (like in the Readme )
add a limiter to when you open the file, it should cache the start time and count, so that subsequent runs can continue the limiter
see if you can be more granular with the rate limiter




# Layout 
TBD finish this 




# Riot API 
using old name cause new name doesn't show up 

# Database

## Running Database From Docker

```bash
docker run --name loca-riot-psql -v local_riot_psql_data:/var/lib/postgresql/data -p 54320:5432 -e POSTGRES_PASSWORD=my_password -d postgres
```

## Database Connection from Django
One way to direct Django to connect to the database is to create a [Connection Service File](https://www.postgresql.org/docs/current/libpq-pgservice.html) and [Password File](https://www.postgresql.org/docs/current/libpq-pgpass.html) and include them in the project's settings.py

### Connection Service File 
Make sure a ~/.pg_service.conf exists. 
The format is:
```bash
[mydb]
host=somehost
port=5433
user=admin
```

### Password File 
Make sure a .pgpass exists in the project's root directory. 
The format is:
```bash
host:port:database:user:password
```


## Database Migration
Uses Pyway, a python version of Flyway

### Usage

### Info
Information lets you know where you are. At first glance, you will see which migrations have already been applied, which others are still pending, and whether there is a discrepancy between the checksum of the local file and the database schema table.

```bash
$ pyway info
```

### Validate
Validate helps you verify that the migrations applied to the database match the ones available locally. This compares the checksums to validate that what is in the migration on disk is what was committed into the database.

```bash
$ pyway validate
```

### Migrate
After validate, it will scan the Database migration dir for available migrations. It will compare them to the migrations that have been applied to the database. If any new migration is found, it will migrate the database to close the gap.

```bash
$ pyway migrate
```

### Import
This allows the user to import a schema file into the migration, for example if the base schema has already been applied, then the user can import that file in so they can then apply subsequent migrations. Currently the import looks in the database_migration_dir for the file.

```bash
$ pyway import --schema-file V01_01__initial_schema.sql
```

### Checksum
Updates a checksum in the database. This is for advanced use only, as it could put the pyway database out of sync with reality. This is mainly to be used for development, where your pyway file may change because of manual applies or formatting changes. It is meant to get the database in sync with what you believe to be the current state of your system. It should NEVER be used in production, only initial development. If you require schema changes in production, create a new schema and apply that.

```bash
$ pyway checksum --checksum-file V01_01__initial_schema.sql
```

## Virtual Environment

### Create Environment

```bash
spencerreyka@Spencers-MBP stats_losses % python3 -m venv ~/venvs/riot_stats 
```

### Activate Environment 

```bash
spencerreyka@Spencers-MBP stats_losses % source ~/venvs/riot_stats/bin/activate
```

### Deactivate Environment

```bash
(riot_stats) spencerreyka@Spencers-MBP stats_losses % deactivate
```