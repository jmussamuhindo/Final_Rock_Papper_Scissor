import socket
import threading
import time

class Player:
    def __init__(self, name, conn, addr, hp):
        self.name = name
        self.conn = conn
        self.addr = addr
        self.hp = hp
        self.challenged = False
        self.challenge_opponent = None
        self.choice = None
        self.challenge_timer = None



class LastManStandingServer:
    def __init__(self, num_players, initial_hp):
        self.num_players = num_players
        self.initial_hp = initial_hp
        self.players = []
        self.challenge_pairs = []
        self.chat_msgs = []

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', 5555))
        self.server_socket.listen(10)

        self.chat_lock = threading.Lock() 
        self.challenge_lock = threading.Lock()
        
    def send_message_to_player(self, player, message):
        message_with_hp = "[{} - HP: {}] {}".format(player.name, player.hp, message)
        player.conn.send(message_with_hp.encode())

    def send_player_list(self):
        player_list = "Player List:\n"
        for player in self.players:
            player_list += "{} - HP: {}\n".format(player.name, player.hp)

        for player in self.players:
            self.send_message_to_player(player, player_list)

    def start(self):
        print("Server started. Waiting for connections...")

        while len(self.players) < self.num_players:
            conn, addr = self.server_socket.accept()
            name = conn.recv(1024).decode()
            player = Player(name, conn, addr, self.initial_hp)
            self.players.append(player)
            self.send_player_list()

            if len(self.players) == self.num_players:
                self.start_game()

    def start_game(self):
        print("Game started!")

        chat_thread = threading.Thread(target=self.handle_chat_messages)
        chat_thread.start()

        challenge_thread = threading.Thread(target=self.handle_challenges)
        challenge_thread.start()

        for player in self.players:
            threading.Thread(target=self.handle_player, args=(player,)).start()

    def handle_player(self, player):
        self.send_message_to_player(player, "Game started! You have {} HP.\n You can challenge other players by sending 'challenge <player_name> <choice>.\n Choices: R (Rock), P (Paper), S (Scissors)\n Example: challenge player2 R\n use 'choice <choice>' to respond to a challenge. Example: choice P\n ".format(player.hp)), 

        while player.hp > 0:
            data = player.conn.recv(1024).decode().strip()
            if data.startswith("challenge"):
                self.handle_challenge(player, data)
            elif data == "quit":
                self.remove_player(player)
                break
            elif data.startswith("chat"):
                self.handle_chat(player, data)
            elif data.startswith("choice"):
                self.handle_choice(player, data)  # New function to handle player's choice
                if player.hp <= 0:
                    self.remove_player(player)

    
    def handle_choice(self, player, data):
        parts = data.split()
        if len(parts) == 2:
            command, choice = parts
            if choice in ["R", "P", "S"]:
                player.choice = choice
                self.send_message_to_player(player, "You chose {}.".format(choice))
            else:
                self.send_message_to_player(player, "Invalid choice. Choices: R (Rock), P (Paper), S (Scissors)")
        else:
            self.send_message_to_player(player, "Invalid command. Format: 'choice <choice>'")

    def handle_challenge(self, challenger, data):
        with self.challenge_lock:
            if not challenger.challenged:
                parts = data.split()
                if len(parts) == 3:
                    command, opponent_name, choice = parts
                    if choice in ["R", "P", "S"]:
                        opponent = self.get_player_by_name(opponent_name)
                        if opponent:
                            if opponent != challenger:
                                if not opponent.challenged:
                                    if not self.is_player_challenged(opponent):
                                        self.send_message_to_player(challenger, "You challenged {} with {}.".format(opponent_name, choice))
                                        self.send_message_to_player(opponent, "{} challenged you.".format(challenger.name))
                                        challenger.challenged = True
                                        opponent.challenged = True
                                        challenger.choice = choice
                                        self.challenge_pairs.append((challenger, opponent))

                                        # Start a timer for 10 seconds
                                        t = threading.Timer(10.0, self.void_challenge, args=(challenger, opponent))
                                        t.start()
                                    else:
                                        self.send_message_to_player(challenger, "{} is already challenged by someone else.".format(opponent_name))
                                else:
                                    self.send_message_to_player(challenger, "{} is already in a challenge.".format(opponent_name))
                            else:
                                self.send_message_to_player(challenger, "You cannot challenge yourself.")
                        else:
                            self.send_message_to_player(challenger, "{} is not a valid player.".format(opponent_name))
                    else:
                        self.send_message_to_player(challenger, "Invalid choice. Choices: R (Rock), P (Paper), S (Scissors)")
                else:
                    self.send_message_to_player(challenger, "Invalid command. Format: 'challenge <player_name> <choice>'")
            else:
                self.send_message_to_player(challenger, "You are already in a challenge.")

    def handle_challenges(self):
        while True:
            with self.challenge_lock:
                new_challenge_pairs = []
                for challenger, opponent in self.challenge_pairs:
                    if challenger.choice and opponent.choice:  # if both made a choice
                        self.send_message_to_player(challenger, "You and {} made a choice. Starting challenge.".format(opponent.name))
                        self.send_message_to_player(opponent, "You and {} made a choice. Starting challenge.".format(challenger.name))
                        self.handle_challenge_response(challenger, opponent)
                        challenger.choice = None
                        opponent.choice = None
                        challenger.challenged = False
                        opponent.challenged = False
                        challenger.challenge_opponent = None
                    else:  # if one or both have not made a choice, keep them in the challenge_pairs
                        new_challenge_pairs.append((challenger, opponent))
                self.challenge_pairs = new_challenge_pairs
            time.sleep(1)  # sleep for 1 second to avoid excessive CPU usage
    
    def broadcast_message(self, message):
        for player in self.players:
            self.send_message_to_player(player, message)

    def cancel_timer(self):
        if self.challenge_timer is not None:
            self.challenge_timer.cancel()
            self.challenge_timer = None

    def handle_challenge_response(self, challenger, opponent):
        if challenger.choice == opponent.choice:
            self.send_message_to_player(challenger, "It's a draw with {}.".format(opponent.name))
            self.send_message_to_player(opponent, "It's a draw with {}.".format(challenger.name))
        else:
            if (challenger.choice == "R" and opponent.choice == "S") or \
                (challenger.choice == "S" and opponent.choice == "P") or \
                (challenger.choice == "P" and opponent.choice == "R"):
                opponent.hp -= 1
                challenger.hp += 1
                self.send_message_to_player(challenger, "You won the challenge against {}.".format(opponent.name))
                self.send_message_to_player(opponent, "You lost the challenge against {}.".format(challenger.name))
            else:
                opponent.hp += 1
                challenger.hp -= 1
                self.send_message_to_player(challenger, "You lost the challenge against {}.".format(opponent.name))
                self.send_message_to_player(opponent, "You won the challenge against {}.".format(challenger.name))

        if challenger.hp <= 0:
            self.send_message_to_player(challenger, "You have lost all your HP. You are out of the game.")
            self.remove_player(challenger)
            self.broadcast_message("{} has been eliminated from the game.".format(challenger.name))
            if len(self.players) == 1:
                self.broadcast_message("{} is the last player standing. They are the winner!".format(self.players[0].name))
        if opponent.hp <= 0:
            self.send_message_to_player(opponent, "You have lost all your HP. You are out of the game.")
            self.remove_player(opponent)
            self.broadcast_message("{} has been eliminated from the game.".format(opponent.name))
            if len(self.players) == 1:
                self.broadcast_message("{} is the last player standing. They are the winner!".format(self.players[0].name))
    
    def void_challenge(self, challenger, opponent):
        # If the opponent has not responded, void the challenge
        if opponent.choice is None:
            self.send_message_to_player(challenger, "Your challenge against {} has been voided.".format(opponent.name))
            self.send_message_to_player(opponent, "You didn't respond to the challenge from {} in time.".format(challenger.name))
            challenger.challenged = False
            opponent.challenged = False
        elif opponent.choice:
            opponent.cancel_timer()

    def is_player_challenged(self, player):
        for pair in self.challenge_pairs:
            if player in pair:
                return True
        return False

    def remove_player(self, player):
        self.players.remove(player)
        player.conn.close()
        # Remove player from any active challenges
        self.challenge_pairs = [(challenger, opponent) for (challenger, opponent) in self.challenge_pairs if challenger != player and opponent != player]
        self.send_player_list()  # Broadcast updated player list
    
    def get_player_by_name(self, name):
        for player in self.players:
            if player.name == name:
                return player
        return None

    def handle_chat(self, player, data):
        parts = data.split(maxsplit=1)
        if len(parts) == 2:
            message = parts[1]
            with self.chat_lock:
                self.chat_msgs.append((player.name, message))

    def handle_chat_messages(self):
        while True:
            time.sleep(0.1)
            with self.chat_lock:
                if self.chat_msgs:
                    for player in self.players:
                        for name, message in self.chat_msgs:
                            if player.name != name:
                                self.send_message_to_player(player, "[{}] {}".format(name, message))
                    self.chat_msgs = []

def main():
    num_players = int(input("Enter the number of players: "))
    initial_hp = int(input("Enter the initial HP: "))

    server = LastManStandingServer(num_players, initial_hp)
    server.start()

if __name__ == '__main__':
    main()
