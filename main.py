from webSystem import WEB
import room
from roomBuilder import rommBuilder
import asyncio
import tcpServer
import sys

try:    
    port = int(sys.argv[1])
except:
    port = 6007
UserMax,RoomMax = 100,1000
web = WEB(UserMax,RoomMax)
loop = asyncio.get_event_loop()
server = tcpServer.TCP_SERVER(web, port, loop)
hall = rommBuilder(web)
async def main():
    await server.start()
    await hall.start()
    return None
loop.run_until_complete(main())