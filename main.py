from webSystem import WEB
import room
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
Game = room.ROOM(web)
Game.roomThreadingFunc()
