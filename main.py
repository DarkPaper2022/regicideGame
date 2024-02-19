from webSystem import WEB
import game
import asyncio
import tcpServer

userMax = 2
web = WEB(userMax)
server = tcpServer.TCP_SERVER(web)
server.start()
Game = game.GAME(userMax, web)
Game.run()
