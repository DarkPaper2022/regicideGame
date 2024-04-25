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
from typing import *
from myLogger import logger
from enum import Enum
from DarkPaperMySQL import sqlSystem as sqlSystem
from importlib import metadata


def get_version() -> str:
    import os

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(current_dir, "VERSION"), "r") as f:
        version = f.read().strip()
    return version


@dataclass
class WebPlayer:
    # player is equal to a username,
    # if someone want to use the same player to play in the same room,
    # we should get the old player and change its cookie, keep its index
    # if someone want to player in other room
    # we should let the old room know,
    # so we need to change the room and send exception when the game is getting message, timeout or roomWrong

    index: playerWebSystemID
    queue: LockQueue
    name: str
    room: Union[int, None]
    level: PLAYER_LEVEL
    cookie: uuid.UUID
    status: PLAYER_STATUS

    # arg: player should in the room and not a zombie
    # ret: deal with the player part, you should deal with the room part on your own
    def leave_room(self):
        self.room = None
        self.status = PLAYER_STATUS.ROOM_IS_NONE

    # different room, different player cookie
    # 可能持有一个糟糕的room,room方短线了,会给予用户很强的反馈


@dataclass
class WebRoom:
    room_id: int
    # 可能持有一个拒绝一切消息的playerIndex,出于断线,只需放平心态,静候即可
    player_indexs: List[playerWebSystemID]
    room_queue: LockQueue
    max_player: int
    status: ROOM_STATUS

    # arg: player should in the room and not a zombie
    # ret: deal with the room part, you should deal with the player part on your own
    def remove_player(self, systemID: playerWebSystemID):
        player_out_of_room_message = MESSAGE(
            roomID=self.room_id,
            playerID=playerWebSystemID(-1),
            dataType=WEB_SYSTEM_DATATYPE.PLAYER_ESCAPE,
            roomData=None,
            webData=systemID,
        )
        self.room_queue.put_nowait(player_out_of_room_message)  # type:ignore
        self.player_indexs = [p for p in self.player_indexs if p != systemID]


class PlayerMannager:
    the_set: Dict[playerWebSystemID, WebPlayer]

    def __init__(self) -> None:
        # TODO maybe load something ?
        self.the_set = {}

    def set(self, id: playerWebSystemID, player: Optional[WebPlayer]) -> None:
        if player is None:
            del self.the_set[id]
        else:
            self.the_set[id] = player

    def get(self, id: playerWebSystemID) -> Optional[WebPlayer]:
        return self.the_set.get(id, None)

    # arg: systemID should in [0,MAX)
    def get_type(self, id: playerWebSystemID) -> PLAYER_STATUS:
        player = self.get(id)
        if player == None:
            return PLAYER_STATUS.NONE
        else:
            return player.status


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

    players: PlayerMannager
    rooms: List[Union[WebRoom, None]]

    def __init__(self, maxPlayer: int, maxRoom) -> None:
        self.maxPlayer = maxPlayer  # should syntax with mysql
        self.maxRoom = maxRoom
        self.hall_queue = LockQueue()
        self.web_system_queue = LockQueue()
        self.players = PlayerMannager()
        self.rooms = [None] * maxRoom
        self.accounts_data_manager = sqlSystem()
        self.games = [FROZEN_GAME_TYPE("regicide", get_version())]
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
                player: WebPlayer = self.players.get(message.playerID)  # type:ignore
                if message.dataType == WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE:
                    self.player_reverse_prepare(message.playerID)
                    self.broadcast_room_status(player.room)
                elif message.dataType == WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM:
                    self.player_create_room(message.playerID, message.webData)
                    self.player_send_room_status(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM:
                    try:
                        self.player_join_room(message.playerID, message.roomData)
                        self.broadcast_room_status(player.room)
                    except RoomDenial as e:
                        systemID = message.playerID
                        player.queue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ANSWER_JOIN_ROOM,
                                None,
                                webData=DATA_ANSWER_JOIN_ROOM(False, e.enum()),
                            )
                        )
                        self.player_send_room_status(message.playerID)
                    except Exception as e:
                        systemID = message.playerID
                        player.queue.put_nowait(
                            MESSAGE(
                                -1,
                                systemID,
                                WEB_SYSTEM_DATATYPE.ERROR,
                                None,
                                webData=str(e),
                            )
                        )
                elif message.dataType == WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS:
                    self.player_send_room_status(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM:
                    roomID = player.room
                    self.player_quit_room(message.playerID)
                    self.broadcast_room_status(roomID)
                    self.player_send_room_status(message.playerID)
                elif message.dataType == WEB_SYSTEM_DATATYPE.LOG_OUT:
                    roomID = player.room
                    self.player_log_out(message.playerID)
                    self.broadcast_room_status(roomID)
                    # if you log out, your player will be none, so can't send room status
                else:
                    logger.error(
                        f"websystem_message_handler 收到了糟糕的消息:{message}"
                    )
            else:
                logger.error(f"websystem_message_handler 收到了糟糕的消息:{message}")

    async def hall_get_message(self) -> MESSAGE:
        message: MESSAGE = await self.hall_queue.get()
        return message

    async def room_get_message(self, roomIndex: int) -> MESSAGE:
        # 此处应当持续接收各个线程的输入，接到game需要的那个为止(这个事儿在game里实现了)
        room = self.rooms[roomIndex]
        if room != None:
            message = await room.room_queue.get()
        return message

    def room_send_message(self, message: MESSAGE):
        # TODO:check it
        if message.playerID == -1:
            self.web_system_queue.put_nowait(message)
        elif message.playerID == -2:
            print(message.roomData)
        else:
            player = self.players.get(message.playerID)
            assert player != None
            assert player.room != None
            playerRoom = self.rooms[player.room]
            if playerRoom != None and playerRoom.room_id == message.roomID:
                player.queue.put_nowait(message)

    async def player_get_message(
        self, playerIndex: playerWebSystemID, cookie: uuid.UUID
    ) -> MESSAGE:
        player = self.players.get(playerIndex)
        if player != None and player.cookie == cookie:
            return await player.queue.get()
        else:
            return MESSAGE(-1, playerIndex, WEB_SYSTEM_DATATYPE.cookieWrong, None, None)

    def player_send_message(self, message: MESSAGE, cookie: uuid.UUID):
        player = self.players.get(message.playerID)
        assert player != None and player.cookie == cookie
        if message.roomID == -1:
            self.web_system_queue.put_nowait(message)
        elif player.room == None:
            self.player_send_room_status(message.playerID)
        else:
            assert player.room == message.roomID
            room: WebRoom = self.rooms[player.room]  # type:ignore
            if room.status == ROOM_STATUS.running:
                room.room_queue.put_nowait(message)
            else:
                self.player_send_room_status(message.playerID)

    # arg: roomID can be None, we do nothing
    # arg: roomID should in [0,MAX)
    def broadcast_room_status(self, roomID: Optional[int]):
        if roomID is None:
            return
        room = self.rooms[roomID]
        if room is None:
            return
        for id in room.player_indexs:
            self.player_send_room_status(id)

    # arg:   systemID should in [0,MAX)
    # arg:   status should be not none
    # raise: assertion error if status is not satisfied
    def player_send_room_status(self, systemID: playerWebSystemID) -> None:
        player = self.players.get(systemID)
        assert player != None
        if player.room == None:
            frozen_room = None
        else:
            room: WebRoom = self.rooms[player.room]  # type:ignore
            frozen_room = FROZEN_ROOM_STATUS_inWebSystem(
                roomID=room.room_id,
                maxPlayer=room.max_player,
                status=room.status,
                playerIndexs=[
                    FROZEN_PLAYER_STATUS_SeenInRoom(
                        self.players.get(index).name,  # type:ignore
                        self.players.get(index).status,  # type:ignore
                    )
                    for index in room.player_indexs
                ],
            )
        message = MESSAGE(
            -1,
            systemID,
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
            None,
            DATA_UPDATE_PLAYER_STATUS(
                playerName=player.name,
                playerLevel=player.level,
                playerRoom=frozen_room,
                playerStatus=player.status,
            ),
        )
        player.queue.put_nowait(message)

    # raise Error
    def pub_register(self, playerName: str, password: str):
        self.accounts_data_manager.userRegister(playerName, password)

    # arg:   legal or illegal playerName and password
    # raise: AuthError
    # ret:   A player not in any room, or keep its origin room
    def pub_login(
        self, playerName: str, password: str
    ) -> Tuple[uuid.UUID, playerWebSystemID]:
        logger.debug(f"""login :{playerName}, {password}""")
        systemID, level = self._checkPassword(playerName, password)
        if level == PLAYER_LEVEL.superUser:
            raise AuthDenial(DINAL_TYPE.LOGIN_SUPER_USER)
        elif level == PLAYER_LEVEL.normal:
            cookie = uuid.uuid4()
            if self.players.get(systemID) != None:
                self.player_log_out(systemID)

            # here the player is None or zombie
            old_player = self.players.get(systemID)
            if old_player == None:
                player = WebPlayer(
                    systemID,
                    LockQueue(),
                    name=playerName,
                    room=None,
                    level=PLAYER_LEVEL.normal,
                    cookie=cookie,
                    status=PLAYER_STATUS.ROOM_IS_NONE,
                )
                self.players.set(systemID, player)
            else:
                old_player.cookie = cookie
                old_player.status = PLAYER_STATUS.IN_ROOM_PLAYING
                player = old_player

            message: MESSAGE = MESSAGE(
                -1,
                systemID,
                WEB_SYSTEM_DATATYPE.ANSWER_LOGIN,
                None,
                webData=DATA_ANSWER_LOGIN(success=True, error=None),
            )
            player.queue.put_nowait(message)
            self.player_send_room_status(systemID)
            return cookie, systemID
        else:
            raise AuthError

    # arg:   player is already log in
    # arg:   must not in any room
    # arg:   room must be not full
    # raise: excpetion if the above is not satisfied
    def player_join_room(self, systemID: playerWebSystemID, roomIndex: int) -> None:
        player = self.players.get(systemID)
        try:
            assert player != None
            assert player.room == None
        except AssertionError:
            raise PlayerNumError(f"{player}")

        # get the room
        if roomIndex >= 0 and roomIndex <= self.maxRoom:
            room = self.rooms[roomIndex]
        else:
            raise RoomOutOfRangeDenial  # index error

        if room == None:
            raise RoomNotExistDenial
        self._room_join_in_system(roomIndex, systemID)  # room error
        player.room = roomIndex
        player.status = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        player.queue.put_nowait(
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
        if self.players.get_type(systemID) == PLAYER_STATUS.IN_ROOM_PREPARED:
            player: WebPlayer = self.players.get(systemID)  # type:ignore
            player.status = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        elif self.players.get_type(systemID) == PLAYER_STATUS.IN_ROOM_NOT_PREPARED:
            player: WebPlayer = self.players.get(systemID)  # type:ignore
            room: WebRoom = self.rooms[player.room]  # type:ignore

            player.status = PLAYER_STATUS.IN_ROOM_PREPARED
            cnt = 0
            for a_systemID in room.player_indexs:
                if (
                    self.players.get_type(a_systemID)  # type:ignore
                    == PLAYER_STATUS.IN_ROOM_PREPARED  # type:ignore
                ):
                    cnt += 1

            if (
                cnt == self._room_ID_to_Max_player(room.room_id)
                and room.status == ROOM_STATUS.preparing
            ):
                self.room_run(room.room_id)

    # arg:   room is preparing
    # raise: assertion or attribute error
    def room_run(self, roomID: int):
        room: WebRoom = self.rooms[roomID]  # type:ignore
        assert room.status == ROOM_STATUS.preparing
        room.room_queue.put_nowait(
            MESSAGE(
                room.room_id,
                playerWebSystemID(-1),
                WEB_SYSTEM_DATATYPE.runRoom,
                None,
                [
                    (systemID, self.players.get(systemID).name)  #   type:ignore
                    for systemID in room.player_indexs
                ],
            )
        )
        room.status = ROOM_STATUS.running
        for a_systemID in room.player_indexs:
            self.players.get(a_systemID).status = (  # type:ignore
                PLAYER_STATUS.IN_ROOM_PLAYING
            )

    # arg: systemID should in [0,MAX)
    # arg: any status is OK
    def player_log_out(self, systemID: playerWebSystemID):
        if self.players.get_type(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING:
            self._change_player_to_zombie(systemID)
        else:
            self.player_quit_room(systemID)
            self.players.set(systemID,None)

    # arg:   systemID should in [0,MAX)
    # arg:   status should be room_is_none
    # raise: assertion error if status is not OK
    def player_create_room(
        self, systemID: playerWebSystemID, expectedRoomMax: int
    ) -> int:
        assert self.players.get_type(systemID) == PLAYER_STATUS.ROOM_IS_NONE
        room_ID = self._find_empty_room(expectedRoomMax)
        player = self.players.get(systemID)

        try:
            assert player != None
            assert player.room == None
        except:
            raise Exception("加你大爷")

        # get the room
        if room_ID >= 0 and room_ID <= self.maxRoom:
            room = self.rooms[room_ID]
        else:
            raise IndexError("错误的房间喵喵")  # index error

        room = self._room_construst(room_ID)
        self.rooms[room_ID] = room
        self.hall_queue.put_nowait(
            MESSAGE(
                -1,
                playerWebSystemID(-1),
                WEB_SYSTEM_DATATYPE.HALL_CREATE_ROOM,
                room_ID,
                None,
            )
        )
        self._room_join_in_system(room_ID, systemID)  # no room error, here
        player.room = room_ID
        player.status = PLAYER_STATUS.IN_ROOM_NOT_PREPARED
        return room_ID

    # arg:   systemID should in [0,MAX)
    # arg:   status can be any
    def player_quit_room(self, systemID: playerWebSystemID):
        if self.players.get_type(systemID) in [
            PLAYER_STATUS.IN_ROOM_PREPARED,
            PLAYER_STATUS.IN_ROOM_NOT_PREPARED,
        ]:
            player: WebPlayer = self.players[systemID]  # type:ignore
            room: WebRoom = self.rooms[player.room]  # type:ignore
            room.remove_player(systemID)
            player.leave_room()
        elif self.players.get_type(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING:
            self._change_player_to_zombie(systemID)


    # safe
    # arg: room is not none
    def _room_destruct(self, roomIndex: int) -> None:
        room: WebRoom = self.rooms[roomIndex]  # type:ignore
        for playerIndex in room.player_indexs:
            player: WebPlayer = self.players.get(playerIndex)  # type: ignore
            if self.players.get_type(playerIndex) == PLAYER_STATUS.IN_ROOM_ZOMBIE:
                self.players.set(playerIndex,None)
            else:
                player.leave_room()
        self.rooms[roomIndex] = None

    # not safe
    def _room_construst(self, roomIndex) -> WebRoom:
        room = WebRoom(
            room_id=roomIndex,
            player_indexs=[],
            room_queue=LockQueue(),
            max_player=self._room_ID_to_Max_player(roomIndex),
            status=ROOM_STATUS.preparing,
        )
        return room

    # arg:  room and systemID are legal
    # raise:RoomError
    def _room_join_in_system(self, roomIndex: int, systemID: playerWebSystemID) -> None:
        room: WebRoom = self.rooms[roomIndex]  # type:ignore
        if self._room_ID_to_Max_player(roomIndex) > len(room.player_indexs):
            room.player_indexs.append(systemID)
        else:
            raise RoomFullDenial

    # raise: AuthDinal
    def _checkPassword(
        self, playerName: str, password: str
    ) -> Tuple[playerWebSystemID, PLAYER_LEVEL]:
        re = self.accounts_data_manager.checkPassword(playerName, password)
        return re

    def _checkOldCookie(
        self, playerIndex: playerWebSystemID, oldCookie: uuid.UUID
    ) -> PLAYER_LEVEL:
        p = self.players.get(playerIndex)
        if p == None:
            return PLAYER_LEVEL.illegal
        else:
            level = p.level if p.cookie == oldCookie else PLAYER_LEVEL.illegal
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
            ] == None:
                return i
        raise ServerBusyError("Sorry")

    # arg:   systemID should in [0,MAX)
    # arg:   status should be in_room_playing
    # raise: assertion error

    def _change_player_to_zombie(self, systemID: playerWebSystemID):

        assert self.players.get_type(systemID) == PLAYER_STATUS.IN_ROOM_PLAYING

        self.players.get(systemID).status = (  # type:ignore
            PLAYER_STATUS.IN_ROOM_ZOMBIE
        )
        room: WebRoom = self.rooms[self.players[systemID].room]  # type:ignore
        room.room_queue.put_nowait(
            MESSAGE(
                roomID=room.room_id,
                playerID=playerWebSystemID(-1),
                dataType=WEB_SYSTEM_DATATYPE.HE_IS_A_ZOMBIE,
                roomData=None,
                webData=systemID,
            )
        )

    def _check_game_vesion(self, game: FROZEN_GAME_TYPE) -> bool:
        return game.name in [game.name for game in self.games]

    def end_sql(self):
        self.accounts_data_manager.end()
