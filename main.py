from webSystem import WEB
import room
from roomBuilder import rommBuilder
import asyncio
import tcpServer
import webSocketServer
import sys
import random

async def logggggg(yes):
    cnt = 0
    while True:
        cnt += 1
        print(f"{cnt}   {yes}")
        tasks = asyncio.all_tasks()
        for task in tasks:
            print(task)
        await asyncio.sleep(5)

try:    
    port_ws = int(sys.argv[1])
except:
    port_ws = 6000 + random.randint(0,9)
try:    
    port_tcp = int(sys.argv[2])
except:
    port_tcp = 7000 + random.randint(0,9)
UserMax,RoomMax = 100,1000
web = WEB(UserMax,RoomMax)
loop = asyncio.get_event_loop()
server_ws = webSocketServer.WEBSOCKET_SERVER(web, port_ws, loop)
server_tcp = tcpServer.TCP_SERVER(web,port_tcp,loop)
hall = rommBuilder(web)
async def main():
    s_ws = asyncio.create_task(server_ws.serverThreadFunc())
    s_tcp = asyncio.create_task(server_tcp.serverThreadFunc())
    h = asyncio.create_task(hall.start())
    w = asyncio.create_task(web.websystem_message_handler())
    await asyncio.gather(s_tcp,s_ws ,h, w ,return_exceptions=False) 
loop.run_until_complete(main())