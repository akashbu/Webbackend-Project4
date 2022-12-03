# game_service: hypercorn game_service --reload --debug --bind api.local.gd:$PORT --access-logfile - --error-logfile - --log-level DEBUG
leaderboard_service: hypercorn leaderboard_service --reload --debug --bind api.local.gd:$PORT --access-logfile - --error-logfile - --log-level DEBUG
user_service: hypercorn user_service --reload --debug --bind api.local.gd:$PORT --access-logfile - --error-logfile - --log-level DEBUG

primary: ./bin/litefs -config ./etc/primary.yml
secondary1: ./bin/litefs -config ./etc/secondary1.yml
secondary2: ./bin/litefs -config ./etc/secondary2.yml
