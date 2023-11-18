# =================================================================================================
# Contributing Author:	Alex Johnston  
# Email Address: amjohnston9@gmail.com        
# Date: 11/17/2023                     
# Purpose: This program is the client that the player uses to play the game.  it sends and receives
#          from the server about the game to continually update the game state allowing the user to play
#          someone using another client                 
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import pickle
import threading
import time

from assets.code.helperCode import *

# This is the main game loop.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0

    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =======================================================================================================
        #Purpose: The Purpose of this section of code is to take the users inputs and send them to the server
        #         Then it takes the data of the other client from the server and decodes it
        #         It then takes this data and uses it to update the game state. It also compares
        #         The sync values of itself and the other client, and if it has lagged behind it uses
        #         The other clients data to update the game
        #Preconditions: The section of code expects the client to beconnected to the server and and
        #               for the another client to be connected to the server and running the play game function       
        #Postconditions: After this section of code is run the score, opponents paddle movement and the sync num
        #                are updated, and if the client is out of sync, the ball pos and movement, the users score
        #                paddle position, and sync num are updated to catch up to the other client.
        #=========================================================================================================       
        
        # Determine which score to send based on the client's paddle side
        if playerPaddle == "left":
            # scoreTemp is the User's score needing to be sent to the opponent, 
            # and altScore is the Opponent's score being sent to verify the opponent isn't behind
            scoreTemp = lScore
            altScore = rScore
        else:
            scoreTemp = rScore
            altScore = lScore

        # Store the direction the paddle is moving as a variable to send
        direction = playerPaddleObj.moving
        
        # Create a list including all data necessary for the opponenet client to receive
        data_list = [playerPaddle, direction, scoreTemp, sync, opponentPaddleObj, ball, altScore]

        # Put the list in Pickled format and send it to the server
        encoded_list = pickle.dumps(data_list)

        client.send(encoded_list)
        
        try: 
            # Try to receive data from server
            rec_list = client.recv(1024)
        except:
            print("Error receiving data.")
        else:
            # Check if the data received isn't empty
            if len(rec_list) > 0:
                # Load data
                opp_list = pickle.loads(rec_list)

                if opp_list[0] == "left" or "right":
                    # Update the direction in which the opponent paddle is moving
                    opponentPaddleObj.moving = opp_list[1]

                    # Update the opponent score based on what it sends
                    if playerPaddle == "left":
                        rScore = opp_list[2]
                    else:
                        lScore = opp_list[2]
                else: 
                    break
                
                # Check if the client's are out of sync
                if opp_list[3] > sync:
                    # If they are, manually update each variable to match the client that is ahead
                    if playerPaddle == "left":
                        lScore == opp_list[6]
                    else:
                        rScore = opp_list[6]
                    playerPaddleObj = opp_list[4]
                    ball = opp_list[5]
                    sync = opp_list[3]


      ## =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
            pygame.display.flip()  # Update the display to show the message

            time.sleep(3) # Show the win message for 3 seconds

            # Display a message notifying the user that the game will close soon
            for i in range(5, 0, -1):
                print("Game will end in: ", i)
                time.sleep(1)
            sys.exit()
        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update([topWall, bottomWall, ball, leftPaddle, rightPaddle, scoreRect, winMessage])
        clock.tick(60)
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1


# This is where you will connect to the server to get the info required to call the game loop.
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    #===================================================================================================================
    # Purpose: This section of code attempts to connect the client to the server, receive the necessary information for the 
    #          client to start the game, then start the game once two clients are ready.
    # Preconditions: This code is ran in concurrence with the startScreen function.
    # Postconditions: After this code is ran, both clients will start the game loop.
    #===================================================================================================================

    # Initiate client object and connect to the server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = int(port)
    client.connect((ip, port))

    # Get the required information from the server (screen width, height & player paddle, "left" or "right")
    screenWidth = client.recv(1024).decode()
    screenWidth = int(screenWidth)
    screenHeight = client.recv(1024).decode()
    screenHeight = int(screenHeight)
    paddleSide = client.recv(1024).decode()

    # If you have messages you'd like to show the user use the errorLabel widget like so
    errorLabel.config(text=f"Some update text. Your input: IP: {ip}, Port: {port}")
    # You may or may not need to call this, depending on how many times you update the label
    errorLabel.update()     

    
    # Close this window and start the game with the info passed to you from the server

    # Send a message to the server that the client is ready to start the game
    client.send(b"ready")

    errorLabel.config(text = f"Waiting for another user to start the game...")
    errorLabel.update()

    flag = 0
    # Wait until the client receives confirmation from the server that both clients are ready before starting the game
    while flag == 0:
        if client.recv(1024).decode() == "start":
            flag = 1
    
    
    app.withdraw()     # Hides the window 
    playGame(screenWidth, screenHeight, paddleSide, client)  # User will be either left or right paddle
    app.quit()         # Kills the window


def startScreen():

    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":

    startScreen()
