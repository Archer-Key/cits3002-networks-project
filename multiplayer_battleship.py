from battleship import Board, BOARD_SIZE, SHIPS, parse_coordinate

def run_multiplayer_game_online(client, opponent, game):
    rfile = client.rfile
    wfile = client.wfile

    def send(msg):
        wfile.write(msg + '\n')
        wfile.flush()

    def send_board(board, show_hidden_board=False):
        
        grid_to_send = board.hidden_grid if show_hidden_board else board.display_grid
        
        wfile.write("GRID\n")
        wfile.write("  " + " ".join(str(i + 1).rjust(2) for i in range(board.size)) + '\n')
        for r in range(board.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(grid_to_send[r][c] for c in range(board.size))
            wfile.write(f"{row_label:2} {row_str}\n")
        wfile.write('\n')
        wfile.flush()
    
    def recv():
        msg = rfile.readline().strip()
        if (len(msg) == 0): # client disconnected
            client.handle_disconnect()
        return(msg)

    def orientation_str(orientation):
        return "vertically" if orientation else "horizontally"
    
    def place_ships_manually(ships=SHIPS):
        board = Board()
        send("Please place your ships on the board.")
        orientation = 0
        for ship_name, ship_size in ships:
            while True:
                # Send user prompt to place ship
                send_board(board, show_hidden_board=True)
                send(f"Placing {ship_name} (size {ship_size}) {orientation_str(orientation)}. Enter 'x' to change orientation.")
                
                # Handle user input
                coord_str = recv().strip().upper() 
                try:
                    if coord_str[0] == 'X':
                        orientation = 1 - orientation
                        continue 
                    row, col = parse_coordinate(coord_str)
                except ValueError as e:
                    send(f"[!] Invalid coordinate: {e}")
                    continue
                    
                # Check if we can place the ship
                if board.can_place_ship(row, col, ship_size, orientation):
                    occupied_positions = board.do_place_ship(row, col, ship_size, orientation)
                    board.placed_ships.append({
                        "name": ship_name,
                        "positions": occupied_positions
                    })
                    break
                else:
                    send(f"[!] Cannot place {ship_name} at {coord_str} (orientation={orientation_str(orientation)}). Try again.")
        
        # Show the user their full board
        client.set_board(board)
        send_board(client.board, show_hidden_board=True)
        send("All ships placed!")
        
        # Wait for opponent to finish placing their ships
        send("Waiting for opponent...")
        while (opponent.board == None):
            pass
    
    def battle_loop():
        moves = 0
        while game.active:
            if (client.player_id == game.player_turn):
                send_board(opponent.board)
                send("enter coordinate to fire at (e.g. B5):")
                guess = recv()
                if guess.lower() == "quit":
                    send("Thanks for playing. Goodbye.")
                    return
                
                try:
                    row, col = parse_coordinate(guess)
                    result, sunk_name = opponent.board.fire_at(row, col)
                    moves += 1

                    if result == 'hit':
                        if sunk_name:
                            send(f"HIT! You sank the {sunk_name}!")
                        else:
                            send("HIT!")
                        if opponent.board.all_ships_sunk():
                            send_board(opponent.board)
                            send(f"Congratulations! You sank all ships in {moves} moves.")
                            game.end()
                            return
                        game.end_turn()
                    elif result == 'miss':
                        send("MISS!")
                        game.end_turn()
                    elif result == 'already_shot':
                        send("You've already fired at that location.")
                except ValueError as e:
                    send(f"Invalid input: {e}")
            else:
                pass

    def main():
        place_ships_manually()
        game.start_battle() # this should be called by an external event
        battle_loop()
        
    main()
