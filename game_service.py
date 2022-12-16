# Project 2 - API Gateway - Wordle Mock Backend

import toml
import sqlite3
import databases
import base64
import dataclasses
import uuid
import itertools
import utils.helpers as helpers
import asyncio
from redis import Redis
from rq import Queue
import time
from job import count_words_at_url

from typing import Tuple, Optional
from quart import Quart, jsonify, g, request, abort
from quart_schema import QuartSchema, validate_request

app = Quart(__name__)
QuartSchema(app)

app.config.from_file(f"./config/app.toml", toml.load)


@dataclasses.dataclass
class Guess:
    guess: str


@dataclasses.dataclass
class Username:
    username: str



db_buffer = ['GAMES', 'GAMES_SECONDARY1', 'GAMES_SECONDARY2']
DbList = itertools.cycle(db_buffer)

# choose = itertools.cycle()

async def _connect_db_write():
    database = g._sqlite_db_read = databases.Database(app.config["DATABASES"]["GAMES"])
    await database.connect()
    print("primary database--------------")
    return database

async def _connect_db_read():
    db = next(DbList)
    database = g._sqlite_db_read = databases.Database(app.config["DATABASES"][db])
    await database.connect()
    print(db)
    print("secondary database-------------")
    return database

# async def _connect_db_write():
#     if not hasattr(g, "sqlite_db"):
#         g.sqlite_db = _connect_db_write()
#     return g.sqlite_db

# async def _connect_db_read():
#     if not hasattr(g, "sqlite_db"):
#         g.sqlite_db = _connect_db_read(next(DbList))
#     return g.sqlite_db

@app.teardown_appcontext
async def close_connection(exception):
    db = getattr(g, "_sqlite_db", None)
    if db is not None:
        await db.disconnect()




def worker():
    q = Queue(connection=Redis())
    print("Working.......")
    data = {'username':'Akash', 'is_won': 1, 'guess' : 4}
    result = q.enqueue(count_words_at_url, 'http://127.0.0.1:3000/dummy', data)

    print(result.result) #Here it will show none output as job is still going on
    time.sleep(5)

    print(result.result) #Prints the counted words


# ----------------------------Routes---------------------------- #

@app.route("/", methods=["GET"])
async def home():
    """
    Home
    
    This is just the welcome message.
    """
    
    return helpers.jsonify_message("Welcome to game service.")

@app.route("/wordle/start", methods=["POST"])
async def start_game():
    """
    Start Game
    
    Initializes a game. Returns the game ID if successful.
    """
    username = request.authorization.username

    db_read = await _connect_db_read()

    query = "SELECT word FROM secret_word ORDER BY RANDOM() LIMIT 1"
    app.logger.info(query), app.logger.warning(query)
    secret_word = await db_read.fetch_one(query=query)

    db_write = await _connect_db_write()

    try:
        gameid = str(uuid.uuid4())
        query = "INSERT INTO games(gameid, username, secretWord) VALUES(:gameid, :username, :secret_word)"
        values = {"gameid":gameid, "username": username, "secret_word": secret_word.word}
        await db_write.execute(query=query, values=values)
    except sqlite3.IntegrityError as e:
        abort(409, e)
    return helpers.jsonify_message(f"Game started with id: {gameid}.")


@app.route("/wordle/games", methods=["GET"])
async def list_active_games():
    """
    List Active Games
    
    This generates a list of game IDs that are active. Games that ran out of attempts 
    or games that have been won are not included in the list.
    """
    username = request.authorization.username

    db_read =  await _connect_db_read()
    query = """
            SELECT gameid FROM games WHERE username = :username AND isActive = 1
            """
    app.logger.info(query), app.logger.warning(query)
    games = await db_read.fetch_all(query=query, values={"username": username})

    if games:
        return list(map(dict, games))
    else:
        return helpers.jsonify_message(f"No active games found for user, {username}."), 404


async def game_is_active(db_read, username, gameid) -> bool:
    query = """
            SELECT * FROM games WHERE username = :username AND gameid = :gameid AND isActive = 1
            """
    app.logger.info(query), app.logger.warning(query)
    game = await db_read.fetch_one(query=query, values={"username": username, "gameid": gameid})
    if game:
        return True
    else:
        return False
        

@app.route("/wordle/<string:gameid>/status", methods=["GET"])
async def retrieve_game(gameid):
    """
    Retrieve Game
    
    This displays the current state of a specified active game. It lists all the attempts, as well as,
    the details of how close the attempts are from the secret word. This also shows the number
    of attempts left before the game ends.
    """
    username = request.authorization.username
    db_read =  await _connect_db_read()

    if await game_is_active(db_read, username, gameid):
        query = """
                SELECT guess, secretWord as secret_word
                FROM guesses
                LEFT JOIN games ON guesses.gameid = games.gameid
                WHERE games.gameid = :gameid AND isActive = 1
                """
        app.logger.info(query), app.logger.warning(query)
        guesses = await db_read.fetch_all(query=query, values={"gameid": gameid})

        return calculate_game_status(guesses)
    else:
        abort(404)


#Adding Client url to the database
@app.route("/gameservice_client_register_url", methods=["POST"])
async def register_leaderboardservice():
    data = await request.get_data()
    url =  data.decode("utf-8")
    db_write =  await _connect_db_write()
    db_read = await _connect_db_read()


    query = "SELECT url from client_url WHERE url=:url"
    existing_url = await db_read.fetch_one(query=query, values={"url":url})
  

    if( not existing_url):
        try:
            query = "INSERT INTO client_url(url) VALUES(:url)"
            values = {"url" : url}
            await db_write.execute(query=query, values=values)
            return "Call-back Url Registered", 200
        except sqlite3.IntegrityError as e:
            abort(409, e)    
    else:
        return "Client URL already exist", 403  
    
    


def calculate_game_status(guesses):
    # Clean up and check guesses:
    num_guesses = len(guesses)
    list_guesses = []
    for guess in guesses:
        correct_letters, correct_indices = helpers.compare_guess(guess.guess, guess.secret_word)
        list_guesses.append({
            "guess": guess.guess,
            "correct_letters": correct_letters,
            "correct_indices": correct_indices
        })

    return {
        "num_guesses": num_guesses,
        "max_attempts": app.config["WORDLE"]["MAX_NUM_ATTEMPTS"],
        "guesses": list_guesses
    }


@app.route("/wordle/<string:gameid>/guess", methods=["POST"])
@validate_request(Guess)
async def make_guess(gameid, data: Guess):
    """
    Guess the Secret Word
    
    This inserts a guess into the guesses table if the guess word is a valid word. If the
    guess is valid, it will show whether it is correct and display hints accordingly. It
    will also tell the player how many attempts they have left.
    """
    username = request.authorization.username
    data = await request.get_json()
    db_write =  await _connect_db_write()
    db_read = await _connect_db_read()

    if await game_is_active(db_read, username, gameid):
        # Validate the guessed word first:
        if len(data["guess"]) != app.config["WORDLE"]["WORDLE_LENGTH"]:
            return helpers.jsonify_message(f"Not a valid guess! Please only guess {app.config['WORDLE']['WORDLE_LENGTH']}-letter words. This attempt does not count.")
        else:
            query = "SELECT * FROM valid_words WHERE word = :guess"
            app.logger.info(query), app.logger.warning(query)
            is_valid = await db_read.fetch_one(query=query, values={"guess": data["guess"]})

            if not is_valid:
                return helpers.jsonify_message(f"{data['guess']} is not a valid word! Try again. This attempt does not count.")

        # guess was valid, proceed to store and check game state
        try:
            query = """
                    INSERT INTO guesses(gameid, guess) VALUES(:gameid, :guess)
                    """
            await db_write.execute(query=query, values={"gameid": gameid, "guess": data["guess"]})
        except sqlite3.IntegrityError as e:
            # guesses are unique per game
            abort(409, e)
        
        # grab the secret word
        query = """
                SELECT secretWord AS secret_word FROM games WHERE gameid = :gameid
                """
        app.logger.info(query), app.logger.warning(query)
        game = await db_read.fetch_one(query=query, values={"gameid": gameid})
        secret_word = game.secret_word 


        query = """
                SELECT guess, secretWord as secret_word
                FROM guesses
                LEFT JOIN games ON guesses.gameid = games.gameid
                WHERE games.gameid = :gameid AND isActive = 1
                """
        app.logger.info(query), app.logger.warning(query)
        guesses = await db_read.fetch_all(query=query, values={"gameid": gameid})
        guesses = calculate_game_status(guesses)

        is_correct = helpers.check_guess(data["guess"], secret_word)
        max_num_attempts = app.config["WORDLE"]["MAX_NUM_ATTEMPTS"]

        if is_correct:
            query = """
                    UPDATE games 
                    SET isActive = 0, hasWon = 1
                    WHERE gameid = :gameid
                    """
            await db_write.execute(query=query, values={"gameid": gameid})
            worker()
            return helpers.jsonify_message(f"Correct! The answer was {secret_word}.")
        elif guesses["num_guesses"] == max_num_attempts and not is_correct:
            query = """
                    UPDATE games 
                    SET isActive = 0
                    WHERE gameid = :gameid
                    """
            await db_write.execute(query=query, values={"gameid": gameid})
            
            return helpers.jsonify_message(f"You have lost! You have made {max_num_attempts} incorrect attempts. The secret word was {secret_word}.")
        else:
            remaining_attempts = max_num_attempts - guesses["num_guesses"]
            return {
                "message": f"Try again! You have {remaining_attempts} more attampts left.",
                "guesses": guesses
            }
    else:
        abort(404)


@app.errorhandler(404)
def not_found(e):
    return {"error": "The resource could not be found"}, 404


@app.errorhandler(409)
def conflict(e):
    return {"error": str(e)}, 409