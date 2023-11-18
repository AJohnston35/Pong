# =================================================================================================
# Contributing Author:	Alex Johnston   
# Email Address: amjohnston9@gmail.com        
# Date: 11/17/2023                     
# Purpose: This program acts as the server with which the two clients use to communicate between each other                  
# =================================================================================================

import socket
from _thread import *
import threading
import time
import pickle

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games


# The server needs to communicate with two clients simultaneously 
# over a network using sockets.  It will need to use threads to handle 
# the two simultaneous clients.  It is responsible for relaying the location 
# of the other player’s paddle to the client, the location of the ball and the current score.  

# Initialize all global variables
print_lock = threading.Lock()
screenWidth = str(640)
screenHeight = str(480)
counter = 0
leftAddr = 0
rightAddr = 0

#================================================================================================================
# Purpose: The purpose of this class is to contain all the functions needed to connect to the clients and share
#          information between the two so the game can be played from different clients
# Preconditions: The class is intialized when the program is started
# Postconditions: When all the functions in the thread class are done running the game should be over
#================================================================================================================
class ThreadedServer(object):

    #=================================================================================================================
    # Purpose: The purpose of this function is to initialize the variables that will be used to connect to the clients
    # Preconditions: This function expects to be called after the server program has started
    # Postconditions: After it has been called all the varaibles will have been initalized so it can connect
    #                 to the clients
    #=================================================================================================================
    def __init__(self,host:str,port:int) -> None:
        self.host = host
        self.port = port
        self.ready_clients = 0
        self.game_started = threading.Event()
        self.client_sockets = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # If the host and port are already bound, don't do anything
        try:
            self.sock.bind((self.host,self.port))
        except:
            pass
    
    #===============================================================================================================
    # Purpose: The purpose of this function is to listen for clients to connect to the server. After a client
    #          has connected the server assigns it to the left or right side and sends it the size of the game
    #          Window. It then waits until both the left side and right side client have sent ready before calling
    #          start_game
    # Preconditions: This function expects to be called after the server has been started and for __init__ to
    #                have initialized the variables needed to connect to clients
    # Postconditions: After the function has been called any clients that have connected will have been given
    #                 a position to play in and the size of the game window, and if two clients have connected
    #                 and are ready to play it will call start_game so they can begin
    #===============================================================================================================
    def listen(self) -> None:
        self.sock.listen(5)
        while True:
            # Accept the connection from client
            client, address = self.sock.accept()

            # Add the client to a list of clients
            self.client_sockets.append(client)

            global screenHeight
            global screenWidth
            global counter
            global leftAddr
            global rightAddr

            # Counter variable to determine how many current client connections there are
            counter = counter + 1
            
            # Send the screenWidth and screenHeight to the client and allow time for the client to receive it
            client.send(screenWidth.encode())
            time.sleep(1)
            
            client.send(screenHeight.encode())
            time.sleep(1)

            # First client connected becomes the left paddle, second becomes the right paddle
            if counter == 1:
                paddleSide = "left"
                leftAddr = address
                client.send(paddleSide.encode())
            elif counter == 2:
                paddleSide = "right"
                rightAddr = address
                client.send(paddleSide.encode())
                # Reset counter for next client to join
                counter = 0

            # Increment the ready_clients counter when a client confirms readiness
            if client.recv(1024).decode() == "ready":
                self.ready_clients += 1

            # Check if both clients are ready to start the game
            if self.ready_clients == 2:
                self.start_game()
            
            client.settimeout(60)
            threading.Thread(target = self.listenToClient, args = (client, address)).start()

    #=============================================================================================================
    # Purpose: The purpose of this function is to send a start message to two clients about to play so they start
    #          at the same time
    # Preconditions: This function expects at least two clients to be connected to the server and for both to have
    #                sent the ready message signifying that both are waiting in the while loop to start
    # Postconditions: After this function has run both clients will exit the while loop before playGame and
    #                 start the game     
    #==============================================================================================================
    def start_game(self) -> None:
        # Signal both clients to start the game
        for client in self.client_sockets:
            client.sendall(b"start")
        
        self.game_started.set()

    #================================================================================================================
    # Purpose: The purpose of this function is to take the data recieved by a client and send it to the other
    #          client
    # Preconditions: This function expects at least two clients to be connected to  the server and running playGame
    # Postconditions: After this function has run the data sent by one client will have been sent to the other client
    #================================================================================================================
    def HandlePickledData(self, data: bytes, client: socket.socket) -> None:
        # Load data and send it to any client in the list besides itself
        received_data = pickle.loads(data)
        other_client = next(sock for sock in self.client_sockets if sock != client)
        other_client.sendall(pickle.dumps(received_data))
    
    #============================================================================================================
    # Purpose: The purpose of this function is to take the data from one of the client and make sure
    #          It is the appropriate data type before sending it to HandlePickledData to be processed
    # Preconditions: This function expects there to be a client connected to the server and that client
    #                has begun the playGame function
    # Postconditions: After this function has called the data sent by the client is sent to HandlePickled Data
    #                 so it can be sent to the other client
    #============================================================================================================
    def listenToClient(self, client: socket.socket, address: Tuple[str, int]) -> None:
        # Size of the incoming data
        size = 1024
        # Continuously listen for messages from the clients
        while True:
            try:
                # Try to receive the incoming data 
                data = client.recv(size)
                if data:
                    try:
                        # Try to load the pickled data and have an exception for data tbat is not pickled
                        pickle.loads(data)
                    except:
                        # Set the response to echo back the received data
                        print("Error pickling data")
                        response = data
                        client.send(response)
                    else:
                        # If the data is pickled then call the function to handle it
                        self.HandlePickledData(data, client)
                else:
                    # If no data is received then the client is disconnected
                    raise error('Client disconnected')
            except:
                print("Closing client")
                client.close()

                # Remove the disconnected client from the list
                self.client_sockets.remove(client)
                # Check if all clients are disconnected
                if len(self.client_sockets) == 0:
                    print("All clients disconnected. Resuming listening...")
                    self.__init__(self.host, self.port) # Clear any existing variables
                    self.listen()  # Call the listen method to wait for more connections
                break

    
#===================================================================================================================
# Purpose: This section of code asks the user to select a port for the server to use. Then if the user selects
#          empty port, the program sets up the server at the designated port and begins to listen for clients
#          trying to connect to the server
# Preconditions: This code is run when the program starts after variables have been initialized
# Postconditions: After this code has run the server should be waiting for clients to connect
#==============================================================================================================
if __name__ == '__main__':
    while True:
        # Import the IP and port number at runtime
        IP = input("IP Address: ")
        port_num = input("Port: ")
        try:
            # If an eligible port number is not provided then raise an exception
            port_num = int(port_num)
            break
        except ValueError:
            pass
    
    #### TO TEST IT WITH ANOTHER CLIENT MAKE SURE YOU ARE ON THE SAME CONNECTION ####
    ThreadedServer(IP,port_num).listen()
