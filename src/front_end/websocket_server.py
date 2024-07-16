import socket
import uuid
from websockets.server import serve, WebSocketServerProtocol
import asyncio
import time
import json
from include.myLogger import logger
from typing import List, Any, Tuple, Union, Optional
from src.web_system import WEB

from include.defineRegicideMessage import (
    TALKING_MESSAGE,
    FROZEN_STATUS_PARTLY,
    REGICIDE_DATATYPE,
)

from include.defineWebSystemMessage import (
    MESSAGE,
    playerWebSystemID,
    WEB_SYSTEM_DATATYPE,
    DATATYPE,
    DATATYPE_tuple,
    DATA_UPDATE_PLAYER_STATUS,
    FROZEN_ROOM_STATUS_inWebSystem,
    DINAL_TYPE,
    DATA_ANSWER_CONNECTION,
    FROZEN_GAME_TYPE,
)

from dataclasses import dataclass
from include.defineError import AuthDenial, MessageFormatError, RegisterDenial
from include.JSON_tools import strToCard, ComplexFrontEncoder
from include.JSON_tools import *
from include.defineRound import ROUND


class WEBSOCKET_CLIENT:
    websocket: WebSocketServerProtocol
    systemID: Optional[playerWebSystemID]
    playerCookie: Optional[uuid.UUID]
    userName: Optional[str]  # be careful, once initialized it should never be changed
    web: WEB
    roomID: int

    def __init__(self, websocket, web, timeOutSetting: int) -> None:
        self.websocket = websocket
        self.web = web
        self.socket_over_flag = False
        self.timeOutSetting = timeOutSetting
        self.roomID = -1
        self.player_exit_event = asyncio.Event()
        self.player_exit_event.clear()

    async def playerMannage(self):
        try:
            await self.websocket.send(
                json.dumps(
                    MESSAGE(
                        roomData=None,
                        playerID=playerWebSystemID(-1),
                        roomID=-1,
                        data_type=WEB_SYSTEM_DATATYPE.ANSWER_CONNECTION,
                        webData=DATA_ANSWER_CONNECTION(tuple(self.web.games)),
                    ),
                    cls=ComplexFrontEncoder,
                )
            )
            checked = await self.check_game_version()
        except Exception as e:
            self._player_exit()
            return
        if not checked:
            await self._socket_exit()
            return

        while not self.socket_over_flag:
            self.player_exit_event.clear()
            await self.authThread()

    async def _socket_exit(self):
        self.socket_over_flag = True
        self._player_exit()
        try:
            await self.websocket.close()
        finally:
            return

    def _player_exit(self):
        self.roomID = -1
        self.userName = None
        self.playerCookie = None
        self.systemID = None
        self.player_exit_event.set()

    # ret: optional
    # raise: no exception
    def _socket_read(self, socket_data: str) -> Optional[Tuple[DATATYPE, Any]]:
        try:
            data_type, data = json.loads(socket_data, object_hook=json_1_obj_hook)
            assert isinstance(data_type, DATATYPE_tuple)
            return data_type, data
        except:
            logger.error(socket_data)
            return None

    async def authThread(self):

        while True:
            socket_data = str(await self.websocket.recv())
            if not socket_data:
                await self._socket_exit()
                return
            re = self._socket_read(socket_data)
            if re is None:
                continue
            else:
                data_type = re[0]
                data = re[1]
            if data_type == WEB_SYSTEM_DATATYPE.ASK_REGISTER:
                reg_data: DATA_ASK_REGISTER = data
                try:
                    self.web.PLAYER_REGISTER(
                        playerName=reg_data.username,
                        password=reg_data.password,
                    )
                    await self.websocket.send(
                        json.dumps(
                            MESSAGE(
                                roomData=None,
                                playerID=playerWebSystemID(-1),
                                roomID=-1,
                                data_type=WEB_SYSTEM_DATATYPE.ANSWER_REGISTER,
                                webData=DATA_SIMPLE_ANSWER(
                                    success=True,
                                    error=None,
                                ),
                            ),
                            cls=ComplexFrontEncoder,
                        )
                    )
                except RegisterDenial as e:
                    await self.websocket.send(
                        json.dumps(
                            MESSAGE(
                                roomData=None,
                                playerID=playerWebSystemID(-1),
                                roomID=-1,
                                data_type=WEB_SYSTEM_DATATYPE.ANSWER_REGISTER,
                                webData=DATA_SIMPLE_ANSWER(
                                    success=False,
                                    error=DINAL_TYPE.REGISTER_FORMAT_WRONG,
                                ),
                            ),
                            cls=ComplexFrontEncoder,
                        )
                    )
            elif data_type == WEB_SYSTEM_DATATYPE.ASK_LOG_IN:
                try:
                    login_data: DATA_ASK_LOGIN = data
                    self.playerCookie, self.systemID, _ = self.web.PLAYER_LOG_IN(
                        playerName=login_data.username,
                        password=login_data.password,
                    )
                    username = login_data.username
                    break
                except TimeoutError as e:
                    logger.error(str(e))
                except AuthDenial as e:
                    await self.websocket.send(
                        json.dumps(
                            MESSAGE(
                                roomID=-1,
                                roomData=None,
                                playerID=playerWebSystemID(-1),
                                data_type=WEB_SYSTEM_DATATYPE.ANSWER_LOGIN,
                                webData=DATA_SIMPLE_ANSWER(
                                    success=False,
                                    error=e.args[0],
                                ),
                            ),
                            cls=ComplexFrontEncoder,
                        )
                    )
            else:
                logger.error("format")

        self.userName = username
        rec = asyncio.create_task(self.recvThreadFunc())
        sen = asyncio.create_task(self.sendThreadFunc())
        log_out = asyncio.create_task(self.player_exit_event.wait())
        done, pending = await asyncio.wait(
            [rec, sen, log_out], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

    # recv From  netcat
    async def recvThreadFunc(self):
        if self.playerCookie is None or self.userName is None:
            raise Exception("Bad logic: auth func don't provide a cookie.")
        while True:
            try:
                data = str(await self.websocket.recv())
                if not data:
                    break
                message = self.dataToMessage(data)
                self.web.player_send_message(message, self.playerCookie)
                if message.data_type == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    break
            except MessageFormatError as e:
                logger.debug(str(e))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(str(e))
                break
        self._player_exit()

    # send To netcat
    async def sendThreadFunc(self):
        if self.playerCookie is None or self.systemID is None:
            raise Exception("Bad logic: auth func don't provide a cookie.")
        while True:
            message = await self.web.playerGetMessage(self.systemID, self.playerCookie)
            data = self.messageToData(message)
            try:
                await self.websocket.send(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                break
            if message.data_type == WEB_SYSTEM_DATATYPE.cookieWrong:
                break
        self._player_exit()

    # error MessageFormatError if bytes are illegal
    def dataToMessage(self, socket_data: str) -> MESSAGE:

        re = self._socket_read(socket_data)
        if re is None:
            raise MessageFormatError(f"{socket_data}")
        else:
            data_type = re[0]
            data = re[1]
        try:
            room_ID = -1 if type(data_type) == WEB_SYSTEM_DATATYPE else self.roomID
            room_data: Any = None
            web_data = None
            if data_type == REGICIDE_DATATYPE.card:
                card_data: Tuple[int, ...] = data
                room_data = card_data
            elif data_type == REGICIDE_DATATYPE.SPEAK:
                speak_data: str = data
                assert self.userName is not None
                room_data = TALKING_MESSAGE(time.time(), self.userName, speak_data)
            elif data_type == REGICIDE_DATATYPE.confirmJoker:
                joker_data: int = data
                room_data = joker_data
            elif data_type == WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM:
                join_data: int = data
                web_data = join_data
            elif data_type == WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM:
                create_data: int = data
                web_data = create_data
            else:
                pass
        except:
            raise MessageFormatError("Fuck you!")
        assert self.systemID is not None
        message = MESSAGE(room_ID, self.systemID, data_type, room_data, web_data)
        return message

    # Warning: not math function, self.room changed here
    def messageToData(self, message: MESSAGE) -> str:
        if message.data_type == WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS:
            room_status: DATA_UPDATE_PLAYER_STATUS = message.webData
            self.roomID = (
                -1 if room_status.playerRoom is None else room_status.playerRoom.roomID
            )
        if message.roomID != self.roomID and message.roomID != -1:
            logger.error(f"奇怪的信号?\n")
        data = json.dumps(message, cls=ComplexFrontEncoder)
        logger.debug(f"send json: {data}")
        return data

    async def check_game_version(self) -> bool:
        socket_data = str(await self.websocket.recv())
        if not socket_data:
            return False
        re = self._socket_read(socket_data)
        if re is None:
            return False
        else:
            data_type = re[0]
            data = re[1]
        if data_type != WEB_SYSTEM_DATATYPE.ASK_CONNECTION:
            return False
        else:
            game_and_version: FROZEN_GAME_TYPE = data
            return self.web._check_game_vesion(game_and_version)


class WEBSOCKET_SERVER:
    cookies: List[uuid.UUID]
    server_socket: socket.socket
    web: WEB

    def __init__(self, web, port, loop: asyncio.AbstractEventLoop) -> None:
        self.SERVER_HOST = "0.0.0.0"
        self.SERVER_PORT = port
        self.BUFFER_SIZE = 1024
        self.sever_socket = None
        self.web = web
        self.loop = loop

    async def serverThreadFunc(self):
        cnt = 0
        while True:
            try:
                async with serve(
                    lambda websocket: tcpClientHandler(websocket, self.web),
                    self.SERVER_HOST,
                    self.SERVER_PORT,
                    reuse_address=True,
                ):
                    print(f"""serving on {self.SERVER_HOST}:{self.SERVER_PORT}""")
                    await asyncio.Future()
                break
            except:
                time.sleep(20)
                logger.info("端口拿不到")
                cnt += 1
                if cnt == 10:
                    logger.error("端口怎么死活拿不到呢呢呢")
                    return


async def tcpClientHandler(websocket, web):
    tcpClient = WEBSOCKET_CLIENT(websocket, web, timeOutSetting=300)
    await asyncio.create_task(tcpClient.playerMannage())
