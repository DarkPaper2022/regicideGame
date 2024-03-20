import socket
import uuid
import random
import json
from define_JSON_UI import MyEncoder
import asyncio
import time
from dataclasses import asdict
from myLogger import logger
from typing import List,Any,Tuple,Union
from webSystem import WEB
from defineRegicideMessage import TALKING_MESSAGE,\
    FROZEN_STATUS_PARTLY,REGICIDE_DATATYPE
from defineWebSystemMessage import MESSAGE, playerWebSystemID,\
WEB_SYSTEM_DATATYPE, DATATYPE, FROZEN_PLAYER_WEB_SYSTEM, FROZEN_ROOM
from dataclasses import dataclass
from defineError import AuthError,MessageFormatError,RoomError,ServerBusyError,RegisterFailedError
from defineTCP_UI import cardsToStr,cardToStr,bossToStr,strToCard
from defineRound import ROUND

UI_HEIGHT = 30
translate_dict:dict[str,DATATYPE] = {
    "join":WEB_SYSTEM_DATATYPE.JOIN_ROOM,
    "create":WEB_SYSTEM_DATATYPE.createRoom,
    "prepare":WEB_SYSTEM_DATATYPE.confirmPrepare,
    "quit":WEB_SYSTEM_DATATYPE.leaveRoom,
    "log out":WEB_SYSTEM_DATATYPE.LOG_OUT,
    "room status":WEB_SYSTEM_DATATYPE.askRoomStatus,
    
    "status":REGICIDE_DATATYPE.askStatus,
    "talk log":REGICIDE_DATATYPE.askTalking,
    "card":REGICIDE_DATATYPE.card,
    "speak":REGICIDE_DATATYPE.speak,
    "joker":REGICIDE_DATATYPE.confirmJoker 
}

#recv and send NO LOCK
#只对socket和web的交互有线程问题、而这两个都是线程安全的
class TCP_CLIENT:
    reader:asyncio.StreamReader
    writer:asyncio.StreamWriter
    playerIndex:playerWebSystemID
    playerCookie:uuid.UUID
    userName:str    #be careful, once initialized it should never be changed 
    web:WEB
    roomID:int
    def __init__(self, reader, writer, web, timeOutSetting:int) -> None:
        self.reader = reader
        self.writer = writer
        self.web = web
        self.overFlag = False
        self.timeOutSetting = timeOutSetting
        self.roomID = -1

    async def authThread(self):
        username = ""
        while True:
            self.writer.write(0*b"\n" + b"Username and Password, plz\n")
            data = await self.reader.read(1024)
            if not data:
                self.writer.close()
                return
            l0 = data.split(b"#")
            if l0[0].strip() == b"register":
                try:
                    l = l0[1].strip().split(b" ")
                    self.web.PLAYER_REGISTER(
                        playerName=l[0].decode("utf-8"),
                        password=l[1].decode("utf-8"))
                except:
                    self.writer.write((UI_HEIGHT*"\n"+"注册失败了喵喵,请看看我们的readme"+"\n").encode())
            elif l0[0].strip() == b"log in":
                try:
                    l = l0[1].strip().split(b" ")
                    self.playerCookie, self.playerIndex = self.web.PLAYER_LOG_IN(
                        playerName=l[0].decode("utf-8"),
                        password=l[1].decode("utf-8"))
                    username = l[0].decode("utf-8")
                    break
                except (AuthError,RegisterFailedError,TimeoutError) as e:
                    self.writer.write((UI_HEIGHT*"\n"+str(e)+"\n").encode())
                except Exception as e:
                    self.writer.write((UI_HEIGHT*"\n"+"Wrong Format Username and Password: 你在乱输什么啊\n").encode() + str(e).encode())
            else:
                self.writer.write((UI_HEIGHT*"\n"+""" "register" or "log in", no other choice """+"\n").encode())
        self.userName = username
        rec = asyncio.create_task(self.recvThreadFunc())
        sen = asyncio.create_task(self.sendThreadFunc())
        await asyncio.gather(rec, sen)
        return
    #recv From  netcat
    async def recvThreadFunc(self):
        #认为到这里我们拿到了一个正常的cookie和playerIndex,但是没有合适的room
        timeOutCnt = 0
        while True:
            try:
                data = await self.reader.read(1024)
                if not data:
                    break
                message = self.dataToMessage(data)
                logger.debug(message)
                self.web.playerSendMessage(message,self.playerCookie)
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
                self.writer.write((UI_HEIGHT*"\n"+"Wrong Format Mesasge: 你在乱输什么啊\n").encode())
            except Exception as e:
                logger.info("recvFromnetcatThread, exception Over")
                break
        try:
            self.overFlag = True
            self.writer.close()
        finally:
            return
    #send To netcat
    async def sendThreadFunc(self):
        logger.debug("I CAN SEND")
        while True:
            message = await self.web.playerGetMessage(self.playerIndex, self.playerCookie)
            data =UI_HEIGHT*b"\n" + self.messageToData(message)
            try:
                self.writer.write(data)
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
            if message.dataType == WEB_SYSTEM_DATATYPE.cookieWrong or message.dataType == WEB_SYSTEM_DATATYPE.leaveRoom:
                logger.info("sendTonetcatThread, cookie Over")
                break
        try:
            self.overFlag = True
            self.writer.close()
        finally:
            return
    # error MessageFormatError if bytes are illegal
    def dataToMessage(self, data:bytes) -> MESSAGE:
        try:
            l = [line.strip() for line in data.strip().split(b'#')]
            data_type_str = l[0].decode()
            data_type = translate_dict[data_type_str]
            messageData = None
            web_data = None
            if data_type == REGICIDE_DATATYPE.card:
                if len(l) == 1 or l[1] == b"":
                    messageData = []
                else:
                    messageData = [strToCard(card.strip()) for card in l[1].split()]
                logger.info("A card Message")
            elif data_type == REGICIDE_DATATYPE.speak:
                messageData = TALKING_MESSAGE(time.time(), self.userName, l[1].decode())
            elif data_type == REGICIDE_DATATYPE.confirmJoker:
                messageData = int(l[1].strip())
            elif data_type == WEB_SYSTEM_DATATYPE.JOIN_ROOM:
                messageData = int(l[1].strip())
            elif data_type == WEB_SYSTEM_DATATYPE.createRoom:
                web_data = int(l[1].strip())
            else:
                pass
        except:
            raise MessageFormatError("Fuck you!")
        message = MESSAGE(self.roomID,self.playerIndex, data_type, messageData, web_data)
        return message
    #Warning: not math function, self.room changed here 
    def messageToData(self, message:MESSAGE) -> bytes:
        try:
            json_string = json.dumps(asdict(message), cls=MyEncoder)
            logger.info("json is:\n" +json_string)
        except Exception as e:
            print("SHIT", e)
        if message.room != self.roomID and message.room != -1:
            return f"奇怪的信号?\n".encode()
        if message.dataType == REGICIDE_DATATYPE.answerStatus:
            status = message.roomData
            messageData = self._statusToStr(status)
        elif message.dataType == REGICIDE_DATATYPE.answerTalking:
            messageData = ""
            talkings:Tuple[TALKING_MESSAGE,...] = message.roomData
            if len(talkings) == 0:
                messageData += "还没人说话呢,等joker了再说吧"
            for line in talkings:
                timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(line.time))
                nameStr = line.userName
                talkStr = line.message
                messageData = (timeStr+" "+nameStr+"说"+"\n\t"+talkStr + "\n") + messageData
        elif message.dataType == REGICIDE_DATATYPE.overSignal:
            isWin:bool = message.roomData
            if isWin:
                messageData = "真棒, 你们打败了魔王\n"
            else:
                messageData = "寄, 阁下请重新来过\n"
        elif message.dataType == WEB_SYSTEM_DATATYPE.cookieWrong or message.dataType == WEB_SYSTEM_DATATYPE.leaveRoom:
            messageData = "你被顶号了,要不要顶回来试试?\n"
        elif message.dataType == REGICIDE_DATATYPE.answerRoom:
            self.roomID = message.roomData
            messageData = f"""你的房间号是{message.roomData}\n"""
        elif message.dataType == WEB_SYSTEM_DATATYPE.logInSuccess:
            messageData = ""
        elif message.dataType == WEB_SYSTEM_DATATYPE.ANSWER_ROOM_STATUS:
            status = message.webData
            messageData = self._room_status_to_str(status)            
        elif (message.roomData == None):
            messageData = ""
        else:
            messageData = str(message.roomData)
        data:bytes = message.dataType.name.encode() +b"\n"+ messageData.encode()
        return data

    def _statusToStr(self, status:FROZEN_STATUS_PARTLY) -> str:
        cardHeapLengthStr:str = f"牌堆还剩{status.cardHeapLength}张牌\n"
        discardHeapLengthStr = f"弃牌堆有{status.discardHeapLength}张牌\n"
        defeatedBossesStr = f"您已经打败了{(cardsToStr(status.defeatedBosses))},还有{12 - len(status.defeatedBosses)}个哦\n" \
                            if len(status.defeatedBosses) != 0 else "还有12个boss要打哦\n"
        currentPlayerStr = "该怎么搞由您说了算\n" if status.currentPlayerLocation == status.yourLocation else\
                            f"""该怎么搞由您的{status.currentPlayerLocation}号位队友说了算\n"""
        currentRoundStr =   ("现在是攻击轮" if status.currentRound == ROUND.atk else\
                            "现在是防御轮" if status.currentRound == ROUND.defend else\
                            "现在joker生效了" if status.currentRound == ROUND.jokerTime else\
                            "现在是一个奇怪的轮次, 你不应该看见我的")        
        currentPlayerAndRoundStr = currentRoundStr + "," +currentPlayerStr
        disCardHeapStr = f"""弃牌堆里有这些牌:{cardsToStr(status.disCardHeap)}\n"""
        atkCardHeapStr = f"""攻击堆里有这些牌:{cardsToStr(status.atkCardHeap)}\n"""
        playersStr:str = "您的队友:"
        for player in status.players:
            preDelta = player.playerLocation - status.yourLocation
            delta =  preDelta if preDelta >= 1 else preDelta + status.totalPlayer 
            #TODO:防御性编程
            playersStr += f"""
    用户名:{player.playerName}
    手牌数目:{player.playerHandCardCnt}/{9 - status.totalPlayer}
    用户位置:{player.playerLocation}号位，你的{delta*"下"}家

"""
        yourCardsStr = f"""{"YourCards"}:
        {cardsToStr(status.yourCards)}
    """
        currentBossStr = bossToStr(status.currentBoss)
        re:str = cardHeapLengthStr + discardHeapLengthStr + disCardHeapStr + atkCardHeapStr + defeatedBossesStr + playersStr + currentPlayerAndRoundStr + yourCardsStr + currentBossStr 
        return re
    def _room_status_to_str(self, status:FROZEN_PLAYER_WEB_SYSTEM)->str:
        room = status.playerRoom
        if room == None:
            re_room = "您不在房里\n"
        else:
            re_room = ""
            re_room += f"""房间的最大人数为:{room.maxPlayer}\n"""
            re_room += f"""房间号为:{room.roomID}\n"""
            re_room += ",".join([f"""{name}({"已" if ready else "未"}准备)\n""" for name, ready in room.playerIndexs])
            re_room += f"""房间状态为:{room.status.name}\n"""
        re = ""
        re += f"""用户等级为:{status.playerLevel.name}\n"""
        re += f"""用户名为:{status.playerName}\n"""
        re += re_room
        return re
class TCP_SERVER:
    cookies:List[uuid.UUID]
    server_socket:socket.socket
    web:WEB
    def __init__(self, web, port, loop:asyncio.AbstractEventLoop) -> None:
        self.SERVER_HOST = '0.0.0.0'
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
                server = await asyncio.start_server(lambda r, w: tcpClientHandler(r, w, self.web), self.SERVER_HOST, self.SERVER_PORT)
                async with server:
                    print(f"""serving on {self.SERVER_HOST}:{self.SERVER_PORT}""")
                    await server.serve_forever()
                break
            except:
                time.sleep(20)
                logger.info("端口拿不到")
                cnt += 1
                if cnt == 10:
                    logger.error("端口怎么死活拿不到呢呢呢")
                    return



        



async def tcpClientHandler(reader, writer, web):
    tcpClient = TCP_CLIENT(reader, writer, web, timeOutSetting=300)
    await asyncio.create_task(tcpClient.authThread())
