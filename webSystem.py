import uuid
import math
from dataclasses import dataclass
from defineRegicideMessage import GAME_SETTINGS
from defineWebSystemMessage import MESSAGE, playerWebSystemID,\
PLAYER_LEVEL,WEB_SYSTEM_DATATYPE,ROOM_STATUS,FROZEN_PLAYER_WEB_SYSTEM,FROZEN_ROOM
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
    playerRoom:Union[int,None]
    playerLevel:PLAYER_LEVEL
    playerCookie:uuid.UUID          
    #different room, different player cookie
    #可能持有一个糟糕的room,room方短线了,会给予用户很强的反馈


@dataclass
class WEB_ROOM:
    roomID:int
    #可能持有一个拒绝一切消息的playerIndex,出于断线,只需放平心态,静候即可
    playerIndexs:List[Tuple[playerWebSystemID, bool]]
    roomQueue:LockQueue
    maxPlayer:int
    status:ROOM_STATUS
    def removePlayer(self, player:WEB_PLAYER):
        player_room_out_message = MESSAGE(
                                    roomID = self.roomID,
                                    playerID= playerWebSystemID(-1),
                                    dataType= WEB_SYSTEM_DATATYPE.leaveRoom,
                                    roomData=None,
                                    webData=player.playerIndex)
        self.roomQueue.put_nowait(player_room_out_message)  # type:ignore
        self.playerIndexs = [(p,_) for p,_ in self.playerIndexs if p != player.playerIndex]

class WEB:
    """
    promise:
        player connect to room <=> room connect to player
        room state <=> room.py state
        player state <=> player.py state
        if a room dont have any player and its state is not playing, we destroy it 
            it depends on the room.py 
        if a player has a bad socket, remove it
            it depends on the player.py
        TODO also, we may have a "gc" to destroy the room which exist too long
            in case the room is not so good
             "gc" for player: we dont do that
    send and get Func:
        in send func, we may deal with it according to the hook
    """
    players:List[Union[WEB_PLAYER,None]]
    rooms:List[Union[WEB_ROOM,None]]
    def __init__(self,maxPlayer:int, maxRoom) -> None:
        self.maxPlayer = maxPlayer
        self.maxRoom = maxRoom
        self.hallQueue = LockQueue()
        self.web_system_queue = LockQueue()
        self.players = [None]*maxPlayer #maxplayer 很大
        self.rooms = [None]*maxRoom
        self.sqlSystem = sqlSystem()
        """
        binding     playerQueue-playerIndex-cookie-playerName
        cookie      playerName+password = cookie 
        """
    

    async def websystem_message_handler(self):
        while True:
            #arg:the player is legal
            message:MESSAGE = await self.web_system_queue.get()
            logger.debug(message)
            if message.playerID == playerWebSystemID(-1):
                if message.dataType==WEB_SYSTEM_DATATYPE.destroyRoom:
                    self._room_destruct(message.roomID)
                    
                    
                    
            elif message.roomID == -1:
                if message.dataType == WEB_SYSTEM_DATATYPE.confirmPrepare:
                    self.player_confirm_prepare(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.createRoom:
                    room_ID = self.player_create_room(message.playerID, message.webData)
                elif message.dataType == WEB_SYSTEM_DATATYPE.JOIN_ROOM:
                    self.player_join_room(message.playerID, message.roomData)
                elif message.dataType == WEB_SYSTEM_DATATYPE.askRoomStatus:
                    pass
                elif message.dataType == WEB_SYSTEM_DATATYPE.leaveRoom:
                    self.player_quit_room(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    self.player_log_out(message.playerID)
                self.player_send_room_status(message.playerID)
            else:
                logger.error(f"websystem_message_handler 收到了糟糕的消息:{message}")
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
        if message.playerID == -1:
            self.web_system_queue.put_nowait(message)
        elif message.playerID == -2:
            print(message.roomData)
        else:
            player = self.players[message.playerID]
            assert player != None
            assert player.playerRoom != None
            playerRoom = self.rooms[player.playerRoom]
            if playerRoom!=None and playerRoom.roomID == message.roomID:
                player.playerQueue.put_nowait(message)
        return
    async def playerGetMessage(self, playerIndex:playerWebSystemID, cookie:uuid.UUID)->MESSAGE:
        player = self.players[playerIndex]
        if player == None:
            #WARNING:这里的message不是从queue里取出来的哦
            return MESSAGE(-1,playerIndex,WEB_SYSTEM_DATATYPE.cookieWrong,None,None)
            #TODO
        else:
            if player.playerCookie == cookie:
                return await player.playerQueue.get()
            else:
                return MESSAGE(-1,playerIndex,WEB_SYSTEM_DATATYPE.cookieWrong,None,None)
    def playerSendMessage(self, message:MESSAGE, cookie:uuid.UUID):
        player = self.players[message.playerID]
        assert player != None and player.playerCookie == cookie
        if message.roomID == -1:
            self.web_system_queue.put_nowait(message)
        elif player.playerRoom == None:
            self.player_send_room_status(message.playerID)
        else:
            assert player.playerRoom == message.roomID
            room = self.rooms[player.playerRoom] 
            room.roomQueue.put_nowait(message)  #type:ignore

    #arg: legal systemID
    def player_send_room_status(self, systemID:playerWebSystemID)->None:
        logger.debug(f"i am sending to {systemID}")
        player = self.players[systemID]
        assert player != None   #type:ignore
        if player.playerRoom==None:
            frozen_room = None
        else:
            room = self.rooms[player.playerRoom]
            assert room != None #type:ignore
            frozen_room = FROZEN_ROOM(
                roomID=room.roomID,
                maxPlayer=room.maxPlayer,
                status=room.status,
                playerIndexs=[{"userName":self.players[index].playerName ,"ready":ready} for index, ready in room.playerIndexs]    #type:ignore
            )
        message = MESSAGE(
            -1,systemID,WEB_SYSTEM_DATATYPE.ANSWER_ROOM_STATUS,None,
            FROZEN_PLAYER_WEB_SYSTEM(
                playerName=player.playerName,
                playerLevel=player.playerLevel,
                playerRoom=frozen_room))
        logger.debug(f"i put {message}")
        player.playerQueue.put_nowait(message)

    #raise Error
    def PLAYER_REGISTER(self,playerName:str, password:str):
        self.sqlSystem.userRegister(playerName,password)
    
    #arg:legal or illegal playerName and password
    #raise:AuthError
    #ret:A player not in any room, or keep its origin room
    def PLAYER_LOG_IN(self, playerName:str, password:str) -> Tuple[uuid.UUID, playerWebSystemID]: # type:ignore
        systemID, level = self._checkPassword(playerName, password) 
        if level == PLAYER_LEVEL.superUser:
            raise AuthError("Super User?")
        elif level == PLAYER_LEVEL.normal:
            cookie = uuid.uuid4()
            if self.players[systemID] != None:
                self.players[systemID].playerCookie = cookie    #type:ignore
                return cookie, systemID
            player = WEB_PLAYER(systemID,
                                LockQueue(),
                                playerName=playerName,
                                playerRoom=None,
                                playerLevel=PLAYER_LEVEL.normal,
                                playerCookie=cookie)
            self.players[systemID] = player
            return cookie, systemID
        else:
            raise AuthError(f"Username or Password is wrong. 忘掉了请联系管理员桑呢\nUsername:{playerName}\n Password:{password}\n")     
    
    #arg:   player is already log in
    #       must not in any room
    #       room must be not full
    #raise: excpetion if the above is not satisfied
    def player_join_room(self,  systemID:playerWebSystemID, roomIndex:int) -> None:
        player = self.players[systemID]
        try:
            assert player != None
            assert player.playerRoom == None
        except:
            raise Exception("加你大爷")
        
        #get the room
        if roomIndex >= 0 and roomIndex <= self.maxRoom:     
            room = self.rooms[roomIndex]    
        else:
            raise IndexError("错误的房间喵喵")  #index error

                  
        if room == None:
            room = self._room_construst(roomIndex, systemID)  
            self.rooms[roomIndex] = room  
            self.hallQueue.put_nowait(
                MESSAGE(-1, playerWebSystemID(-1), WEB_SYSTEM_DATATYPE.createRoom, roomIndex, None))
        else:
            self._roomJoin(roomIndex,systemID)  #room error
        player.playerRoom = roomIndex
        player.playerQueue.put_nowait(
            MESSAGE(-1, systemID, WEB_SYSTEM_DATATYPE.logInSuccess, None, None))
    def player_confirm_prepare(self, systemID:playerWebSystemID):
        player = self.players[systemID]
        assert player != None
        assert player.playerRoom != None
        room = self.rooms[player.playerRoom]
        assert room != None
        cnt = 0
        for index, tuple in enumerate(room.playerIndexs):
            if tuple[0] == systemID:
                room.playerIndexs[index] = (systemID, True)
            if tuple[1] == True:
                cnt += 1
        if cnt == self._roomIndexToMaxPlayer(player.playerRoom) and room.status == ROOM_STATUS.preparing:
            room.roomQueue.put_nowait(
                MESSAGE(room.roomID,
                        playerWebSystemID(-1),
                        WEB_SYSTEM_DATATYPE.runRoom,
                        None,
                        None))
            room.status = ROOM_STATUS.running
    def player_log_out(self,systemID:playerWebSystemID):
        self.player_quit_room(systemID)
        self.players[systemID] = None
    def player_create_room(self,systemID:playerWebSystemID, expectedRoomMax:int)->int:
        room_ID = self._find_empty_room(expectedRoomMax)
        self.player_join_room(systemID, room_ID)
        return room_ID
    def player_quit_room(self,systemID:playerWebSystemID):
        player = self.players[systemID]
        assert player != None #type:ignore
        if player.playerRoom != None:
            room = self.rooms[player.playerRoom]
            room.removePlayer(player)   # type:ignore


    #safe
    def _room_destruct(self,roomIndex:int) -> None:
        room = self.rooms[roomIndex]
        for playerIndex, _ in room.playerIndexs:        #type: ignore
            self.players[playerIndex].playerRoom = None #type: ignore
        self.rooms[roomIndex] = None

    #not safe
    def _room_construst(self, roomIndex, firstPlayerIndex:playerWebSystemID)->WEB_ROOM:
        room = WEB_ROOM(roomID=roomIndex,
                        playerIndexs=[(firstPlayerIndex, False)],
                        roomQueue=LockQueue(),
                        maxPlayer=self._roomIndexToMaxPlayer(roomIndex),
                        status=ROOM_STATUS.preparing)
        return room
    #not safe
    def _roomJoin(self, roomIndex:int, playerIndex:playerWebSystemID) -> None:
        room = self.rooms[roomIndex]
        assert room != None
        if self._roomIndexToMaxPlayer(roomIndex) < len(room.playerIndexs):
            room.playerIndexs.append((playerIndex,False))
        else:
            raise RoomError("房满了,要不...踢个人?")
        return   

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
    def _find_empty_room(self, expected_max_player:int)->int:
        for i in range(self.maxRoom):
            if (self._roomIndexToMaxPlayer(i) == expected_max_player) and self.rooms[i] == None:
                return i
        raise RoomError(f"{expected_max_player}的房满了")


