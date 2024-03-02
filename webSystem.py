import uuid
import math
from dataclasses import dataclass
from defineRegicideMessage import MESSAGE,DATATYPE,GAME_SETTINGS,playerWebSystemID,PLAYER_LEVEL
from defineError import AuthError,PlayerNumError,ServerBusyError,RoomError,RegisterFailedError
from myLockQueue import myLockQueue as LockQueue
from collections import deque
from typing import List,Union,Tuple
from myLogger import logger
from enum import Enum
from DarkPaperMySQL import sqlSystem as sqlSystem



@dataclass
class WEB_PLAYER:
    #player is equal to a username,
    #if someone want to use the same player to play in the same room, 
    #we should get the old player and change its cookie, keep its index
    #if someone want to player in other room
    #we should let the old room know, 
    #so we need to change the room and send exception when the game is getting message, timeout or roomWrong  
    
    playerIndex:playerWebSystemID
    playerQueue:LockQueue
    playerName:str
    playerRoom:int
    playerLevel:PLAYER_LEVEL
    playerCookie:uuid.UUID          
    #different room, different player cookie
    #可能持有一个糟糕的room,room方短线了,会给予用户很强的反馈
    

@dataclass
class WEB_ROOM:
    roomID:int
    #可能持有一个拒绝一切消息的playerIndex,出于断线和change room,只需放平心态,静候即可
    playerIndexs:List[int]
    roomQueue:LockQueue
    maxPlayer:int

class WEB:
    """
    promise:
        player connect to room <=> room connect to player
    send and get Func:
        in send func, we may deal with it according to the hook
    """
    players:List[Union[WEB_PLAYER,None]]
    rooms:List[Union[WEB_ROOM,None]]
    def __init__(self,maxPlayer:int, maxRoom) -> None:
        self.maxPlayer = maxPlayer
        self.maxRoom = maxRoom
        self.hallQueue = LockQueue()
        self.players = [None]*maxPlayer #maxplayer 很大
        self.rooms = [None]*maxRoom
        self.sqlSystem = sqlSystem()
        """
        binding     playerQueue-playerIndex-cookie-playerName
        cookie      playerName+password = cookie 
        """
    async def hallGetMessage(self) -> MESSAGE:
        message:MESSAGE = await self.hallQueue.get()
        return message
    async def roomGetMessage(self, roomIndex:int) -> MESSAGE:
        #此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        room =self.rooms[roomIndex] 
        if room != None:
                message = await room.roomQueue.get()
        return message
    def roomSendMessage(self, message:MESSAGE):
        #TODO:check it
        #TODO:room 的终结
        if message.player == -1:
            self.hallQueue.put_nowait(message)
        elif message.player == -2:
            print(message.roomData)
        else:
            player = self.players[message.player]
            if player != None:
                playerRoom = self.rooms[player.playerRoom]
                if playerRoom!=None and playerRoom.roomID == message.room:
                    player.playerQueue.put_nowait(message)
        return
    async def playerGetMessage(self, playerIndex:playerWebSystemID, cookie:uuid.UUID)->MESSAGE:
        player = self.players[playerIndex]
        if player == None:
            #WARNING:这里的message不是从queue里取出来的哦
            return MESSAGE(-1,playerIndex,DATATYPE.cookieWrong,None,None)
            #TODO
        else:
            if player.playerCookie == cookie:
                return await player.playerQueue.get()
            else:
                return MESSAGE(-1,playerIndex,DATATYPE.cookieWrong,None,None)
    def playerSendMessage(self, message:MESSAGE, cookie:uuid.UUID):
        player = self.players[message.player]
        if player != None and player.playerCookie == cookie:
            room = self.rooms[player.playerRoom]
            if room != None:
                room.roomQueue.put_nowait(message)
            else:
                self.hallQueue.put_nowait(message)
        #TODO:else

    #arg:legal or illegal playerName and password
    #ret:raise RegisterError, AuthError
    #ret:room creating may cause error
    def playerJoinRoom(self, playerName:str, password:str, roomIndex:int) -> Tuple[uuid.UUID, playerWebSystemID]:
        """
        password are needed
        WARNING: if player use TCP, thier password is VERY easy to leak, keep it in mind
        WARNING: PLZ, check should be threading SAFE
        """
        systemID,level = self._checkPassword(playerName, password)
        if level == PLAYER_LEVEL.superUser:
            #TODO
            raise AuthError("Super User?")
        elif level == PLAYER_LEVEL.normal:
            try:
                playerIndex = systemID
                player = self._newPlayer(playerIndex, playerName, roomIndex)
                re = (player.playerCookie, playerIndex)
                
                userChangeRoomFlag = True
                if roomIndex >= 0 and roomIndex <=self.maxRoom:     
                    room = self.rooms[roomIndex]    #index error
                else:
                    raise IndexError("错误的房间喵喵")
                newRoomFlag = (room == None)
                if newRoomFlag:
                    room = self._newRoom(roomIndex, playerIndex)    
                else:
                    room,userChangeRoomFlag = self._changeRoom(roomIndex, playerIndex)    #room error

                self.players[playerIndex] = player
                self.rooms[roomIndex] = room
                player.playerQueue.put_nowait(MESSAGE(-1, playerIndex, DATATYPE.logInSuccess, None, None))
                if newRoomFlag:
                    self.hallQueue.put_nowait(MESSAGE(-1, playerWebSystemID(-1), DATATYPE.createRoom, roomIndex, None))
                if userChangeRoomFlag:
                    room.roomQueue.put_nowait(MESSAGE(room.roomID, playerIndex, DATATYPE.confirmPrepare, playerName, None))
                return re
            except Exception as e:
                logger.error(str(e))
                raise RegisterFailedError("注册失败了\n")
                
        else:
            raise AuthError(f"Username or Password is wrong. 忘掉了请联系管理员桑呢\nUsername:{playerName}\n Password:{password}\n")
    def playerLogIn(self, playerName:str, password:str) -> Tuple[uuid.UUID, playerWebSystemID]:# type:ignore
        pass    
    #raise Error
    def playerRegister(self,playerName:str, password:str):
        self.sqlSystem.userRegister(playerName,password)
    def roomDestruct(self,roomIndex:int) -> None:
        room = self.rooms[roomIndex]
        if room == None:
            logger.error(f"淦这个房怎么没关就没了")
            return
        for playerIndex in room.playerIndexs:
            self.players[playerIndex] = None

    def playerLogOut(self,playerIndex:playerWebSystemID, cookie:uuid.UUID):
        pass
    def _newPlayer(self, playerIndex:playerWebSystemID, playerName:str, playerRoom:int) -> WEB_PLAYER:
        player = self.players[playerIndex]
        if player != None:
            player.playerQueue.put_nowait(MESSAGE(-1, playerIndex, DATATYPE.logOtherPlace, roomData=None, webData=None))
        cookie = uuid.uuid4()
        player = WEB_PLAYER(playerCookie=cookie, playerIndex=playerIndex, playerQueue=LockQueue(), playerName=playerName, playerRoom= playerRoom, playerLevel= PLAYER_LEVEL.normal)
        return player
        

    def _newRoom(self, roomIndex, firstPlayerIndex)->WEB_ROOM:
        room = WEB_ROOM(roomID=roomIndex,
                        playerIndexs=[firstPlayerIndex],
                        roomQueue=LockQueue(),
                        maxPlayer=self._roomIndexToMaxPlayer(roomIndex))
        return room
    def _changeRoom(self, roomIndex, playerIndex)->Tuple[WEB_ROOM, bool]:
        room = self.rooms[roomIndex]
        newIndexs =  list(set(room.playerIndexs + [playerIndex]))
        userChangeRoomFlag = True
        for ind in room.playerIndexs:
            if ind == playerIndex:
                userChangeRoomFlag = False
                break
        if len(newIndexs) > room.maxPlayer:
            raise RoomError("满了\n")
        else:
            newRoom = WEB_ROOM(roomIndex, newIndexs, room.roomQueue, room.maxPlayer)
        return (newRoom,userChangeRoomFlag)    
    #Only checked in register
    def _checkPassword(self, playerName:str, password:str) -> Tuple[playerWebSystemID, PLAYER_LEVEL]:
        try:
            re = self.sqlSystem.checkPassword(playerName, password)
            return re
        except:
            return (playerWebSystemID(-1),PLAYER_LEVEL.illegal)
    def _checkOldCookie(self,playerIndex:playerWebSystemID , oldCookie:uuid.UUID)->PLAYER_LEVEL:
        p = self.players[playerIndex]
        if p == None:
            return PLAYER_LEVEL.illegal
        else:
            level = p.playerLevel if p.playerCookie==oldCookie else PLAYER_LEVEL.illegal
            return level
    def _roomIndexToMaxPlayer(self,roomIndex:int)->int:
        if (roomIndex >= 0 and roomIndex < self.maxRoom):
            re = math.floor(roomIndex/100) + 2 
            re = re if (re in [2,3,4]) else 2
            return re
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

