# CPSC 449 - Project 2 - Wordle Mock Backend

This README describes how to run the app and test the various access points.

### Authors
Group 17
Members: 
- Akash Butala (akbutala@csu.fullerton.edu)
- Heet Savla (heetsavla@csu.fullerton.edu)
- Sam Truong (samtruonh@csu.fullerton.edu)


## Setup
### Requirements
- Python 3 (with pip)
- Quart
- SQLite 3
- Databases
- SQLAlchemy
- Foreman
- Quart-Schema
- HTTPie
- PyTest (including pytest-asyncio)

Run the following commands if any of the required libraries are missing:
```
$ sudo snap install httpie
$ sudo apt update
$ sudo apt install --yes python3-pip ruby-foreman sqlite3
$ python3 -m pip install --upgrade quart[dotenv] click markupsafe Jinja2
$ python3 -m pip install sqlalchemy==1.4.41
$ python3 -m pip install databases[aiosqlite]
$ python3 -m pip install pytest pytest-asyncio
$ sudo apt install nginx
$ sudo apt install --yes nginx-extras

```
### Configuring Nginx File
#### Path (/etc/ngnix/sites-enabled/tutorial.txt)

To utilize the Nginx file we must set it up by 'cd /etc/nginx/sites-enabled' and then 'sudo "${EDITOR:-vi}" tutorial' (as described here: https://ubuntu.com/tutorials/install-and-configure-nginx#4-setting-up-virtual-host) into the Linux terminal. The second part will allow us to use the Linux terminal to edit the contents of the tutorial file which hosts the configuration of our Nginx settings. The named 'tutorial' Nginx configuration file and directories may need to be created before hand, see (https://ubuntu.com/tutorials/install-and-configure-nginx#1-overview) for more details on this process. See this (https://nginx.org/en/docs/http/ngx_http_core_module.html#directives) for explanations of Nginx configuration properties including ones like 'server_name.'
```
upstream wordle { server  127.0.0.1:3000; server  127.0.0.1:3001; server 127.0.0.1:3002; }

server {
       listen 80;
       listen [::]:80;

       server_name tuffix-vm;
	
	location /login {
		    proxy_pass http://127.0.0.1:3100/login;	
	}
        
	location / {
            auth_request     /auth;
            auth_request_set $auth_status $upstream_status;
	        proxy_pass 	     http://wordle;
        }
	
    location = /auth {
            internal;
            proxy_pass              http://127.0.0.1:3100/login;
            proxy_pass_request_body off;
            proxy_set_header        Content-Length "";
            proxy_set_header        X-Original-URI $request_uri;
        }
        
  	location /register {
            proxy_pass     http://127.0.0.1:3100/register;
        }

}

```
#### Restart Nginx Service
After configuration is done restart the the nginx service.
```
$ sudo service nginx restart

```

### Initializing the Database
Before running the app, run the following command to initialize the database and populate the table.
```
$ ./bin/init.sh

```
### Launching the App
Use the following command to start the app. (3 game service and 1 user service will start)
```
$ foreman start --formation "game_service=3,user_service=1"

```

## Database Structure

#### Users Database:
It contains one table.
- `user`
    - used for authentication
    - contains the `userid`,`username` and `pwd` fields

#### Games Database:
It contains four tables.
- `games`
    - the main game entry
    - a user can have as many games
    - apart from storing the `gameid` and `secretWord`, it also has the `isActive` and `hasWon` flags for tracking the state of the game.
    - `gameid` is the primary key and it has `username` field.
- `guesses`
    - each game can have as many guesses (currently capped at **six** based on project requirements)
    - `gameid` is a foreign key
- `secret_word`
    - this is a lookup table for potential secret words
    - imported from the official Wordle JSON
- `valid_words`
    - this is a lookup table for valid words
    - imported from the official Wordle JSON
    - this includes the secret_words (in contrast to the official Wordle JSON that does not include the secret words in its valid words list)



### User Authentication Routes
#### Registering a new user
```
http POST http://tuffix-vm/register username=<new username> password=<new password>
```
Using a `GET` request will display a message asking to use `POST`. It will also give a `400` error when the username already exists.
#### Logging In
```
http GET http://tuffix-vm/login --auth <username>:<password>

```
Will return `{"authenticated": True}` if properly authenticated.


### Wordle Game Routes
#### Starting a game
```
http --auth <username>:<password> POST http://tuffix-vm/wordle/start

```
This will only create a game. It will return the game ID, if successful. You will need to pass a valid username or else it will respond with a `400` error. It can also respond with a `409` error if any database issue happens.

#### List active games
```
http --auth <username>:<password> GET http://tuffix-vm/wordle/games
```
This lists all the game IDs of the active games of the user. Note that this only lists **active** games -- unfinished games that are below the 6 guess limit.

#### Get the status of a specific game by ID
```
http --auth <username>:<password> GET http://tuffix-vm/wordle/<gameid>/status

```
This retrieves all the relevant information of a particular **active** game. It provides a JSON string in the with the number guesses for the the current game along with all the previous guesses tied to that particular game. Each guess entry contains hints on which letters are in the secret word and in the correct spot or wrong spot.

Return JSON is in the form of:
```
{
    "num_guesses": num_guesses,
    "max_attempts": max_number_of_attempts,
    "guesses": [
        {
            "guess": guess_word,
            "correct_letters": [list of correct letters],
            "correct_indices": [list of correct indices]
        }
    ]
}
```

#### Making a guess
```
http --auth <username>:<password> POST  http://tuffix-vm/wordle/<gameid>/guess guess=<guess_word>

```
After verifying that the game is active and is owned by the username in the request, the `guess_word` is processed accordingly. 

First, the app verifies if it is a valid 5-letter string by checking if it exists in the `valid_words` table. If it does not exist, it will throw an error message accordingly, informing the user that the word is invalid. Invalid words do not affect the number of attempts.

If `guess_word` is valid, the app goes through a series of checks to see if the word is the secret word. If it is not the secret word, it will show the the hints (i.e. which letters in the wrong index and correct index). It will also record this guess as a valid attempt. If the number of guesses reaches the threshold number of attempts, it will end/lock the game (i.e. `isActive = False`). If the the guess was the secret word, it will set the `hasWon` flag to `True`.


## Error Routes
Any other routes or request types not specified above will get a `404` error, along with the following message:
```
{
    "error": "The resource could not be found"
}
```
`409` conflict errors are also caught with its corresponding error messages displayed accordingly.


## Quart-Schema Auto-Generated API Endpoint
Open the following link `http://tuffix-vm/docs` in the browser  while the server is running. It will ask for authentication if not authenticated before. After succeessfull authentication it will show the API Schema (generated by Quart-Schema). You can test all of the routes specified above without needing to use HTTPie.
