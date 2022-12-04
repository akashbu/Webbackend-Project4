# game_service: hypercorn game_service --reload --debug --bind api.local.gd:$PORT --access-logfile - --error-logfile - --log-level DEBUG
user_service: hypercorn user_service --reload --debug --bind api.local.gd:$PORT --access-logfile - --error-logfile - --log-level DEBUG

game_service_1: ./bin/litefs -config ./etc/primary.yml
game_service_2: ./bin/litefs -config ./etc/secondary1.yml
game_service_3: ./bin/litefs -config ./etc/secondary2.yml
