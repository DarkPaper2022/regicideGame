import web_pipe_ver
import game
import asyncio
import tcpServer

userMax = 2
web = web_pipe_ver.WEB(userMax)
#player = web_pipe_ver.PLAYER_TERMINAL(web)
server = tcpServer.TCP_SERVER(web)
server.start()
Game = game.GAME(userMax, web)
Game.run()
