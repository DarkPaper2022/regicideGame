import socket
import threading
import uuid
import random
import time
from myLogger import logger
from typing import List,Any,Tuple
from webSystem import WEB
from defineMessage import MESSAGE,DATATYPE,TALKING_MESSAGE,STATUS
from dataclasses import dataclass
from defineError import AuthError,MessageFormatError
from defineTCP_UI import cardsToStr,cardToStr,bossToStr
from defineRound import ROUND




#recv and send NO LOCK
class TCP_CLIENT:
    clientSocket:socket.socket
    clientAddr:Any
    playerIndex:int
    playerCookie:uuid.UUID
    userName:str    #be careful, once initialized it should never be changed 
    web:WEB
    def __init__(self, clientSocket, clientAddr, web) -> None:
        self.clientAddr = clientAddr
        self.clientSocket = clientSocket
        self.web = web
    def start(self):
        authThread = threading.Thread(target=self.authThread)
        authThread.start()
        return
    #and it will start the other two thread, the children will release the socket on their own
    def authThread(self):
        print(f"Accepted connection from {self.clientAddr}")
        username = ""
        while True:
            self.clientSocket.send(b"Username and Password, plz")
            data = self.clientSocket.recv(1024)
            if not data:
                self.clientSocket.close()
                print(f"Connection with {self.clientAddr} closed.")
                return
            l = data.strip().split(b" ")
            try:
                self.playerCookie, self.playerIndex = self.web.register(playerName=l[0].decode("utf-8"), password=l[1].decode("utf-8"))
                username = l[0].decode("utf-8")
                break
            except AuthError as e:
                self.clientSocket.send(str(e).encode())
            except Exception as e:
                self.clientSocket.send("Wrong Format Username and Password: 你在乱输什么啊\n".encode())
        self.userName = username
        recvThread = threading.Thread(target=self.recvThreadFunc)
        sendThread = threading.Thread(target=self.sendThreadFunc)
        recvThread.start()
        sendThread.start()
        return
    #recv From  netcat
    def recvThreadFunc(self):
        #认为到这里我们拿到了一个正常的cookie和playerIndex
        while True:
            try:
                data = self.clientSocket.recv(1024)
                if not data:
                    break
                message = self.dataToMessage(data)
                self.web.playerSendMessage(message,self.playerCookie)
            except MessageFormatError as e:
                pass
            except Exception as e:
                print(f"Error: {e}")
                break
        try:
            self.clientSocket.close()
            print(f"Connection with {self.clientAddr} closed.")
        except:
            pass
    #send To netcat
    def sendThreadFunc(self):
        while True:
            message = self.web.playerGetMessage(self.playerIndex, self.playerCookie)
            data = self.messageToData(message)
            try:
                self.clientSocket.send(data)
            except Exception as e:
                print(f"Error: {e}")
                break
        try:
            self.clientSocket.close()
            print(f"Connection with {self.clientAddr} closed.")
        except:
            pass
    # error MessageFormatError if bytes are illegal
    def dataToMessage(self, data:bytes) -> MESSAGE:
        try:
            l = [line.strip() for line in data.strip().split(b'#')]
            dataType = DATATYPE(int(l[0].decode()))
            if dataType == DATATYPE.card:
                if len(l) == 1 or l[1] == b"":
                    messageData = []
                else:
                    messageData = [int(card.decode()) for card in l[1].split(b" ")]
                logger.info("A card Message")
            elif dataType == DATATYPE.speak:
                messageData = TALKING_MESSAGE(time.time(), self.userName, l[1].decode())
            elif dataType == DATATYPE.confirmJoker:
                messageData = int(l[1].strip())
            else:
                messageData = None
        except:
            self.clientSocket.send("Wrong Format Mesasge: 你在乱输什么啊\n".encode())
            raise MessageFormatError("Fuck you!")
        message = MESSAGE(self.playerIndex, dataType, messageData)
        return message
    def messageToData(self, message:MESSAGE) -> bytes:
        if message.dataType == DATATYPE.answerStatus:
            flag, status = message.data
            if flag:
                messageData = self._statusToStr(status)
            else:
                messageData = "没开呢，别急\n"
        elif message.dataType == DATATYPE.answerTalking:
            messageData = ""
            talkings:Tuple[TALKING_MESSAGE,...] = message.data
            for line in talkings:
                timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(line.time))
                nameStr = line.userName
                talkStr = line.message
                messageData += (timeStr+" "+nameStr+"说"+"\n\t"+talkStr + "\n")
        elif message.dataType == DATATYPE.overSignal:
            isWin:bool = message.data
            if isWin:
                messageData = "真棒, 你们打败了魔王\n"
            else:
                messageData = "寄, 阁下请重新来过\n"
        elif (message.data == None):
            messageData = ""
        else:
            messageData = str(message.data)
        data:bytes = message.dataType.name.encode() +b"\n"+ messageData.encode()
        return data
    def _statusToStr(self, status:STATUS) -> str:
        cardHeapLengthStr:str = f"牌堆还剩{status.cardHeapLength}张牌\n"
        discardHeapLengthStr = f"弃牌堆有{status.discardHeapLength}张牌\n"
        defeatedBossesStr = f"您已经打败了{cardsToStr(status.defeatedBosses)},还有{12 - len(status.defeatedBosses)}个哦"
        currentPlayerStr = "该怎么搞由您说了算" if status.currentPlayerIndex == self.playerIndex else\
                            f"""该怎么搞由您的{status.currentPlayerIndex}号队友"""
        currentRoundStr =   ("现在是攻击轮" if status.currentRound == ROUND.atk else\
                            "现在是防御轮" if status.currentRound == ROUND.defend else\
                            "现在joker生效了" if status.currentRound == ROUND.jokerTime else "现在是一个奇怪的轮次, 你不应该看见我的")        
        currentPlayerAndRoundStr = currentRoundStr + "," +currentPlayerStr
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
        re:str = cardHeapLengthStr + discardHeapLengthStr + defeatedBossesStr + playersStr + currentPlayerAndRoundStr + yourCardsStr + currentBossStr 
        return re


class TCP_SERVER:
    cookies:List[uuid.UUID]
    server_socket:socket.socket
    web:WEB
    def __init__(self, web) -> None:
        self.SERVER_HOST = '127.0.0.1'
        self.SERVER_PORT = 6666
        self.BUFFER_SIZE = 1024
        self.sever_socket = None
        self.web = web
    def start(self):
        serverThread = threading.Thread(target=self.serverThreadFunc)
        serverThread.start()
    def serverThreadFunc(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server_socket.bind((self.SERVER_HOST, self.SERVER_PORT))
        except:
            self.SERVER_PORT += random.randint(1,200)
            self.server_socket.bind((self.SERVER_HOST, self.SERVER_PORT))
        self.server_socket.listen(5)
        print(f"Server listening on {self.SERVER_HOST}:{self.SERVER_PORT}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            #可能在标识自己身份的时候出错,交由子线程处理，socket也由子线程来释放
            tcpClient = TCP_CLIENT(client_socket, client_address, self.web)
            tcpClient.start()
        server_socket.close()
