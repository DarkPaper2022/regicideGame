from webSystem import WEB
import room
from roomBuilder import rommBuilder
import asyncio
import tcpServer
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
    port = int(sys.argv[1])
except:
    port = 6000 + random.randint(0,10)
UserMax,RoomMax = 100,1000
web = WEB(UserMax,RoomMax)
loop = asyncio.get_event_loop()
server = tcpServer.TCP_SERVER(web, port, loop)
hall = rommBuilder(web)
async def main():
    s = asyncio.create_task(server.serverThreadFunc())
    h = asyncio.create_task(hall.start())
    await asyncio.gather(s, h ,return_exceptions=False) 
loop.run_until_complete(main())