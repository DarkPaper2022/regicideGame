from webSystem import WEB
import room
from roomBuilder import rommBuilder
import asyncio
import tcpServer
import sys

try:
    port = int(sys.argv[1])
except:
    port = 6666
UserMax,RoomMax = 100,40
web = WEB(UserMax,RoomMax)
server = tcpServer.TCP_SERVER(web, port)
server.start()
hall = rommBuilder(web)
hall.start()
