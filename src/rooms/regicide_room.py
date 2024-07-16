from collections import deque
import os
from typing import Any, Callable, Dict, List, Optional, Union, Deque, Tuple
from queue import Queue as LockQueue
import pickle
import uuid
from include.defineRegicideMessage import (
    FROZEN_STATUS,
    REGICIDE_DATATYPE,
    FROZEN_STATUS_PARTLY,
    FROZEN_BOSS,
    TALKING_MESSAGE,
    FrozenPlayerInRoom_partly,
    FrozenPlayerInRoom_archieve,
    playerRoomLocation,
)

from include.defineWebSystemMessage import (
    MESSAGE,
    playerWebSystemID,
    WEB_SYSTEM_DATATYPE,
    DATATYPE,
)

from include.defineError import CardError
from include.defineColor import COLOR, cardToNum
from include.defineRound import ROUND
from include.myLogger import logger
from dataclasses import dataclass
import random
import asyncio
import math
import sys
from src.rooms.regicide_talking import TALKING
from src.web_system import WEB


class BOSS:
    color: Union[COLOR, None]
    name: int

    def __init__(self, name: int):
        self.name = name
        self.atk = 10 + 5 * ((name % 13) - 10)
        self.hp = 2 * self.atk
        self.color = COLOR(math.floor(name / 13))
        self.temp_weaken_atk = 0  # 暂时存在而未生效的虚弱buff总数

    def unfroze(self, frozen: FROZEN_BOSS):
        self.name = frozen.name
        self.atk = frozen.atk
        self.hp = frozen.hp
        self.color = frozen.color
        self.temp_weaken_atk = frozen.temp_weaken_atk

    def frozen(self):
        return FROZEN_BOSS(
            self.name, self.atk, self.hp, self.color, self.temp_weaken_atk
        )

    def hurt(self, cnt):
        self.hp = self.hp - cnt

    def weak(self, cnt):
        self.atk = self.atk - cnt if self.atk >= cnt else 0

    def sameColorHandler(self, cnt):
        if self.color == COLOR.S:
            self.temp_weaken_atk += cnt
        return

    def clearify(self):
        self.color = None
        self.weak(self.temp_weaken_atk)
        self.temp_weaken_atk = 0
        return


class PLAYER:
    cards: List[int]
    location: playerRoomLocation
    webSystemID: playerWebSystemID
    userName: str

    def __init__(self, location, userName: str, webSystemID):
        self.cards = []
        self.location = location
        self.userName = userName
        self.webSystemID = webSystemID

    def deleteCards(self, cards: List[int]):
        for card in cards:
            self.cards.remove(card)

    def newGame(self):
        self.cards = []


class ROOM:
    """
    card        = A B C D   (pop card here, ordered)
    discard     = E F G H   (not ordered)
    num = func()
    color = COLOR(math.floor(card / 13))
    name = num + color * 13 - 1
    location    既代表数组中索引，又表明轮次关系
    webSystemID
    """

    """
    在某些时刻，game可以响应一个请求，在其它时刻则不行
    game应当维持一定频率的允许请求响应
    game在运行逻辑时不能响应请求，只有IO时允许响应请求
    out部分:会调用web，接着直接调用socket的输出,直接把包立刻发出去,中间不会有迟滞的情况,所以也不允许响应请求
            即使有迟滞也由web部分进行缓存，

    请求如何进入game呢,在in部分,
        可以接收应当作出选择的人的card型字符串,
        可以接受任何人的查询字符串，这是在任何的in都允许的,可以把逻辑放在这里面


    web这一class仅提供了一个用户管理系统，仅负责维护用户管道到game管道、game管道到用户管道的路由
    注意到此时需要game来指定目标用户，像ip一样

    递归逻辑可以依次是：仅传输信息的io通道函数，区分来源性质的seprate函数，从区分后的直接生成cards操作结构体的最终io函数    
    game可以仅维护一个管道，由game内部进行处理seperate处理，也可以分开来，
        形成 聊天线程（输入聊天内容，即时输出）、卡牌主线程（输入game打牌内容、即时输出状态内容）、状态线程（向game输入请求，向外输出状态）的模型
        其中卡牌管道是主要线程中的，状态管道和聊天管道接受主要线程的信息来决定是否允许输入输出
            各线程通信均是由lock控制的
        卡牌线程、聊天线程对用户的请求是隐式提供的，即包含在输出的状态内容中的，client收到以后自行显示

        此时,用户发来(以函数参数的形式)同一的结构体格式(管道, 请求类型（str）,具体数据)
    """

    playerTotalNum: int

    currentRound: ROUND

    defeated_boss_heap: Deque[int]
    currentBoss: BOSS
    boss_heap: Deque[BOSS]

    current_player: PLAYER
    playerList: List[PLAYER]

    discard_heap: Deque[int]
    atk_heap: Deque[int]
    card_heap: Deque[int]

    talkings: TALKING

    web: WEB

    status_to_load: Optional[FROZEN_STATUS]

    def __init__(self, web: WEB, roomIndex: int):
        self.startFlag = False
        self.zombieFlag = False
        self.web = web
        self.roomIndex = roomIndex
        self.playerTotalNum = self.web._room_ID_to_Max_player(roomIndex)
        self.talkings = TALKING()
        self.currentRound = ROUND.preparing
        self.status_to_load = None

    def froze(self) -> FROZEN_STATUS:
        players_arch = tuple(
            [
                FrozenPlayerInRoom_archieve(pl.cards, pl.location)
                for pl in self.playerList
            ]
        )
        talking_arch = tuple(self.talkings.messages)
        return FROZEN_STATUS(
            totalPlayer=self.playerTotalNum,
            currentRound=self.currentRound,
            players=players_arch,
            currentPlayerLocation=self.current_player.location,
            card_heap=tuple(self.card_heap),
            disCardHeap=tuple(self.discard_heap),
            atkCardHeap=tuple(self.atk_heap),
            defeatedBosses=tuple(self.defeated_boss_heap),
            currentBoss=self.currentBoss.frozen(),
            boss_heap=tuple([boss.name for boss in self.boss_heap]),
            talking=talking_arch,
        )

    def deal_load(self, status: FROZEN_STATUS):
        logger.info(f"pre loading status")
        self.status_to_load = status
        return

    def load(self, status: FROZEN_STATUS):
        if status.totalPlayer != self.playerTotalNum:
            logger.warning("load failed for the room size don't fit")
            return
        self.talkings.messages = deque(status.talking)
        self.boss_heap = deque([BOSS(name) for name in status.boss_heap])
        self.currentBoss.unfroze(status.currentBoss)
        self.defeated_boss_heap = deque(status.defeatedBosses)
        self.atk_heap = deque(status.atkCardHeap)
        self.discard_heap = deque(status.disCardHeap)
        self.card_heap = deque(status.card_heap)

        for fpl in status.players:
            self.playerList[fpl.location].cards = fpl.cards

        self.current_player = self.playerList[status.currentPlayerLocation]

    def getCard_cardHeap(self, cnt):
        notEmptyPlayerIndex = self.current_player.location
        notEmptyPlayer = [i for i in range(self.playerTotalNum)]
        # player[index]     0 1 3
        # index             0 1 2
        while cnt != 0:
            if len(self.card_heap) == 0:
                return
            elif (
                len(self.playerList[notEmptyPlayer[notEmptyPlayerIndex]].cards)
                == self.maxHandSize
            ):
                del notEmptyPlayer[notEmptyPlayerIndex]
                if len(notEmptyPlayer) == notEmptyPlayerIndex:
                    notEmptyPlayerIndex = playerRoomLocation(0)  # overflow
                if len(notEmptyPlayer) == 0:
                    return
            else:
                self.playerList[notEmptyPlayer[notEmptyPlayerIndex]].cards.append(
                    self.card_heap.pop()
                )
                cnt -= 1
            notEmptyPlayerIndex = playerRoomLocation(notEmptyPlayerIndex + 1)
            if notEmptyPlayerIndex == len(notEmptyPlayer):
                notEmptyPlayerIndex = playerRoomLocation(0)

    def weaken(self, cnt):
        self.currentBoss.weak(cnt)

    def atkBoss(self, cnt):
        self.currentBoss.hurt(cnt)

    def update_cardHeap(self, cnt):
        if cnt >= len(self.discard_heap):
            random.shuffle(self.discard_heap)
            self.card_heap = self.discard_heap + self.card_heap
            self.discard_heap.clear()
        else:
            random.shuffle(self.discard_heap)
            discardHeapList = list(self.discard_heap)
            self.card_heap = deque(discardHeapList[:cnt]) + self.card_heap
            self.discard_heap = deque(discardHeapList[cnt:])

    # ret: change the state
    async def jokerRound(self) -> None:
        while True:
            location = await self.ioGetJokerNum()
            if location == self.current_player.location:
                self.ioSendException(
                    self.current_player.webSystemID, "不要joker给自己！"
                )
                continue
            elif location >= self.playerTotalNum or location < 0:
                self.ioSendException(self.current_player.webSystemID, "有人在乱搞")
            else:
                self.current_player = self.playerList[location]
                self.currentRound = ROUND.atk
                return

    # ret: change the state
    async def atkRound(self) -> None:
        while True:
            cards = await self.ioGetCards()
            try:
                check = self._atkRoundCheckLegalCards(cards)
                if check:
                    break
                else:
                    self.ioSendException(
                        self.current_player.webSystemID,
                        "你小子乱出牌？看规则书吧你！\n",
                    )
            except CardError as e:
                self.ioSendException(self.current_player.webSystemID, str(e))
        self._atkRoundHandleLegalCards(cards)  # here change state
        return

    # ret change the state
    def _atkRoundHandleLegalCardsWithoutJoker(self, cards: List[int]) -> None:
        if len(cards) == 0:
            self.currentRound = ROUND.defend
            # self.simpleChangePlayer() 不用改哦
            return
        else:
            cardNum = sum(cardToNum(card) for card in cards)
            cardColors: List[COLOR] = list(
                set([COLOR(math.floor(card / 13)) for card in cards])
            )  # 去重
            cardColors.sort(key=lambda x: -x.value)
            # 红桃先于方片
        # here we get color and num
        for cardColor in cardColors:
            if cardColor == self.currentBoss.color:
                self.currentBoss.sameColorHandler(cardNum)
                continue
            if cardColor == COLOR.S:
                self.weaken(cardNum)
            elif cardColor == COLOR.D:
                self.getCard_cardHeap(cardNum)
            elif cardColor == COLOR.H:
                self.update_cardHeap(cardNum)
            elif cardColor == COLOR.C:
                self.atkBoss(cardNum)
            else:
                raise ValueError("Wrong card color")
        self.atkBoss(cardNum)
        killed, gameover = self._atkRoundBossKilledCheck()
        if gameover:
            # self.currentPlayer 不用改
            self.currentRound = ROUND.over
        elif killed:
            self.ioSendGameTalk(
                self.current_player.webSystemID, "您干死它了,该您的队友干活儿了\n"
            )
            self.simpleChangePlayer()
            self.currentRound = ROUND.atk
            return
        else:
            self.ioSendGameTalk(
                self.current_player.webSystemID, "您输出拉满！但是该防了现在\n"
            )
            # currentPlayer不变哦
            self.currentRound = ROUND.defend
            return

    # ret: change the state
    def _atkRoundHandleLegalCards(self, cards: List[int]) -> None:
        self.current_player.deleteCards(cards)
        for card in cards:
            self.atk_heap.appendleft(card)
        if len(cards) == 1 and (cards[0] == 53 or cards[0] == 52):
            self.currentBoss.clearify()
            self.currentRound = ROUND.jokerTime
            # self.currentPlayer 不变哦
            return
        else:
            self._atkRoundHandleLegalCardsWithoutJoker(cards)  # here change state
            return

    def _atkRoundCheckLegalCards(self, cards: List[int]) -> bool:
        if len(cards) > self.maxHandSize:
            return False
        elif len(cards) == 0:
            return True
        else:
            if len(set(cards)) != len(cards):
                return False
        for card in cards:
            if card not in self.current_player.cards:
                return False
        if 52 in cards or 53 in cards:
            return len(cards) == 1
        # here, card无重复, card 一定在手里, card一定没有joker
        elif len(cards) == 1:
            return True
        # here, card无重复, card 一定在手里, card一定没有joker, card 多于一个
        else:
            # 仅一狗
            cntA = 0
            cntElse = 0
            for card in cards:
                if cardToNum(card) != 1:
                    cntA += 1
                else:
                    cntElse += 1
            if cntA == 1 and cntElse == 1:
                return True
            else:
                # 3、4个A是允许的
                total = 0
                for card in cards:
                    if cardToNum(card) == cardToNum(cards[0]):
                        total += cardToNum(card)
                    else:
                        return False
                if total >= 10:
                    return False
                else:
                    return True

    # 不负责用户的切换，仅负责牌堆的更新
    def _atkRoundBossKilledCheck(self) -> Tuple[bool, bool]:
        currentBoss: BOSS = self.currentBoss
        if currentBoss.hp > 0:
            return (False, False)
        elif currentBoss.hp == 0:
            self.card_heap.append(currentBoss.name)
        else:
            self.discard_heap.appendleft(currentBoss.name)
        self.defeated_boss_heap.append(currentBoss.name)
        self.discard_heap += self.atk_heap
        self.atk_heap.clear()
        if len(self.boss_heap) == 0:
            self.congratulations()
            return (True, True)
        else:
            self.currentBoss = self.boss_heap.popleft()
            return (True, False)

    # ret: change the state
    async def defendRound(self):
        if (
            sum([cardToNum(card) for card in self.current_player.cards])
            < self.currentBoss.atk
        ):
            self.fail()
            # self.currentPlayer 不用改
            self.currentRound = ROUND.over
            return
        while True:
            cards = await self.ioGetCards()
            try:
                check = self._defendRoundCheckLegalCards(cards)
                if check:
                    break
                else:
                    self.ioSendException(
                        self.current_player.webSystemID,
                        "你小子乱弃牌？看规则书吧你！\n",
                    )
            except CardError as e:
                self.ioSendException(self.current_player.webSystemID, str(e))
        self.current_player.deleteCards(cards)
        for card in cards:
            self.discard_heap.appendleft(card)
        self.ioSendGameTalk(self.current_player.webSystemID, "您全防住了\n")
        self.simpleChangePlayer()
        self.currentRound = ROUND.atk
        return

    def _defendRoundCheckLegalCards(self, cards: List[int]) -> bool:
        for card in cards:
            if card not in self.current_player.cards:
                return False
        if len(set(cards)) != len(cards):
            return False
        return sum([cardToNum(card) for card in cards]) >= self.currentBoss.atk

    async def run(self):
        logger.debug("room thread start")
        self.playerList = []
        await self.ioGetPlayerRegister()
        logger.debug("room get player info, starting ...")
        while True:
            await self.start()

    async def start(self):
        self.init_game()
        cnt = 0
        save_id = uuid.uuid4()
        while True:
            cnt += 1
            pickle.dump(self.froze(), open(f"data/room/{save_id}_{cnt}.pkl", "wb"))

            if self.status_to_load is not None:
                self.load(self.status_to_load)
                logger.info("after load room")
                self.status_to_load = None

            if self.currentRound == ROUND.over:
                return
            elif self.currentRound == ROUND.atk:
                for i in range(self.playerTotalNum):
                    self.ioSendStatus(playerRoomLocation(i))
                await self.atkRound()
            elif self.currentRound == ROUND.defend:
                for i in range(self.playerTotalNum):
                    self.ioSendStatus(playerRoomLocation(i))
                await self.defendRound()
            elif self.currentRound == ROUND.jokerTime:
                for i in range(self.playerTotalNum):
                    self.ioSendStatus(playerRoomLocation(i))
                await self.jokerRound()
            else:
                raise ValueError("strange round")

    def init_game(self):
        # 这里的game向web提供了4个位置,由web来决定哪个位置编号给哪个客户端，目前来看是按顺序给的
        maxPlayer = self.playerTotalNum
        self.maxHandSize = 9 - maxPlayer
        self.playerTotalNum = maxPlayer

        self.talkings.clear()

        self.current_player = self.playerList[0]
        for player in self.playerList:
            player.newGame()

        self.boss_heap = deque()
        for num in [10, 11, 12]:
            for color in random.sample(list(COLOR), 4):
                self.boss_heap.append(BOSS(color.value * 13 + num))
        self.currentBoss = self.boss_heap.popleft()

        self.card_heap = deque()
        for color in list(COLOR):
            for i in range(10):
                self.card_heap.append(color.value * 13 + i)
        self.card_heap.append(53)
        self.card_heap.append(52)
        random.shuffle(self.card_heap)
        self.discard_heap = deque()
        self.atk_heap = deque()
        self.defeated_boss_heap = deque()
        self.getCard_cardHeap(self.playerTotalNum * self.maxHandSize)
        self.startFlag = True
        self.currentRound = ROUND.atk
        return

    def simpleChangePlayer(self) -> None:
        self.current_player = self.playerList[
            (self.current_player.location + 1) % self.playerTotalNum
        ]
        return

    def congratulations(self):
        self.ioSendOverSignal(True)

    def fail(self):
        self.ioSendOverSignal(False)

    def _webSystemID_toPlayerLocation(
        self, webSystemID: playerWebSystemID
    ) -> Optional[playerRoomLocation]:
        for player in self.playerList:
            if player.webSystemID == webSystemID:
                return player.location
        return None

    def ioSendStatus(self, playerLocation: playerRoomLocation):
        if self.startFlag:
            playersLocal = tuple(
                [
                    FrozenPlayerInRoom_partly(
                        player.userName, len(player.cards), player.location
                    )
                    for player in self.playerList
                    if player.location != playerLocation
                ]
            )
            status = FROZEN_STATUS_PARTLY(
                discardHeap=tuple(self.discard_heap),
                atkCardHeap=tuple(self.atk_heap),
                currentRound=self.currentRound,
                currentPlayerLocation=self.current_player.location,
                totalPlayer=self.playerTotalNum,
                yourLocation=playerLocation,
                players=playersLocal,
                yourCards=tuple(self.playerList[playerLocation].cards),
                currentBoss=self.currentBoss.frozen(),
                cardHeapLength=len(self.card_heap),
                defeatedBosses=tuple(self.defeated_boss_heap),
                discardHeapLength=len(self.discard_heap),
            )
        else:
            l = self.playerList
            status = None
        retMessage: MESSAGE = MESSAGE(
            roomID=self.roomIndex,
            playerID=self.playerList[playerLocation].webSystemID,
            data_type=REGICIDE_DATATYPE.UPDATE_GAME_STATUS,
            roomData=status,
            webData=None,
        )
        self.mainSend(retMessage)

    def ioSendTalkings(self, webSystemID: playerWebSystemID):
        talking = self.talkings.get()
        retMessage: MESSAGE = MESSAGE(
            self.roomIndex,
            playerID=webSystemID,
            data_type=REGICIDE_DATATYPE.ANSWER_TALKING,
            roomData=talking,
            webData=None,
        )
        self.mainSend(retMessage)

    def ioSendException(self, webSystemID: playerWebSystemID, exceptStr: str):
        exceptMessage: MESSAGE = MESSAGE(
            self.roomIndex,
            playerID=webSystemID,
            data_type=REGICIDE_DATATYPE.exception,
            roomData=exceptStr,
            webData=None,
        )
        self.mainSend(exceptMessage)

    def ioSendGameTalk(self, webSystemID: playerWebSystemID, gameTalkStr: str):
        talkMessage: MESSAGE = MESSAGE(
            self.roomIndex,
            playerID=webSystemID,
            data_type=REGICIDE_DATATYPE.gameTalk,
            roomData=gameTalkStr,
            webData=None,
        )
        self.mainSend(talkMessage)

    def ioSendOverSignal(self, isWin: bool):
        for player in self.playerList:
            overMessage: MESSAGE = MESSAGE(
                self.roomIndex,
                player.webSystemID,
                REGICIDE_DATATYPE.overSignal,
                isWin,
                None,
            )
            self.mainSend(overMessage)
        return

    # ret:保证一定返回合适类型的信息
    async def dataTypeSeprator(self, expected: DATATYPE):
        check_wanted: Callable[[MESSAGE], bool] = (
            lambda message: message.data_type == expected
        )
        return await self._Seperator(check_wanted)

    # ret: MESSAGE: 保证一定返回合适类型、由合适人发来的消息
    async def mixSeperator(self, expected: List[Tuple[playerRoomLocation, DATATYPE]]):
        check_wanted: Callable[[MESSAGE], bool] = (
            lambda message: (
                self._webSystemID_toPlayerLocation(message.playerID),
                message.data_type,
            )
            in expected
        )
        return await self._Seperator(check_wanted)

    async def _Seperator(self, check_wanted: Callable[[MESSAGE], bool]):
        while True:
            message = await self.mainRead()
            if message.data_type == REGICIDE_DATATYPE.askStatus:
                #TODO:admin ask
                location = self._webSystemID_toPlayerLocation(message.playerID)
                if location is None: 
                    raise Exception(f"systemID:{message.playerID} error when asking status, not found in {[p.webSystemID for p in self.playerList]}") 
                self.ioSendStatus(location)
            elif message.data_type == REGICIDE_DATATYPE.REGICIDE_ACTION_TALKING_MESSAGE:
                self.ioSendTalkings(message.playerID)
            elif message.data_type == WEB_SYSTEM_DATATYPE.dumpRoom:
                pickle.dump(self, open(f"data/room/{message.roomData}.pkl", "wb"))
            elif message.data_type == WEB_SYSTEM_DATATYPE.LOAD_ROOM:
                path = f"data/room/{message.roomData}"
                if not os.path.exists(path):
                    self.ioSendException(message.playerID, "没有这个存档")
                    continue
                with open(path, "rb") as f:
                    status: FROZEN_STATUS = pickle.load(f)
                self.deal_load(status)
            elif not check_wanted(message):
                self.ioSendException(message.playerID, "我现在不要这种的信息啊岂可修")
            else:
                return message

    # not math function
    async def ioGetPlayerRegister(self) -> None:
        message = await self.dataTypeSeprator(WEB_SYSTEM_DATATYPE.runRoom)
        for i, web_player in enumerate(message.webData):
            player = PLAYER(
                webSystemID=web_player[0], userName=web_player[1], location=i
            )
            self.playerList.append(player)
        return

    async def ioGetCards(self) -> List[int]:
        while True:
            messgae = await self.mixSeperator(
                [(self.current_player.location, REGICIDE_DATATYPE.card)]
            )
            try:
                return messgae.roomData
            except:
                self.ioSendException(messgae.playerID, "卡牌格式错误")
                continue

    async def ioGetJokerNum(self) -> playerRoomLocation:
        while True:
            l: List[Tuple[playerRoomLocation, DATATYPE]] = [
                (playerRoomLocation(i), REGICIDE_DATATYPE.SPEAK)
                for i in range(self.playerTotalNum)
            ]
            l = l + [(self.current_player.location, REGICIDE_DATATYPE.confirmJoker)]
            message = await self.mixSeperator(l)
            if message.data_type == REGICIDE_DATATYPE.SPEAK:
                self.talkings.insert(message.roomData)
                for i in range(self.playerTotalNum):
                    self.ioSendTalkings(self.playerList[i].webSystemID)
            else:
                # TODO:bad logic
                return message.roomData

    async def mainRead(self) -> MESSAGE:
        try:
            message: MESSAGE = await self.web.roomGetMessage(self.roomIndex)
        except Exception as e:
            self.mainSend(
                MESSAGE(
                    self.roomIndex,
                    playerID=playerWebSystemID(-1),
                    data_type=REGICIDE_DATATYPE.gameOver,
                    roomData=None,
                    webData=None,
                )
            )
            logger.debug(f"{e}")
            logger.info(f"ROOM {self.roomIndex} 正常关闭了")
            sys.exit()
        logger.debug(
            "room get a message:" + message.data_type.name + " " + str(message.roomData)
        )
        return message

    def mainSend(self, message: MESSAGE):
        logger.debug(
            "room send a message:"
            + message.data_type.name
            + " "
            + str(message.roomData)
        )
        self.web.roomSendMessage(message)
