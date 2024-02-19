import socket
import asyncio
import websockets
import os
import subprocess
import uuid
from dataclasses import dataclass
from messageDefine import MESSAGE,DATATYPE
from queue import Queue as LockQueue
from collections import deque
from typing import List,Union
from errorDefine import AuthError
from myLogger import logger


@dataclass
class PLAYER:
    cookie:uuid.UUID
    playerIndex:int
    playerQueue:LockQueue
    playerName:str


class WEB:
    players:List[Union[PLAYER,None]]
    def __init__(self,maxPlayer:int) -> None:
        self.maxPlayer = maxPlayer
        self.gameQueue = LockQueue()
        self.players = [None]*maxPlayer
        self.indexPool = LockQueue()
        for i in range(maxPlayer):
            self.indexPool.put(i)
    """
    binding     playerQueue-playerIndex-cookie-playerName
    cookie      playerName+password = cookie 
    """
    def gameGetMessage(self) -> MESSAGE:
        #此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        logger.info("wanting a meesgae")
        message = self.gameQueue.get()
        logger.info("get a message")
        return message
    def gameSendMessage(self, message:MESSAGE):
        player = self.players[message.player]
        if player == None:
            pass
            #TODO
        else:
            player.playerQueue.put(message)
        return
    def playerGetMessage(self, playerIndex:int, cookie:uuid.UUID)->MESSAGE:
        #cookie check
        player = self.players[playerIndex]
        if player == None:
            return MESSAGE(-1,DATATYPE(-1),None)
            #TODO
        else:
            return player.playerQueue.get()
    def playerSendMessage(self, message:MESSAGE, cookie:uuid.UUID):
        #cookie check
        self.gameQueue.put(message)
    
    def register(self, playerName:str, password:str):
        """
        password are needed
        WARNING: if player use TCP, thier password is VERY easy to leak, keep it in mind
        """
        checkBool:bool = self.check()
        if checkBool:
            id = uuid.uuid4()
            playerIndex = self.indexPool.get()
            player = PLAYER(id, playerIndex, LockQueue(), playerName)
            self.players[playerIndex] = player
            player.playerQueue.put(MESSAGE(playerIndex, DATATYPE.logInSuccess, None))
            if (self.indexPool.empty()):
                self.gameQueue.put(MESSAGE(-1, DATATYPE.startSignal, None))
            return (id, playerIndex)
        else:
            raise AuthError(f"Username or Password is wrong. 忘掉了请联系管理员桑呢\nUsername:{playerName}\n Password:{password}\n")
    def check(self) -> bool:
        #TODO
        return True

"""class PLAYER_TERMINAL:
    web:WEB
    def __init__(self,web) -> None:
        self.queue = LockQueue()
        self.web = web
        self.num = None
    def read(self) -> None: #you should reg first!!!
        while True:
            inputStr = input().strip()
            if inputStr != None:
                if inputStr[:2] == "ask"[:2]:
                    message = MESSAGE(self.num, DATATYPE.askStatus, None)
                else:
                    cards = [int(card) for card in inputStr.split(" ")]
                    message = MESSAGE(self.num, DATATYPE.card, cards)
                self.web.gameQueue.put(message)
    def send(self,message:str):
        print(message)
        return
    def register(self):
        self.web.register(self)"""

