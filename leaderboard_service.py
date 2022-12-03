import redis
import toml
import utils.helpers as helpers
from quart import Quart, jsonify, g, request, abort
app = Quart(__name__)
app.config.from_file(f"./config/app.toml", toml.load)
players = "Players"
r = redis.StrictRedis(host='localhost',port=6379,db=0)

@app.route("/leaderboard", methods=["GET", "POST"])
async def update_leaderboard():
    if (request.method == "GET"):
        top10 = r.zrange(players, 0, 9, desc=True, withscores=True)
        return jsonify({username.decode('utf-8'): score for username, score in top10})
    else:
        data = await request.get_json()
        if not data or 'username' not in data or 'score' not in data:
            return helpers.jsonify_message("Required username and score"), 400
        username = data['username']
        score = int(data['score'])
        if not r.zscore(players, username):
            r.zadd(players, {username: 0})
        old_score = r.zscore(players, username)
        r.zadd(players, {username: old_score + score})
        return {username: r.zscore(players, username)}

    
