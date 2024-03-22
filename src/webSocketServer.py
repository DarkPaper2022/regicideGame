import socket
import uuid
from websockets.server import serve, WebSocketServerProtocol
import asyncio
import time
import json
from myLogger import logger
from typing import List, Any, Tuple, Union
from webSystem import WEB
from defineRegicideMessage import (
    TALKING_MESSAGE,
    FROZEN_STATUS_PARTLY,
    REGICIDE_DATATYPE,
)
from defineWebSystemMessage import (
    MESSAGE,
    playerWebSystemID,
    WEB_SYSTEM_DATATYPE,
    DATATYPE,
    DATA_UPDATE_PLAYER_STATUS,
    FROZEN_ROOM_STATUS_inWebSystem,
    DATA_ANSWER_LOGIN,
    DINAL_TYPE,
    DATA_ANSWER_CONNECTION,
    DATA_ANSWER_REGISTER,
    FROZEN_GAME_TYPE,
)
from dataclasses import dataclass
from defineError import (
    AuthDenial,
    MessageFormatError,
    UserNameNotFoundDenial,
    PasswordWrongDenial,
    RegisterFailedError,
)
from define_JSON_UI_1 import strToCard, ComplexFrontEncoder
from define_JSON_UI_1 import *
from defineRound import ROUND



class WEBSOCKET_CLIENT:
    websocket: WebSocketServerProtocol
    playerIndex: playerWebSystemID
    playerCookie: uuid.UUID
    userName: str  # be careful, once initialized it should never be changed
    web: WEB
    roomID: int

    def __init__(self, websocket, web, timeOutSetting: int) -> None:
        self.websocket = websocket
        self.web = web
        self.overFlag = False
        self.timeOutSetting = timeOutSetting
        self.roomID = -1

    async def authThread(self):

        try:
            await self.websocket.send(
                json.dumps(
                    MESSAGE(
                        roomData=None,
                        playerID=playerWebSystemID(-1),
                        roomID=-1,
                        dataType=WEB_SYSTEM_DATATYPE.ANSWER_CONNECTION,
                        webData=DATA_ANSWER_CONNECTION(tuple(self.web.games)),
                    ),
                    cls=ComplexFrontEncoder,
                )
            )
            checked: bool = await self.socket_init()
        except:
            await self.websocket.close()
            return
        if not checked:
            await self.websocket.close()
            return
        while True:
            socket_data = str(await self.websocket.recv())
            if not socket_data:
                await self.websocket.close()
                return
            data_type, data = json.loads(socket_data, object_hook=json_1_obj_hook)
            data_type: DATATYPE
            if data_type == WEB_SYSTEM_DATATYPE.ASK_REGISTER:
                reg_data: DATA_ASK_REGISTER = data
                try:
                    self.web.PLAYER_REGISTER(
                        playerName=reg_data.username,
                        password=reg_data.password,
                    )
                except:
                    await self.websocket.send(
                        json.dumps(
                            MESSAGE(
                                roomData=None,
                                playerID=playerWebSystemID(-1),
                                roomID=-1,
                                dataType=WEB_SYSTEM_DATATYPE.ANSWER_REGISTER,
                                webData=DATA_ANSWER_REGISTER(
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
                    self.playerCookie, self.playerIndex = self.web.PLAYER_LOG_IN(
                        playerName=login_data.username,
                        password=login_data.password,
                    )
                    username = login_data.username
                    break
                except (RegisterFailedError, TimeoutError) as e:
                    logger.error(str(e))
                except AuthDenial as e:
                    await self.websocket.send(
                        json.dumps(
                            MESSAGE(
                                roomID=-1,
                                roomData=None,
                                playerID=playerWebSystemID(-1),
                                dataType=WEB_SYSTEM_DATATYPE.ANSWER_LOGIN,
                                webData=DATA_ANSWER_LOGIN(
                                    success=False,
                                    error=(
                                        DINAL_TYPE.LOGIN_PASSWORD_WRONG
                                        if isinstance(e, PasswordWrongDenial)
                                        else (
                                            DINAL_TYPE.LOGIN_PASSWORD_WRONG
                                            if isinstance(e, PasswordWrongDenial)
                                            else None
                                        )
                                    ),
                                ),
                            )
                        )
                    )
            else:
                logger.error("format")

        self.userName = username
        rec = asyncio.create_task(self.recvThreadFunc())
        sen = asyncio.create_task(self.sendThreadFunc())
        await asyncio.gather(rec, sen)
        return

    # recv From  netcat
    async def recvThreadFunc(self):
        # 认为到这里我们拿到了一个正常的cookie和playerIndex,但是没有合适的room
        timeOutCnt = 0
        while True:
            try:
                data = str(await self.websocket.recv())
                if not data:
                    break
                message = self.dataToMessage(data)
                self.web.playerSendMessage(message, self.playerCookie)
                if message.dataType == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    break
            except socket.timeout:
                if self.overFlag == False:
                    timeOutCnt += 1
                    if timeOutCnt == 3:
                        self.overFlag = True
                else:
                    break
            except MessageFormatError as e:
                logger.error(str(e))
            except Exception as e:
                logger.info("recvFromnetcatThread, exception Over")
                break
        try:
            self.overFlag = True
            await self.websocket.close()
        finally:
            return

    # send To netcat
    async def sendThreadFunc(self):
        while True:
            message = await self.web.playerGetMessage(
                self.playerIndex, self.playerCookie
            )
            data = self.messageToData(message)
            try:
                await self.websocket.send(data)
            except socket.timeout:
                if self.overFlag == False:
                    logger.info("sendTonetcatThread, timeout Continue")
                    pass
                else:
                    logger.info("sendTonetcatThread, timeout Over")
                    break
            except Exception as e:
                logger.info("sendTonetcatThread, exception Over")
                break
            if (
                message.dataType == WEB_SYSTEM_DATATYPE.cookieWrong
                or message.dataType == WEB_SYSTEM_DATATYPE.leaveRoom
            ):
                logger.info("sendTonetcatThread, cookie Over")
                break
        try:
            self.overFlag = True
            await self.websocket.close()
        finally:
            return

    # error MessageFormatError if bytes are illegal
    def dataToMessage(self, socket_data: str) -> MESSAGE:
        try:
            data_type, data = json.loads(socket_data, object_hook=json_1_obj_hook)
            data_type: DATATYPE
            room_ID = -1 if type(data_type) == WEB_SYSTEM_DATATYPE else self.roomID
            messageData = None
            web_data = None
            if data_type == REGICIDE_DATATYPE.card:
                card_data: Tuple[int, ...] = data
                messageData = card_data
            elif data_type == REGICIDE_DATATYPE.speak:
                speak_data: str = data
                messageData = TALKING_MESSAGE(time.time(), self.userName, speak_data)
            elif data_type == REGICIDE_DATATYPE.confirmJoker:
                joker_data: int = data
                messageData = joker_data
            elif data_type == WEB_SYSTEM_DATATYPE.JOIN_ROOM:
                join_data: int = data
                messageData = join_data
            elif data_type == WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM:
                create_data: int = data
                web_data = create_data
            else:
                pass
        except:
            raise MessageFormatError("Fuck you!")
        message = MESSAGE(room_ID, self.playerIndex, data_type, messageData, web_data)
        return message

    # Warning: not math function, self.room changed here
    def messageToData(self, message: MESSAGE) -> str:
        if message.dataType == WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS:
            room_status: DATA_UPDATE_PLAYER_STATUS = message.webData
            self.roomID = (
                -1 if room_status.playerRoom == None else room_status.playerRoom.roomID
            )
        if message.roomID != self.roomID and message.roomID != -1:
            logger.error(f"奇怪的信号?\n")
        data = json.dumps(message, cls=ComplexFrontEncoder)
        return data

    async def socket_init(self) -> bool:
        data = str(await self.websocket.recv())
        if not data:
            return False
        dataType, game_and_version = json.loads(data)
        if dataType != WEB_SYSTEM_DATATYPE.ASK_CONNECTION:
            return False
        else:
            game_and_version: FROZEN_GAME_TYPE
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
        self.taskSet = []

    async def serverThreadFunc(self):
        cnt = 0
        while True:
            try:
                async with serve(
                    lambda websocket: tcpClientHandler(websocket, self.web),
                    self.SERVER_HOST,
                    self.SERVER_PORT,
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
    await asyncio.create_task(tcpClient.authThread())
