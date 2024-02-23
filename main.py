from webSystem import WEB
import game
import asyncio
import tcpServer
import sys

try:
    port = int(sys.argv[1])
except:
    port = 6666
try:
    userMax = int(sys.argv[2])
except:
    userMax = 2
web = WEB(userMax)
server = tcpServer.TCP_SERVER(web, port)
server.start()
Game = game.ROOM(web)
Game.run()
