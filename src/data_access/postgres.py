import os
import psycopg2

class PostgresProxy():

    def __init__(self):
        self.port = API_KEY = os.getenv('DOCKER_PORT')
        self.db = API_KEY = os.getenv('DOCKER_DB')
        self.user = API_KEY = os.getenv('DOCKER_USER')
        self.password = API_KEY = os.getenv('DOCKER_PASS')

        try:
            # Connect to an existing database
            self.connection = psycopg2.connect(user=self.user,
                                        password=self.password,
                                        host="127.0.0.1",
                                        port=self.port,
                                        database=self.db)

        except Exception as error:
            print("Error while connecting to PostgreSQL", error)                     

    def add_match(self, match_id, win, dps_threat, match_data):  
        
        try:
            # Create a cursor to perform database operations
            cursor = self.connection.cursor()
            # Executing a SQL query
            cursor.execute("INSERT INTO match_data (riot_match_id, win, dps_threat, match_data) VALUES(%s, %s, %s, %s) ON CONFLICT DO NOTHING", (match_id, win, dps_threat, str(match_data)))
            self.connection.commit()
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL", error)
        finally:
            if (cursor):
                cursor.close()
                #print("cursor connection is closed")

    def add_matches(self, matches):  
                
        try:
            # Create a cursor to perform database operations
            cursor = self.connection.cursor()

            values = ""
            for match in matches:
                values += f"(%{match.id}, %{match.win}, %{match.dps_threat}, %{str(match.match_data)}) "

            # Executing a SQL query
            cursor.execute("INSERT INTO match_data (riot_match_id, win, dps_threat, match_data) VALUES %s ON CONFLICT DO NOTHING", (values))
            self.connection.commit()
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL", error)
        finally:
            if (cursor):
                cursor.close()
                #print("cursor connection is closed")


    def close(self):
        if (self.connection):
            self.connection.close()
            print("PostgreSQL connection is closed")