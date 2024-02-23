import socket
import asyncio
import websockets
import os
import subprocess
import uuid
import threading
from dataclasses import dataclass
from defineMessage import MESSAGE,DATATYPE,GAME_SETTINGS
from defineError import AuthError,PlayerNumError
from queue import Queue as LockQueue
from collections import deque
from typing import List,Union
from myLogger import logger
from enum import Enum

class PLAYER_LEVEL(Enum):
    illegal = 0
    normal = 1
    superUser = 2
def checkPlayerLevel(player:int) -> PLAYER_LEVEL:
    #TODO
    if player >= 0:
        return PLAYER_LEVEL.normal
    elif player == -2:
        return PLAYER_LEVEL.superUser
    else:
        raise ValueError("playerLevel")
@dataclass
class PLAYER:
    cookie:uuid.UUID
    playerIndex:int
    playerQueue:LockQueue
    playerName:str


class WEB:
    players:List[Union[PLAYER,None]]
    def __init__(self,maxPlayer:int) -> None:
        self.registerLock = threading.Lock()
        self.maxPlayer = maxPlayer
        self.gameQueue = LockQueue()
        self.players = [None]*maxPlayer
        self.indexPool = LockQueue()
        for i in range(maxPlayer):
            self.indexPool.put(i)
        self.suIndexPool = LockQueue()
        for i in [-1]:
            self.suIndexPool.put(i)
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
        if message.player == -2:
            print(message.data)
        else:
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
    #arg:legal or illegal playerName and password
    #ret:raise AuthError if illegal
    def register(self, playerName:str, password:str):
        self.registerLock.acquire()
        """
        password are needed
        WARNING: if player use TCP, thier password is VERY easy to leak, keep it in mind
        WARNING: PLZ, check should be threading SAFE
        """
        level:PLAYER_LEVEL = self._check(playerName, password)
        if level == PLAYER_LEVEL.superUser:
            #TODO
            self.registerLock.release()
            raise AuthError("Super User?")
        elif level == PLAYER_LEVEL.normal:
            id = uuid.uuid4()
            playerIndex = self.indexPool.get()
            for player in self.players:
                if player != None and player.playerName == playerName:
                    return (player.cookie, player.playerIndex)
            player = PLAYER(id, playerIndex, LockQueue(), playerName)
            self.players[playerIndex] = player
            player.playerQueue.put(MESSAGE(playerIndex, DATATYPE.logInSuccess, None))
            if (self.indexPool.empty()):
                #TODO:no exception the other side
                l = [player.playerName for player in self.players if player != None]
                if len(l) != self.maxPlayer:
                    raise PlayerNumError("PlayerNum Wrong, webSystem side caught")
                self.gameQueue.put(MESSAGE(-1, DATATYPE.startSignal, 
                                           GAME_SETTINGS(tuple(l))))
            self.registerLock.release()
            return (id, playerIndex)
        else:
            self.registerLock.release()
            raise AuthError(f"Username or Password is wrong. 忘掉了请联系管理员桑呢\nUsername:{playerName}\n Password:{password}\n")
    #Only checked in register, lock in register
    def _check(self, playerName:str, password:str) -> PLAYER_LEVEL:
        #TODO
        return PLAYER_LEVEL.normal

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

