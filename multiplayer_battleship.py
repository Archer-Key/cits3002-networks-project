from battleship import Board, BOARD_SIZE, SHIPS, parse_coordinate

def run_multiplayer_game_online(rfile, wfile, opponent):
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
    
    def send_opponent(msg):
        opponent.wfile.write(msg + '\n')
        opponent.wfile.flush()

    def recv():
        return rfile.readline().strip()

    def get_user_input():
        while True:
            user_input = recv()
            if user_input != "":
                return user_input
    
    def orientation_str(orientation):
        return "vertically" if orientation else "horizontally"
    
    def place_ships_manually(board, ships=SHIPS):
        send("Please place your ships on the board.")
        orientation = 0
        for ship_name, ship_size in ships:
            while True:
                # Send user prompt to place ship
                send_board(board, show_hidden_board=True)
                send(f"Placing {ship_name} (size {ship_size}) {orientation_str(orientation)}. Enter 'x' to change orientation.")
                
                # Handle user input
                coord_str = get_user_input().strip().upper() # This may need a new thread
                if coord_str[0] == 'X':
                  orientation = 1 - orientation
                  continue 
                try:
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
        send_board(board, show_hidden_board=True)
        send("All ships placed!")

    def main():
        board = Board()
        place_ships_manually(board)

        while True:
            pass
    
    main()


    

