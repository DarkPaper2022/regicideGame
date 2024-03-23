import uuid
import math
from dataclasses import dataclass
from defineRegicideMessage import GAME_SETTINGS
from defineWebSystemMessage import (
    MESSAGE,
    playerWebSystemID,
    PLAYER_LEVEL,
    WEB_SYSTEM_DATATYPE,
    ROOM_STATUS,
    DATA_UPDATE_PLAYER_STATUS,
    FROZEN_ROOM_STATUS_inWebSystem,
    PLAYER_STATUS,
    DINAL_TYPE,
    DATA_ANSWER_LOGIN,
)
from defineWebSystemMessage import *
from defineError import (
    AuthDenial,
    PlayerNumError,
    ServerBusyError,
    RoomDenial,
    RegisterDenial,
    AuthError,
    RoomFullDenial,
    RoomOutOfRangeDenial,
    RoomNotExistDenial,
)
from myLockQueue import myLockQueue as LockQueue
from collections import deque
from typing import List, Union, Tuple
from myLogger import logger
from enum import Enum
from DarkPaperMySQL import sqlSystem as sqlSystem


@dataclass
class WEB_PLAYER:
    # player is equal to a username,
    # if someone want to use the same player to play in the same room,
    # we should get the old player and change its cookie, keep its index
    # if someone want to player in other room
    # we should let the old room know,
    # so we need to change the room and send exception when the game is getting message, timeout or roomWrong

    playerIndex: playerWebSystemID
    playerQueue: LockQueue
    playerName: str
    playerRoom: Union[int, None]
    playerLevel: PLAYER_LEVEL
    playerCookie: uuid.UUID
    playerStatus: PLAYER_STATUS

    # arg: player should in the room and not a zombie
    # ret: deal with the player part, you should deal with the room part on your own
    def leave_room(self):
        self.playerRoom = None
        self.playerStatus = PLAYER_STATUS.ROOM_IS_NONE

    # different room, different player cookie
    # 可能持有一个糟糕的room,room方短线了,会给予用户很强的反馈


@dataclass
class WEB_ROOM:
    roomID: int
    # 可能持有一个拒绝一切消息的playerIndex,出于断线,只需放平心态,静候即可
    playerIndexs: List[playerWebSystemID]
    roomQueue: LockQueue
    maxPlayer: int
    status: ROOM_STATUS

    # arg: player should in the room and not a zombie
    # ret: deal with the room part, you should deal with the player part on your own
    def removePlayer(self, systemID: playerWebSystemID):
        player_out_of_room_message = MESSAGE(
            roomID=self.roomID,
            playerID=playerWebSystemID(-1),
            dataType=WEB_SYSTEM_DATATYPE.PLAYER_ESCAPE,
            roomData=None,
            webData=systemID,
        )
        self.roomQueue.put_nowait(player_out_of_room_message)  # type:ignore
        self.playerIndexs = [p for p in self.playerIndexs if p != systemID]


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

    players: List[Union[WEB_PLAYER, None]]
    rooms: List[Union[WEB_ROOM, None]]

    def __init__(self, maxPlayer: int, maxRoom) -> None:
        self.maxPlayer = maxPlayer  # should syntax with mysql
        self.maxRoom = maxRoom
        self.hallQueue = LockQueue()
        self.web_system_queue = LockQueue()
        self.players = [None] * maxPlayer  # maxplayer 很大
        self.rooms = [None] * maxRoom
        self.sqlSystem = sqlSystem()
        self.games = [FROZEN_GAME_TYPE("regicide", "1.1.0")]
        """
        binding     playerQueue-playerIndex-cookie-playerName
        cookie      playerName+password = cookie 
        """

    async def websystem_message_handler(self):
        while True:
            # arg: player or room of the message is not -1
            message: MESSAGE = await self.web_system_queue.get()
            logger.debug(message)
            if message.playerID == playerWebSystemID(-1):
                if message.dataType == WEB_SYSTEM_DATATYPE.destroyRoom:
                    self._room_destruct(message.roomID)

            elif message.roomID == -1:
                if message.dataType == WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE:
                    self.player_reverse_prepare(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM:
                    room_ID = self.player_create_room(message.playerID, message.webData)
                elif message.dataType == WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM:
                    try:
                        self.player_join_room(message.playerID, message.roomData)
                    except RoomDenial as e:
                        systemID = message.playerID
                        player: WEB_PLAYER = self.players[systemID]  # type:ignore
                        player.playerQueue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ANSWER_JOIN_ROOM,
                                None,
                                webData=DATA_ANSWER_JOIN_ROOM(
                                    False, e.enum()
                                ),
                            )
                        )
                    except Exception as e:
                        systemID = message.playerID
                        player: WEB_PLAYER = self.players[systemID]  # type:ignore
                        player.playerQueue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ERROR,
                                None,
                                webData=str(e),
                            )
                        )
                elif message.dataType == WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS:
                    pass
                elif message.dataType == WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM:
                    self.player_quit_room(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    self.player_log_out(message.playerID)
                    continue  # if you log out, your player will be none, so can't send room status
                self.player_send_room_status(message.playerID)
            else:
                logger.error(f"websystem_message_handler 收到了糟糕的消息:{message}")

    async def hallGetMessage(self) -> MESSAGE:
        message: MESSAGE = await self.hallQueue.get()
        return message

    async def roomGetMessage(self, roomIndex: int) -> MESSAGE:
        # 此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        room = self.rooms[roomIndex]
        if room != None:
            message = await room.roomQueue.get()
        return message

    def roomSendMessage(self, message: MESSAGE):
        # TODO:check it
        if message.playerID == -1:
            self.web_system_queue.put_nowait(message)
        elif message.playerID == -2:
            print(message.roomData)
        else:
            player = self.players[message.playerID]
            assert player != None
            assert player.playerRoom != None
            playerRoom = self.rooms[player.playerRoom]
            if playerRoom != None and playerRoom.roomID == message.roomID:
                player.playerQueue.put_nowait(message)
        return

    async def playerGetMessage(
        self, playerIndex: playerWebSystemID, cookie: uuid.UUID
    ) -> MESSAGE:
        player = self.players[playerIndex]
        if player == None:
            # WARNING:这里的message不是从queue里取出来的哦
            return MESSAGE(-1, playerIndex, WEB_SYSTEM_DATATYPE.cookieWrong, None, None)
            # TODO
        else:
            if player.playerCookie == cookie:
                return await player.playerQueue.get()
            else:
                return MESSAGE(
                    -1, playerIndex, WEB_SYSTEM_DATATYPE.cookieWrong, None, None
                )

    def playerSendMessage(self, message: MESSAGE, cookie: uuid.UUID):
        player = self.players[message.playerID]
        assert player != None and player.playerCookie == cookie
        if message.roomID == -1:
            self.web_system_queue.put_nowait(message)
        elif player.playerRoom == None:
            self.player_send_room_status(message.playerID)
        else:
            assert player.playerRoom == message.roomID
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore
            if room.status == ROOM_STATUS.running:
                room.roomQueue.put_nowait(message)
            else:
                self.player_send_room_status(message.playerID)

    # arg:   systemID should in [0,MAX)
    # arg:   status should be not none
    # raise: assertion error if status is not satisfied
    def player_send_room_status(self, systemID: playerWebSystemID) -> None:
        player = self.players[systemID]
        assert player != None
        if player.playerRoom == None:
            frozen_room = None
        else:
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore
            frozen_room = FROZEN_ROOM_STATUS_inWebSystem(
                roomID=room.roomID,
                maxPlayer=room.maxPlayer,
                status=room.status,
                playerIndexs=[
                    FROZEN_PLAYER_STATUS_SeenInRoom(
                        self.players[index].playerName,  # type:ignore
                        self.players[index].playerStatus,  # type:ignore
                    )
                    for index in room.playerIndexs
                ],
            )
        message = MESSAGE(
            -1,
            systemID,
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
            None,
            DATA_UPDATE_PLAYER_STATUS(
                playerName=player.playerName,
                playerLevel=player.playerLevel,
                playerRoom=frozen_room,
                playerStatus=player.playerStatus,
            ),
        )
        player.playerQueue.put_nowait(message)

    # raise Error
    def PLAYER_REGISTER(self, playerName: str, password: str):
        self.sqlSystem.userRegister(playerName, password)
    
    # arg:   legal or illegal playerName and password
    # raise: AuthError
    # ret:   A player not in any room, or keep its origin room
    def PLAYER_LOG_IN(
        self, playerName: str, password: str
    ) -> Tuple[uuid.UUID, playerWebSystemID]:
        systemID, level = self._checkPassword(playerName, password)
        if level == PLAYER_LEVEL.superUser:
            raise AuthDenial(DINAL_TYPE.LOGIN_SUPER_USER)
        elif level == PLAYER_LEVEL.normal:
            cookie = uuid.uuid4()
            if self.players[systemID] != None:
                self.player_log_out(systemID)

            # here the player is None or zombie
            old_player = self.players[systemID]
            if old_player == None:
                player = WEB_PLAYER(
                    systemID,
                    LockQueue(),
                    playerName=playerName,
                    playerRoom=None,
                    playerLevel=PLAYER_LEVEL.normal,
                    playerCookie=cookie,
                    playerStatus=PLAYER_STATUS.ROOM_IS_NONE,
                )
                self.players[systemID] = player
            else:
                old_player.playerCookie = cookie
                old_player.playerStatus = PLAYER_STATUS.IN_ROOM_PLAYING
                player = old_player

            message: MESSAGE = MESSAGE(
                -1,
                systemID,
                WEB_SYSTEM_DATATYPE.ANSWER_LOGIN,
                None,
                webData=DATA_ANSWER_LOGIN(success=True, error=None),
            )
            player.playerQueue.put_nowait(message)
            self.player_send_room_status(systemID)
            return cookie, systemID
        else:
            raise AuthError

    # arg:   player is already log in
    # arg:   must not in any room
    # arg:   room must be not full
    # raise: excpetion if the above is not satisfied
    def player_join_room(self, systemID: playerWebSystemID, roomIndex: int) -> None:
        player = self.players[systemID]
        try:
            assert player != None
            assert player.playerRoom == None
        except:
            raise PlayerNumError(f"{player}")

        # get the room
        if roomIndex >= 0 and roomIndex <= self.maxRoom:
            room = self.rooms[roomIndex]
        else:
            raise RoomOutOfRangeDenial  # index error

        if room == None:
            raise RoomNotExistDenial
        self._room_join_in_system(roomIndex, systemID)  # room error
        player.playerRoom = roomIndex
        player.playerStatus = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        player.playerQueue.put_nowait(
            MESSAGE(
                -1,
                systemID,
                WEB_SYSTEM_DATATYPE.ANSWER_JOIN_ROOM,
                None,
                webData=DATA_ANSWER_JOIN_ROOM(True, None),
            )
        )

    # arg:   systemID should in [0,MAX)
    # arg:   status should be in_room_not_prepared
    # raise: no error even status is not satisfied
    def player_reverse_prepare(self, systemID: playerWebSystemID):
        if self._status(systemID) == PLAYER_STATUS.IN_ROOM_PREPARED:
            player: WEB_PLAYER = self.players[systemID]  # type:ignore
            player.playerStatus = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
            return
        elif self._status(systemID) == PLAYER_STATUS.IN_ROOM_NOT_PREPARED:
            player: WEB_PLAYER = self.players[systemID]  # type:ignore
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore

            player.playerStatus = PLAYER_STATUS.IN_ROOM_PREPARED
            cnt = 0
            for a_systemID in room.playerIndexs:
                if (
                    self.players[a_systemID].playerStatus  # type:ignore
                    == PLAYER_STATUS.IN_ROOM_PREPARED  # type:ignore
                ):
                    cnt += 1

            if (
                cnt == self._room_ID_to_Max_player(room.roomID)
                and room.status == ROOM_STATUS.preparing
            ):
                self.room_run(room.roomID)
        else:
            pass

    # arg:   room is preparing
    # raise: assertion or attribute error
    def room_run(self, roomID: int):
        room: WEB_ROOM = self.rooms[roomID]  # type:ignore
        assert room.status == ROOM_STATUS.preparing
        room.roomQueue.put_nowait(
            MESSAGE(
                room.roomID,
                playerWebSystemID(-1),
                WEB_SYSTEM_DATATYPE.runRoom,
                None,
                [
                    (systemID, self.players[systemID].playerName)  #   type:ignore
                    for systemID in room.playerIndexs
                ],
            )
        )
        room.status = ROOM_STATUS.running
        for a_systemID in room.playerIndexs:
            self.players[a_systemID].playerStatus = (  # type:ignore
                PLAYER_STATUS.IN_ROOM_PLAYING
            )

    # arg: systemID should in [0,MAX)
    # arg: any status is OK
    def player_log_out(self, systemID: playerWebSystemID):
        if self._status(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING:
            self._change_player_to_zombie(systemID)
        else:
            self.player_quit_room(systemID)
            self.players[systemID] = None

    # arg:   systemID should in [0,MAX)
    # arg:   status should be room_is_none
    # raise: assertion error if status is not OK
    def player_create_room(
        self, systemID: playerWebSystemID, expectedRoomMax: int
    ) -> int:
        assert self._status(systemID) == PLAYER_STATUS.ROOM_IS_NONE
        room_ID = self._find_empty_room(expectedRoomMax)
        player = self.players[systemID]

        try:
            assert player != None
            assert player.playerRoom == None
        except:
            raise Exception("加你大爷")

        # get the room
        if room_ID >= 0 and room_ID <= self.maxRoom:
            room = self.rooms[room_ID]
        else:
            raise IndexError("错误的房间喵喵")  # index error

        room = self._room_construst(room_ID)
        self.rooms[room_ID] = room
        self.hallQueue.put_nowait(
            MESSAGE(
                -1,
                playerWebSystemID(-1),
                WEB_SYSTEM_DATATYPE.HALL_CREATE_ROOM,
                room_ID,
                None,
            )
        )
        self._room_join_in_system(room_ID, systemID)  # no room error, here
        player.playerRoom = room_ID
        player.playerStatus = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        return room_ID

    # arg:   systemID should in [0,MAX)
    # arg:   status can be any
    def player_quit_room(self, systemID: playerWebSystemID):
        if self._status(systemID) in [
            PLAYER_STATUS.IN_ROOM_PREPARED,
            PLAYER_STATUS.IN_ROOM_NOT_PREPARED,
        ]:
            player: WEB_PLAYER = self.players[systemID]  # type:ignore
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore
            room.removePlayer(systemID)
            player.leave_room()
        elif self._status(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING:
            self._change_player_to_zombie(systemID)
        else:
            pass

    # safe
    # arg: room is not none
    def _room_destruct(self, roomIndex: int) -> None:
        room: WEB_ROOM = self.rooms[roomIndex]  # type:ignore
        for playerIndex in room.playerIndexs:
            player: WEB_PLAYER = self.players[playerIndex]  # type: ignore
            if self._status(playerIndex) == PLAYER_STATUS.IN_ROOM_ZOMBIE:
                self.players[playerIndex] = None
            else:
                player.leave_room()
        self.rooms[roomIndex] = None

    # not safe
    def _room_construst(self, roomIndex) -> WEB_ROOM:
        room = WEB_ROOM(
            roomID=roomIndex,
            playerIndexs=[],
            roomQueue=LockQueue(),
            maxPlayer=self._room_ID_to_Max_player(roomIndex),
            status=ROOM_STATUS.preparing,
        )
        return room

    # arg:  room and systemID are legal
    # raise:RoomError
    def _room_join_in_system(self, roomIndex: int, systemID: playerWebSystemID) -> None:
        room: WEB_ROOM = self.rooms[roomIndex]  # type:ignore
        if self._room_ID_to_Max_player(roomIndex) > len(room.playerIndexs):
            room.playerIndexs.append(systemID)
        else:
            raise RoomFullDenial

    # raise: AuthDinal
    def _checkPassword(
        self, playerName: str, password: str
    ) -> Tuple[playerWebSystemID, PLAYER_LEVEL]:
        re = self.sqlSystem.checkPassword(playerName, password)
        return re

    def _checkOldCookie(
        self, playerIndex: playerWebSystemID, oldCookie: uuid.UUID
    ) -> PLAYER_LEVEL:
        p = self.players[playerIndex]
        if p == None:
            return PLAYER_LEVEL.illegal
        else:
            level = (
                p.playerLevel if p.playerCookie == oldCookie else PLAYER_LEVEL.illegal
            )
            return level

    def _room_ID_to_Max_player(self, roomIndex: int) -> int:
        if roomIndex >= 0 and roomIndex < self.maxRoom:
            re = math.floor(roomIndex / 100) + 2
            re = re if (re in [2, 3, 4]) else 2
            return re
        else:
            logger.error(f"这里炸了,{roomIndex}被送进来了")
            return 2

    def _find_empty_room(self, expected_max_player: int) -> int:
        for i in range(self.maxRoom):
            if (self._room_ID_to_Max_player(i) == expected_max_player) and self.rooms[
                i
            ] == None:
                return i
        raise ServerBusyError("Sorry")

    # arg:   systemID should in [0,MAX)
    # arg:   status should be in_room_playing
    # raise: assertion error

    def _change_player_to_zombie(self, systemID: playerWebSystemID):

        assert self._status(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING

        self.players[systemID].playerStatus = (  # type:ignore
            PLAYER_STATUS.IN_ROOM_ZOMBIE
        )
        room: WEB_ROOM = self.rooms[self.players[systemID].playerRoom]  # type:ignore
        room.roomQueue.put_nowait(
            MESSAGE(
                roomID=room.roomID,
                playerID=playerWebSystemID(-1),
                dataType=WEB_SYSTEM_DATATYPE.HE_IS_A_ZOMBIE,
                roomData=None,
                webData=systemID,
            )
        )

    # arg: systemID should in [0,MAX)
    def _status(self, systemID: playerWebSystemID) -> PLAYER_STATUS:
        player = self.players[systemID]
        if player == None:
            return PLAYER_STATUS.NONE
        else:
            return player.playerStatus

    def _check_game_vesion(self, game: FROZEN_GAME_TYPE) -> bool:
        return game.name in [game.name for game in self.games]
