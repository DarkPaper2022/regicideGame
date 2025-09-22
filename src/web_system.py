from http.cookies import CookieError
import uuid
import math
from dataclasses import dataclass
from src.include.defineWebSystemMessage import (
    MESSAGE,
    playerWebSystemID,
    PLAYER_LEVEL,
    WEB_SYSTEM_DATATYPE,
    ROOM_STATUS,
    DATA_UPDATE_PLAYER_STATUS,
    FROZEN_ROOM_STATUS_inWebSystem,
    PLAYER_STATUS,
)

from src.include.defineWebSystemMessage import *
from src.include.defineError import (
    AuthDenial,
    CookieDenial,
    Denial,
    PlayerStatusDenial,
    RoomSatusDenial,
    ServerBusyDenial,
    RoomDenial,
    RegisterDenial,
    AuthError,
    RoomFullDenial,
    RoomOutOfRangeDenial,
    RoomNotExistDenial,
)
from src.include.myLockQueue import myLockQueue as LockQueue
from collections import deque
from typing import List, Union, Tuple, Optional
from src.include.myLogger import logger
from enum import Enum
from src.include.DarkPaperMySQL import sqlSystem as sqlSystem
from importlib import metadata

room_ID_WEBSYSTEM = -1
player_ID_WEBSYSTEM = playerWebSystemID(-1)


def get_version() -> str:
    import os

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(current_dir, "VERSION"), "r") as f:
        version = f.read().strip()
    return version


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
    def remove_room(self):
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
    def remove_player(self, systemID: playerWebSystemID):
        player_out_of_room_message = MESSAGE(
            roomID=self.roomID,
            playerID=player_ID_WEBSYSTEM,
            data_type=WEB_SYSTEM_DATATYPE.PLAYER_ESCAPE,
            roomData=None,
            webData=systemID,
        )
        self.roomQueue.put_nowait(player_out_of_room_message)
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

    spec:
        elements, connection, message

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
        self.games = [FROZEN_GAME_TYPE("regicide", get_version())]
        """
        binding     playerQueue-playerIndex-cookie-playerName
        cookie      playerName+password = cookie 
        """

    async def websystem_message_handler(self) -> None:
        while True:
            # arg: player or room of the message is not -1
            message = await self.web_system_queue.get()
            logger.debug(message)
            if message.playerID == player_ID_WEBSYSTEM:
                if message.data_type == WEB_SYSTEM_DATATYPE.destroyRoom:
                    self._room_destruct(message.roomID)

            elif message.roomID == room_ID_WEBSYSTEM:
                player: WEB_PLAYER = self.players[message.playerID]  # type:ignore
                if message.data_type == WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE:
                    try:
                        self.player_reverse_prepare(message.playerID)
                        self.broadcast_room_status(player.playerRoom)
                    except Denial as e:
                        systemID = message.playerID
                        player.playerQueue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.DENIAL,
                                None,
                                webData=e.enum(),
                            )
                        )
                        self.player_send_room_status(message.playerID)
                elif message.data_type == WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM:
                    try:
                        self.player_create_room(message.playerID, message.webData)
                        self.player_send_room_status(message.playerID)
                    except Denial as e:
                        logger.info(f"create room, but failed {e.enum().name}")
                        systemID = message.playerID
                        player.playerQueue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ANSWER_CREATE_ROOM,
                                None,
                                webData=DATA_SIMPLE_ANSWER(False, e.enum()),
                            )
                        )
                        self.player_send_room_status(message.playerID)
                elif message.data_type == WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM:
                    try:
                        self.player_join_room(message.playerID, message.webData)
                        self.broadcast_room_status(player.playerRoom)
                    except Denial as e:
                        systemID = message.playerID
                        player.playerQueue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ANSWER_JOIN_ROOM,
                                None,
                                webData=DATA_SIMPLE_ANSWER(False, e.enum()),
                            )
                        )
                        self.player_send_room_status(message.playerID)
                elif message.data_type == WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS:
                    self.player_send_room_status(message.playerID)
                elif message.data_type == WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM:
                    roomID = player.playerRoom
                    self.player_quit_room(message.playerID)
                    self.broadcast_room_status(roomID)
                    self.player_send_room_status(message.playerID)
                elif message.data_type == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    roomID = player.playerRoom
                    self.player_log_out(message.playerID)
                    self.broadcast_room_status(roomID)
                    continue  # if you log out, your player will be none, so can't send room status
            else:
                logger.error(f"websystem_message_handler 收到了糟糕的消息:{message}")

    async def hallGetMessage(self) -> MESSAGE:
        message: MESSAGE = await self.hallQueue.get()
        return message

    async def roomGetMessage(self, roomIndex: int) -> MESSAGE:
        # 此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        room = self.rooms[roomIndex]
        if room is not None:
            message = await room.roomQueue.get()
        return message

    def roomSendMessage(self, message: MESSAGE):
        # TODO:check it
        if message.playerID == player_ID_WEBSYSTEM:
            self.web_system_queue.put_nowait(message)
        elif message.playerID == -2:
            print(message.roomData)
        else:
            player = self.players[message.playerID]
            if player is None:
                raise Exception(
                    f"player {message.playerID} not found while room sending message."
                )
            player.playerQueue.put_nowait(message)
        return

    async def playerGetMessage(
        self, playerIndex: playerWebSystemID, cookie: uuid.UUID
    ) -> MESSAGE:
        player = self.players[playerIndex]
        if player is None:
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

    def player_send_message(self, message: MESSAGE, cookie: uuid.UUID):
        player = self.players[message.playerID]
        if player is None:
            logger.error(f"player {message.playerID} not in system")
            raise PlayerStatusDenial(f"player {message.playerID} not in system")
        if player.playerCookie != cookie:
            raise CookieDenial(f"{message.playerID} cookie wrong")
        if message.roomID == room_ID_WEBSYSTEM:
            self.web_system_queue.put_nowait(message)
        elif player.playerRoom is None:
            self.player_send_room_status(message.playerID)
        else:
            if player.playerRoom != message.roomID:  # admin don't go here
                raise PlayerStatusDenial(f"Strange player:{player} send message.")
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore
            if room.status == ROOM_STATUS.running:
                logger.debug(f"message arrive web_system: {message.data_type.name}")
                room.roomQueue.put_nowait(message)
            else:
                self.player_send_room_status(message.playerID)

    def adminSendMessage(self, message: MESSAGE, cookie: uuid.UUID):
        admin = self.players[message.playerID]
        if not (
            admin is not None
            and admin.playerCookie == cookie
            and admin.playerLevel == PLAYER_LEVEL.superUser
        ):
            raise PlayerStatusDenial(f"Strange player:{admin} send message.")
        if message.data_type in admin_types:
            logger.info(f"adminSendMessage: {message}")
            if message.roomID == -1:
                self.web_system_queue.put_nowait(message)
            else:
                room = self.rooms[message.roomID]
                if room is None:
                    raise RoomNotExistDenial
                room.roomQueue.put_nowait(message)
        else:
            self.player_send_message(message, cookie)

    def broadcast_room_status(self, roomID: Optional[int]):
        if roomID is None:
            return
        room = self.rooms[roomID]
        if room is None:
            return
        try:
            for id in room.playerIndexs:
                self.player_send_room_status(id)
        except PlayerStatusDenial:
            logger.error(f"player {id} not in system")

    def player_send_room_status(self, systemID: playerWebSystemID) -> None:
        """
        arg:   systemID should in [0,MAX)
        arg:   status should be not none
        raise: PlayerStatusDenial if status is not satisfied
        """
        player = self.players[systemID]
        if player is None:
            raise PlayerStatusDenial(f"player not found message.")
        if player.playerRoom is None:
            frozen_room = None
        else:
            room = self.rooms[player.playerRoom]
            assert room is not None
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
            room_ID_WEBSYSTEM,
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
    ) -> Tuple[uuid.UUID, playerWebSystemID, PLAYER_LEVEL]:
        logger.debug(f"""login :{playerName}, {password}""")
        systemID, level = self._check_password(playerName, password)
        if level in [PLAYER_LEVEL.superUser, PLAYER_LEVEL.normal]:
            cookie = uuid.uuid4()
            if self.players[systemID] is not None:
                self.player_log_out(systemID)

            # here the player is None or zombie
            old_player = self.players[systemID]
            if old_player is None:
                player = WEB_PLAYER(
                    systemID,
                    LockQueue(),
                    playerName=playerName,
                    playerRoom=None,
                    playerLevel=level,
                    playerCookie=cookie,
                    playerStatus=PLAYER_STATUS.ROOM_IS_NONE,
                )
                self.players[systemID] = player
            else:
                old_player.playerCookie = cookie
                old_player.playerStatus = PLAYER_STATUS.IN_ROOM_PLAYING
                self.players[systemID] = old_player
                player = old_player

            message: MESSAGE = MESSAGE(
                -1,
                systemID,
                WEB_SYSTEM_DATATYPE.ANSWER_LOGIN,
                None,
                webData=DATA_SIMPLE_ANSWER(success=True, error=None),
            )
            player.playerQueue.put_nowait(message)
            self.player_send_room_status(systemID)
            logger.debug(f"login succeed. status:{player.playerStatus.name}")
            return cookie, systemID, level
        else:
            # unsupported player level
            raise AuthError

    def player_join_room(self, systemID: playerWebSystemID, roomIndex: int) -> None:
        """
        arg:   player is already log in
        arg:   must not in any room
        arg:   room must be not full
        raise: denail if the above is not satisfied
        """
        player = self.players[systemID]
        if player is None or player.playerRoom is not None:
            raise PlayerStatusDenial(f"Strange player:{player} join room.")

        # get the room
        if roomIndex >= 0 and roomIndex <= self.maxRoom:
            room = self.rooms[roomIndex]
        else:
            raise RoomOutOfRangeDenial  # index error

        if room is None:
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
                webData=DATA_SIMPLE_ANSWER(True, None),
            )
        )

    def player_reverse_prepare(self, systemID: playerWebSystemID):
        """
        arg:   systemID should in [0,MAX)
        arg:   status should be in_room_not_prepared
        raise: status denial if status is not satisfied
        """
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
                    == PLAYER_STATUS.IN_ROOM_PREPARED
                ):
                    cnt += 1

            if (
                cnt == self._room_ID_to_Max_player(room.roomID)
                and room.status == ROOM_STATUS.preparing
            ):
                self.room_run(room.roomID)
        else:
            raise PlayerStatusDenial(f"Strange player:{systemID} reverse prepare.")

    # arg:   room is preparing
    # raise: denial or attribute error
    def room_run(self, roomID: int):
        room: WEB_ROOM = self.rooms[roomID]  # type:ignore
        if room.status != ROOM_STATUS.preparing:
            raise RoomSatusDenial
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
        logger.debug("runRoom message sending to room")
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

    def player_create_room(
        self, systemID: playerWebSystemID, expectedRoomMax: int
    ) -> int:
        """
        arg:   systemID should in [0,MAX)
        arg:   status should be room_is_none
        raise: room denial if status is not OK
        """
        player = self.players[systemID]
        if self._status(systemID) != PLAYER_STATUS.ROOM_IS_NONE:
            raise PlayerStatusDenial(f"Strange player:{systemID} create room.")
        if player is None or player.playerRoom is not None:
            raise Exception(
                "player status not consist."
            )  # the check above should keep it

        room_ID = self._find_empty_room(expectedRoomMax)
        # get the room
        if room_ID >= 0 and room_ID <= self.maxRoom:
            room = self.rooms[room_ID]
        else:
            raise RoomOutOfRangeDenial

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
        self._room_join_in_system(
            room_ID, systemID
        )  # no room error here, because empty room can always join one
        player.playerRoom = room_ID
        player.playerStatus = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        return room_ID

    def player_quit_room(self, systemID: playerWebSystemID):
        """
        arg:   systemID should in [0,MAX)
        arg:   status can be any
        """
        if self._status(systemID) in [
            PLAYER_STATUS.IN_ROOM_PREPARED,
            PLAYER_STATUS.IN_ROOM_NOT_PREPARED,
        ]:
            player: WEB_PLAYER = self.players[systemID]  # type:ignore
            room: WEB_ROOM = self.rooms[player.playerRoom]  # type:ignore
            room.remove_player(systemID)
            player.remove_room()
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
                player.remove_room()
        self.rooms[roomIndex] = None

    # not safe
    def _room_construst(self, roomIndex: int) -> WEB_ROOM:
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
    def _check_password(
        self, playerName: str, password: str
    ) -> Tuple[playerWebSystemID, PLAYER_LEVEL]:
        re = self.sqlSystem.checkPassword(playerName, password)
        return re

    def _checkOldCookie(
        self, playerIndex: playerWebSystemID, oldCookie: uuid.UUID
    ) -> PLAYER_LEVEL:
        p = self.players[playerIndex]
        if p is None:
            return PLAYER_LEVEL.illegal
        else:
            level = (
                p.playerLevel if p.playerCookie == oldCookie else PLAYER_LEVEL.illegal
            )
            return level

    def _room_ID_to_Max_player(self, roomIndex: int) -> int:
        if roomIndex >= 10 and roomIndex < self.maxRoom:
            re = math.floor(roomIndex / 100) + 2
            re = re if (re in [2, 3, 4]) else 2
            return re
        else:
            logger.error(f"这里炸了,{roomIndex}被送进来了")
            return 0

    def _find_empty_room(self, expected_max_player: int) -> int:
        for i in range(15, self.maxRoom):
            if (self._room_ID_to_Max_player(i) == expected_max_player) and self.rooms[
                i
            ] is None:
                return i
        raise ServerBusyDenial

    def _change_player_to_zombie(self, systemID: playerWebSystemID):
        """
        arg:   systemID should in [0,MAX)
        arg:   status should be in_room_playing
        raise: exception if the caller don't check the status
        """
        if self._status(systemID) != PLAYER_STATUS.IN_ROOM_PLAYING:
            raise Exception("player status not consist")

        self.players[systemID].playerStatus = (  # type:ignore
            PLAYER_STATUS.IN_ROOM_ZOMBIE
        )
        room: WEB_ROOM = self.rooms[self.players[systemID].playerRoom]  # type:ignore
        room.roomQueue.put_nowait(
            MESSAGE(
                roomID=room.roomID,
                playerID=playerWebSystemID(-1),
                data_type=WEB_SYSTEM_DATATYPE.HE_IS_A_ZOMBIE,
                roomData=None,
                webData=systemID,
            )
        )

    # arg: systemID should in [0,MAX)
    def _status(self, systemID: playerWebSystemID) -> PLAYER_STATUS:
        player = self.players[systemID]
        if player is None:
            return PLAYER_STATUS.NONE
        else:
            return player.playerStatus

    def _check_game_vesion(self, game: FROZEN_GAME_TYPE) -> bool:
        return game.name in [game.name for game in self.games]

    def end_sql(self):
        self.sqlSystem.end()
