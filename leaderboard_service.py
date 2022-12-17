import redis
import toml
import os
import httpx
import utils.helpers as helpers
from quart import Quart, jsonify, g, request, abort
app = Quart(__name__)
app.config.from_file(f"./config/app.toml", toml.load)
players = "Players"
game_count = "GameCount"
score_sum = "ScoreSum"
r = redis.StrictRedis(host='localhost',port=6379,db=0)
import socket


url = socket.gethostbyname(socket.getfqdn("localhost"))
port = os.environ.get('PORT')

# Registering call back url with game_service
def register_url():
    #Generated Callback Url
    call_back_url = 'http://' + url + ':' + port + '/leaderboard' 
    data = {'client_name': 'leaderboard_service', 'url' : call_back_url}
    #Sending Registering post request
    response = httpx.post('http://tuffix-vm/gameservice_client_register_url', json = data)
    #Register Successfully
    if (response.status_code == '200'):
        print(response.text)
        

#Updating the leaderboard scores
@app.route("/leaderboard", methods=["POST"])
async def update_leaderboard():
    data = await request.get_json()
    if not data or 'username' not in data or 'is_won' not in data or 'guess' not in data:
        return helpers.jsonify_message("Required username, is_won(0/1), guess"), 400
    username = data['username']
    is_won = int(data['is_won'])
    guess = int(data['guess'])
    score = app.config["WORDLE"]["MAX_NUM_ATTEMPTS"] - guess + 1 if is_won else 0

    if not r.hget(game_count, username):
        r.hset(game_count, username, 0)
    old_game_count = int(r.hget(game_count, username).decode('utf-8'))
    r.hset(game_count, username, old_game_count + 1)

    if not r.hget(score_sum, username):
        r.hset(score_sum, username, 0)
    old_score_sum = int(r.hget(score_sum, username).decode('utf-8'))
    new_score = old_score_sum + score
    r.hset(score_sum, username, new_score)

    if not r.zscore(players, username):
        r.zadd(players, {username: 0})
    new_game_count = int(r.hget(game_count, username).decode('utf-8'))
    new_score_sum = int(r.hget(score_sum, username).decode('utf-8'))
    print(f"Total score: {new_score_sum}, Total played: {new_game_count}")
    r.zadd(players, {username: new_score_sum / new_game_count})
    return {username: r.zscore(players, username)}

#Printing Top 10 leaderboard scores 
@app.route("/top10", methods=["GET"])
async def get_rankings():
    top10 = r.zrevrange(players, 0, 9, withscores=True)
    result = "Top 10 Leaderboard \n"
    for element in top10:
        element = str(element)
        result = result + element[2:-1] + "\n"
    return result


try:
    register_url()
except httpx.HTTPError as exc:
    print(f"HTTP Exception for {exc.request.url} - {exc}")
