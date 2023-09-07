import socket
import threading
import time

class Client:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', 5555))

        self.recv_thread = threading.Thread(target=self.receive_messages)
        self.recv_thread.start()

        self.name = input("Enter your name: ")
        self.client_socket.send(self.name.encode())

        self.chat_thread = threading.Thread(target=self.send_chat_messages)
        self.chat_thread.start()

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode()
                print("Received message: {}".format(message))
            except Exception as e:
                print("Error receiving message:", str(e))
                break

    def send_chat_messages(self):
        while True:
            message = input("Enter message: ")
            if message == "quit":
                self.client_socket.send(message.encode())
                break
            else:
                self.client_socket.send(message.encode())

def main():
    client = Client()

if __name__ == '__main__':
    main()
