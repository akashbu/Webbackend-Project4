# Initialize database and populate initial values:

from databases import Database

import asyncio
import json

users_database = Database('sqlite+aiosqlite:///database/users.db')
games_database = Database('sqlite+aiosqlite:///var/primary/mount/games.db')

async def init_users_db():
    await users_database.connect()

    query = "DROP TABLE IF EXISTS user"
    await users_database.execute(query=query)
    
    query = """
            CREATE TABLE user (
                userid INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
                username TEXT NOT NULL UNIQUE, 
                pwd BLOB NOT NULL
            )
            """
    await users_database.execute(query=query)

    print("Users database has been initiailized.")

async def init_games_db():
    await games_database.connect()

    query = "DROP TABLE IF EXISTS games"
    await games_database.execute(query=query)
    query = "DROP TABLE IF EXISTS guesses"
    await games_database.execute(query=query)
    query = "DROP TABLE IF EXISTS secret_word"
    await games_database.execute(query=query)
    query = "DROP TABLE IF EXISTS valid_words"
    await games_database.execute(query=query)

    query = """ 
            CREATE TABLE games (
                gameid TEXT NOT NULL PRIMARY KEY ,
                username TEXT NOT NULL,
                secretWord TEXT NOT NULL,
                isActive INTEGER DEFAULT 1 NOT NULL,
                hasWon INTEGER DEFAULT 0 NOT NULL
            )
            """
    await games_database.execute(query=query)

    query = """
            CREATE TABLE guesses (
                guessid INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                gameid TEXT NOT NULL,
                guess TEXT NOT NULL,
                UNIQUE(gameid, guess)
                FOREIGN KEY(gameid) REFERENCES games(gameid)
            )
            """
    await games_database.execute(query=query)

    query = """ 
            CREATE TABLE secret_word (
                word TEXT PRIMARY KEY
            )
            """
    await games_database.execute(query=query)

    query = """ 
            CREATE TABLE valid_words (
                word TEXT PRIMARY KEY
            )
            """
    await games_database.execute(query=query)
    print("Games database has been initialized.")

    #Creating Index
    print("Initializing Indexes.")

    query = """
            CREATE INDEX games_id_index ON games(
                username,
                isActive);
            """
    await games_database.execute(query=query)

    print("Index Created.")
    

async def populate_tables():
    # Fill secret_word and valid_words with words from correct.json and valid.json:
    correct_json = open("share/correct.json")
    valid_json = open("share/valid.json")
    
    print("Populating secret_word table...")
    query = """
            INSERT INTO secret_word (word) VALUES (:word)
            """
    correct_words = [{"word": word} for word in json.load(correct_json)]
    await games_database.execute_many(query=query, values=correct_words)

    print("Populating valid_words table...")
    query = """
            INSERT INTO valid_words (word) VALUES (:word)
            """
    valid_words = [{"word": word} for word in json.load(valid_json)]
    await games_database.execute_many(query=query, values=valid_words)
    await games_database.execute_many(query=query, values=correct_words)



def main():
    asyncio.run(init_users_db()) 
    asyncio.run(init_games_db())
    asyncio.run(populate_tables())

if __name__ == "__main__":
    main()

