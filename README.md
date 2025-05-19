# cits3002-networks-project

## Using BEER
To get the game running you must:
1. Start a Server
    - a server is started through `python server.py`
2. Start Clients
    - each client is started through `python client.py`
    - a client is unable to connect to the server until a non-null username is entered
    - the first 2 connections will be players with subsequent clients joining as spectators
3. Running through game
    - each player follows the on instructions provided

## Valid Commands
the players have the following commands to use
- CHAT - broadcasts a message to all other players
- FIRE \<Coordinates> - fires a missile at coordinates if in firing stage
- PLACE \<Coordinates> - places a ship in previously set orientation if in placing stage
- QUIT - disconnects player from server