from src.web_system import WEB
from src.rooms.regicide_builder import rommBuilder
import asyncio
import src.front_end.tcp_server as tcp_server
import src.front_end.websocket_server as websocket_server
import sys
import atexit

try:
    port_ws = int(sys.argv[1])
except:
    port_ws = 6000
try:
    port_tcp = int(sys.argv[2])
except:
    port_tcp = 7000
UserMax, RoomMax = 10000, 10000


web = WEB(UserMax, RoomMax)
loop = asyncio.get_event_loop()
server_ws = websocket_server.WEBSOCKET_SERVER(web, port_ws, loop)
server_tcp = tcp_server.TCP_SERVER(web, port_tcp, loop)
hall = rommBuilder(web)


atexit.register(web.end_sql)


async def main():
    s_ws = asyncio.create_task(server_ws.serverThreadFunc())
    s_tcp = asyncio.create_task(server_tcp.serverThreadFunc())
    h = asyncio.create_task(hall.start())
    w = asyncio.create_task(web.websystem_message_handler())
    await asyncio.gather(s_tcp, s_ws, h, w, return_exceptions=False)


loop.run_until_complete(main())
