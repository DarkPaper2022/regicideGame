import socket
import asyncio
import websockets
import os
import subprocess
import uuid
import threading
import math
from dataclasses import dataclass
from defineMessage import MESSAGE,DATATYPE,GAME_SETTINGS
from defineError import AuthError,PlayerNumError,ServerBusyError,RoomError
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
class WEB_PLAYER:
    cookie:uuid.UUID
    playerIndex:int
    playerQueue:LockQueue
    playerName:str
    playerRoom:int

#线程安全了现在
@dataclass
class WEB_ROOM:
    lock:threading.Lock
    roomID:int
    playerIndexs:List[int]
    roomQueue:LockQueue
    maxPlayer:int
class WEB:
    players:List[Union[WEB_PLAYER,None]]
    rooms:List[Union[WEB_ROOM,None]]
    def __init__(self,maxPlayer:int, maxRoom) -> None:
        self.registerLock = threading.Lock()
        self.maxPlayer = maxPlayer
        self.maxRoom = maxRoom
        self.hallQueue = LockQueue()
        self.players = [None]*maxPlayer #maxplayer 很大
        self.rooms = [None]*maxRoom
        self.indexPool = LockQueue()
        
        for i in range(maxPlayer):
            self.indexPool.put(i)
        self.suIndexPool = LockQueue()
        for i in [-2]:
            self.suIndexPool.put(i)
        self.roomPool = LockQueue()
        for i in range(maxRoom):
            self.roomPool.put(i)
        """
        binding     playerQueue-playerIndex-cookie-playerName
        cookie      playerName+password = cookie 
        """
    def hallGetMessage(self) -> MESSAGE:
        message = self.hallQueue.get()
        return message
    def roomGetMessage(self, roomIndex:int) -> MESSAGE:
        #此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        room =self.rooms[roomIndex] 
        if room != None:
            message = room.roomQueue.get()
        return message

    def roomSendMessage(self, message:MESSAGE):
        #TODO:check it
        try:
            if message.player == -2:
                print(message.data)
            else:
                player = self.players[message.player]
                if player != None:
                    room = self.rooms[player.playerRoom]
                    if room!=None:
                        player.playerQueue.put(message)
            return
        except:
            return
    def playerGetMessage(self, playerIndex:int, cookie:uuid.UUID)->MESSAGE:
        player = self.players[playerIndex]
        if player == None:
            #WARNING:这里的message不是从queue里取出来的哦
            return MESSAGE(-1,playerIndex,DATATYPE.cookieWrong,None)
            #TODO
        else:
            if player.cookie == cookie:
                #WARNING: 这里有时间差,注意是否有错位风险
                return player.playerQueue.get()
            else:
                return MESSAGE(-1,playerIndex,DATATYPE.cookieWrong,None)
    def playerSendMessage(self, message:MESSAGE, cookie:uuid.UUID):
        player = self.players[message.player]
        try:
            if player != None and player.cookie == cookie:
                room = self.rooms[player.playerRoom]
                if room != None:
                    room.roomQueue.put(message)
        except:
            pass
        #TODO:else
    #arg:legal or illegal playerName and password
    #ret:raise AuthError if illegal, RoomError, TimeOutError, ServerBusyError
    #ret:room creating may cause error
    def register(self, playerName:str, password:str, roomIndex:int):
        logger.info(f"i wait for lock now{playerName,password,roomIndex}")
        self.registerLock.acquire(timeout=20)
        logger.info(f"i get lock now{playerName,password,roomIndex}")
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
            for player in self.players:
                if player != None and player.playerName == playerName:
                    index = player.playerIndex
                    newID = uuid.uuid4()
                    player.cookie = newID
                    self.registerLock.release()
                    return (newID, index)
            id = uuid.uuid4()
            playerIndex = self.indexPool.get()
            try:
                room = self.rooms[roomIndex]
            except:
                logger.info(f"i get error now{playerName,password,roomIndex}")
                raise RoomError(f"你在试图进入一个不存在的房间{roomIndex}?\n")
            if room == None:    #WARNING: not threading safe here, but outside is safe, and easy to fix
                room = WEB_ROOM(lock=threading.Lock(),
                                roomID=roomIndex, 
                                playerIndexs = [playerIndex], 
                                roomQueue=LockQueue(), 
                                maxPlayer= self._roomIndexToMaxPlayer(roomIndex=roomIndex))
                self.rooms[roomIndex] = room
                self.hallQueue.put(MESSAGE(-1, -1, DATATYPE.createRoom, roomIndex))
            else:
                room.lock.acquire()
                if len(room.playerIndexs) < room.maxPlayer:
                    room.playerIndexs.append(playerIndex)
                    room.lock.release()
                else:
                    room.lock.release()
                    raise RoomError(f"{roomIndex}号房间满了\n")
            player = WEB_PLAYER(id, playerIndex, LockQueue(), playerName, playerRoom = roomIndex)
            self.players[playerIndex] = player
            player.playerQueue.put(MESSAGE(-1, playerIndex, DATATYPE.logInSuccess, None))
            room.roomQueue.put(MESSAGE(room.roomID, playerIndex, DATATYPE.confirmPrepare, playerName))
            self.registerLock.release()
            return (id, playerIndex)
        else:
            self.registerLock.release()
            raise AuthError(f"Username or Password is wrong. 忘掉了请联系管理员桑呢\nUsername:{playerName}\n Password:{password}\n")
    #Only checked in register, lock in register
    def _check(self, playerName:str, password:str) -> PLAYER_LEVEL:
        #TODO
        return PLAYER_LEVEL.normal


    def _roomIndexToMaxPlayer(self,roomIndex:int)->int:
        if (roomIndex >= 0 and roomIndex < self.maxRoom):
            return math.floor(roomIndex/100) + 2
        else:
            logger.error(f"这里炸了,{roomIndex}被送进来了")
            return 2

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

