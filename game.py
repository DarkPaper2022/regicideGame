from collections import deque
from typing import List,Union,Deque,Tuple
from queue import Queue as LockQueue
from defineMessage import MESSAGE,DATATYPE,STATUS,FROZEN_BOSS,GAME_SETTINGS,TALKING_MESSAGE,FROZEN_PLAYER
from defineError import CardError
from defineColor import COLOR,cardToNum
from defineRound import ROUND
from myLogger import logger
from dataclasses import dataclass
import random
import asyncio
import math
from webSystem import WEB


class BOSS:
    color:Union[COLOR,None]
    def __init__(self,name):
        self.name = name
        self.atk = 10 + 5*((name % 13) - 10)
        self.hp = 2 * self.atk
        self.color = COLOR(math.floor(name / 13))
    def final(self):
        return FROZEN_BOSS(self.name,self.atk,self.hp,self.color)
    def hurt(self,cnt): 
        self.hp = self.hp - cnt
    def weak(self,cnt):
        self.atk = self.atk - cnt if self.atk >= cnt else 0

class PLAYER:
    cards:List[int]
    def __init__(self, num, userName:str):
        self.cards = []
        self.num = num
        self.userName = userName
    def deleteCards(self,cards:List[int]):
        for card in cards:
            self.cards.remove(card)

class TALKING:
    messages:Deque[TALKING_MESSAGE]
    def __init__(self) -> None:
        self.messages = deque(maxlen=100)
    def insert(self, message:TALKING_MESSAGE):
        if len(self.messages) == 0 or self.messages[0].time < message.time:
            self.messages.appendleft(message)
        else:
            #TODO: maybe a little sort ?
            self.messages.appendleft(message)
    def get(self) -> Tuple[TALKING_MESSAGE,...]:
        return tuple(self.messages)


class GAME:
    """
    card        = A B C D   (pop card here, ordered)
    discard     = E F G H   (not ordered)  
    num = func()
    color = COLOR(math.floor(card / 13))
    name = num + color * 13 - 1
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
    currentRound:ROUND
    discardBossHeap:Deque[int]
    currentBoss:BOSS
    playerList:List[PLAYER]
    discardHeap:Deque[int]
    atkHeap:Deque[int]
    web:WEB
    def __init__(self, maxPlayer, web):
        self.maxHandSize = 9 - maxPlayer
        self.playerTotalNum = maxPlayer
        self.talkings = TALKING()
        self.startFlag = False
        self.web = web

    def getCard_cardHeap(self, cnt):
        notEmptyPlayerIndex = self.currentPlayer.num
        notEmptyPlayer = [i for i in range(self.playerTotalNum)]
        #player     0 1 3
        #index      0 1 2
        while cnt != 0:
            if len(self.cardHeap) == 0:
                return
            elif len(self.playerList[notEmptyPlayer[notEmptyPlayerIndex]].cards) == self.maxHandSize:
                del notEmptyPlayer[notEmptyPlayerIndex]
                if len(notEmptyPlayer) == notEmptyPlayerIndex:
                    notEmptyPlayerIndex = 0
                if len(notEmptyPlayer) == 0:
                    return                    
            else:
                self.playerList[notEmptyPlayer[notEmptyPlayerIndex]].cards.append(
                    self.cardHeap.pop()
                )
                cnt -= 1
            notEmptyPlayerIndex += 1
            if notEmptyPlayerIndex == len(notEmptyPlayer):
                notEmptyPlayerIndex = 0
    def weaken(self, cnt):
        self.currentBoss.weak(cnt)
    def atkBoss(self,cnt):
        self.currentBoss.hurt(cnt)
    def update_cardHeap(self, cnt):
        if cnt >= len(self.discardHeap):
            random.shuffle(self.discardHeap)
            self.cardHeap = self.discardHeap + self.cardHeap
            self.discardHeap.clear()
        else:
            random.shuffle(self.discardHeap)
            discardHeapList = list(self.discardHeap)
            self.cardHeap = deque(discardHeapList[:cnt]) + self.cardHeap
            self.discardHeap = deque(discardHeapList[cnt+1:])

    #ret: change the state
    def jokerRound(self) -> None:
        self.currentBoss.color = None
        while True:
            playerIndex = self.ioGetJokerNum()
            if playerIndex == self.currentPlayer.num:
                self.ioSendException(self.currentPlayer.num, "不要joker给自己！")
                continue
            elif playerIndex >= self.playerTotalNum or playerIndex < 0:
                self.ioSendException(self.currentPlayer.num, "有人在乱搞")
            else:
                self.currentPlayer = self.playerList[playerIndex]
                self.currentRound = ROUND.atk
                return

    #ret: change the state
    def atkRound(self) -> None:
        while True:
            cards = self.ioGetCards()
            try:
                check = self._atkRoundCheckLegalCards(cards)
                if check:
                    break
                else:
                    self.ioSendException(self.currentPlayer.num, "你小子乱出牌？看规则书吧你！\n")
            except CardError as e:
                self.ioSendException(self.currentPlayer.num, str(e))
        self._atkRoundHandleLegalCards(cards)       #here change state
        return
    #ret change the state
    def _atkRoundHandleLegalCardsWithoutJoker(self, cards:List[int]) -> None:
        if len(cards) == 0:
            self.currentRound = ROUND.defend
            #self.simpleChangePlayer() 不用改哦
            return
        else:
            cardNum = sum(cardToNum(card) for card in cards)
            cardColors:List[COLOR] = list(set([COLOR(math.floor(card / 13)) for card in cards]))    #去重
            cardColors.sort(key=lambda x:-x.value)
            #红桃先于方片
        for cardColor in cardColors:
            if cardColor == self.currentBoss.color:
                continue
            if cardColor == COLOR.colorS:
                self.weaken(cardNum)
            elif cardColor == COLOR.colorD:
                self.getCard_cardHeap(cardNum)
            elif cardColor == COLOR.colorH:
                self.update_cardHeap(cardNum)
            elif cardColor == COLOR.colorC:
                self.atkBoss(cardNum)
            else:
                raise ValueError("Wrong card color")            
        self.atkBoss(cardNum)
        killed, gameover = self.bossKilledCheck()
        if gameover:
            #self.currentPlayer 不用改
            self.currentRound = ROUND.over
        elif killed:
            self.simpleChangePlayer()
            self.currentRound = ROUND.atk
            return
        else:
            #currentPlayer不变哦
            self.currentRound = ROUND.defend
            return
    #ret: change the state
    def _atkRoundHandleLegalCards(self, cards:List[int]) -> None:
        self.currentPlayer.deleteCards(cards)
        for card in cards:
            self.atkHeap.appendleft(card)
        if (len(cards) == 1 and (cards[0] == 53 or cards[0] == 52)):
            self.currentRound = ROUND.jokerTime
            #self.currentPlayer 不变哦 
            return
        else:
            self._atkRoundHandleLegalCardsWithoutJoker(cards) #here change state
            return 
    def _atkRoundCheckLegalCards(self,cards:List[int]) -> bool:
        if len(cards) > self.maxHandSize:
            return False
        elif len(cards) == 0:
            return True
        else:
            if len(set(cards)) != len(cards):
                return False 
        for card in cards:
            if card not in self.currentPlayer.cards:
                return False
        if (52 in cards or 53 in cards):
            return (len(cards) == 1)
        # here, card无重复, card 一定在手里, card一定没有joker
        elif len(cards) == 1:
            return True
        # here, card无重复, card 一定在手里, card一定没有joker, card 多于一个
        else:
            #仅一狗
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
                #3、4个A是允许的
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

    #ret: change the state
    def defendRound(self):
        if sum([cardToNum(card) for card in self.currentPlayer.cards]) < self.currentBoss.atk:
            self.fail()
            #self.currentPlayer 不用改
            self.currentRound = ROUND.over
            return
        while True:
            cards = self.ioGetCards()
            try:
                check = self._defendRoundCheckLegalCards(cards)
                if check:
                    break
                else:
                    self.ioSendException(self.currentPlayer.num, "你小子乱弃牌？看规则书吧你！\n")
            except CardError as e:
                self.ioSendException(self.currentPlayer.num, str(e))
        self.currentPlayer.deleteCards(cards)
        for card in cards:
            self.discardHeap.appendleft(card)
        self.ioSendGameTalk(self.currentPlayer.num, "您全防住了\n")
        self.simpleChangePlayer()
        self.currentRound = ROUND.atk
        return
    #不负责用户的切换，仅负责牌堆的更新
    def bossKilledCheck(self) -> Tuple[bool, bool]:
        currentBoss:BOSS = self.currentBoss
        if currentBoss.hp > 0:
            return (False,False)
        elif currentBoss.hp == 0:
            self.cardHeap.append(currentBoss.name)
            self.discardBossHeap.append(currentBoss.name)
        else:
            self.discardHeap.appendleft(currentBoss.name)
            self.discardBossHeap.append(currentBoss.name)
            self.discardHeap = self.atkHeap
        if len(self.bossHeap) == 0:
            self.congratulations()
            return (True,True)
        else:
            self.currentBoss = self.bossHeap.popleft()
            return (True,False)


    def _defendRoundCheckLegalCards(self,cards:List[int]) -> bool:
        for card in cards:
            if card not in self.currentPlayer.cards:
                return False
        if len(set(cards)) != len(cards):
                return False 
        return (sum([cardToNum(card) for card in cards]) >= self.currentBoss.atk)


    def run(self):
        settings = self.ioGetStartSignal()
        self.start(settings)
    def start(self,settings:GAME_SETTINGS):
        self.startGame(settings)
        bossKilled = False
        while True:
            if self.currentRound == ROUND.over:
                return
            elif self.currentRound == ROUND.atk:
                self.ioSendStatus(self.currentPlayer.num)
                self.atkRound()
            elif self.currentRound == ROUND.defend:
                self.ioSendStatus(self.currentPlayer.num)
                self.defendRound()
            elif self.currentRound == ROUND.jokerTime:
                for i in range(self.playerTotalNum):
                    self.ioSendStatus(i)
                self.jokerRound()
            else:
                raise ValueError("strange round")
    def startGame(self,settings:GAME_SETTINGS):
        #这里的game向web提供了4个位置,由web来决定哪个位置编号给哪个客户端，目前来看是按顺序给的
        self.playerList = []
        for player_num in range(self.playerTotalNum):
            self.playerList.append(PLAYER(player_num, settings.playerNames[player_num]))
        self.currentPlayer = self.playerList[0]


        self.bossHeap = deque()
        for num in [10,11,12]:
            for color in random.sample(list(COLOR), 4):
                self.bossHeap.append(BOSS(color.value*13+num))
        self.currentBoss = self.bossHeap.popleft()

        self.cardHeap = deque()
        for color in list(COLOR):
            for i in range(10):
                self.cardHeap.append(color.value*13 + i)
        self.cardHeap.append(53)
        self.cardHeap.append(52)
        random.shuffle(self.cardHeap)
        self.discardHeap = deque()
        self.atkHeap = deque()
        self.discardBossHeap = deque()
        self.getCard_cardHeap(self.playerTotalNum * self.maxHandSize)
        self.startFlag = True
        self.currentRound = ROUND.atk
        return

    
    def simpleChangePlayer(self) -> None:     
        self.currentPlayer = self.playerList[(self.currentPlayer.num + 1) % self.playerTotalNum]
        return

    def congratulations(self):
        self.ioSendOverSignal(True)
    def fail(self):
        self.ioSendOverSignal(False)





    def ioSendStatus(self, playerIndex:int):
        if self.startFlag:
            playersLocal = tuple([FROZEN_PLAYER(player.userName,len(player.cards),player.num)
                            for player in self.playerList if player.num != playerIndex])
            status = STATUS(
                        currentRound=self.currentRound,
                        currentPlayerIndex= self.currentPlayer.num,
                        totalPlayer = self.playerTotalNum,
                        yourLocation = playerIndex,
                        players = playersLocal,
                        yourCards=tuple(self.playerList[playerIndex].cards), 
                        currentBoss=self.currentBoss.final(),
                        cardHeapLength=len(self.cardHeap),
                        defeatedBosses=tuple(self.discardBossHeap),
                        discardHeapLength=len(self.discardHeap),
                        elsedata=0)
            state = (self.startFlag, status)
        else:
            state = (self.startFlag, None)
        retMessage:MESSAGE = MESSAGE(player=playerIndex, dataType=DATATYPE.answerStatus, data=state)
        self.mainSend(retMessage)
    def ioSendTalkings(self, playerIndex:int):
        talking = self.talkings.get()
        retMessage:MESSAGE = MESSAGE(player=playerIndex, dataType=DATATYPE.answerTalking, data=talking)
        self.mainSend(retMessage)
    def ioSendException(self, playerIndex:int, exceptStr:str):
        exceptMessage:MESSAGE = MESSAGE(player=playerIndex, dataType=DATATYPE.exception, data=exceptStr)
        self.mainSend(exceptMessage) 
    def ioSendGameTalk(self, playerIndex:int, gameTalkStr:str):
        talkMessage:MESSAGE = MESSAGE(player=playerIndex, dataType=DATATYPE.gameTalk, data=gameTalkStr)
        self.mainSend(talkMessage) 
    def ioSendOverSignal(self, isWin:bool):
        for i in range(self.playerTotalNum):
            overMessage:MESSAGE = MESSAGE(i, DATATYPE.overSignal, isWin)
            self.mainSend(overMessage)
        return
    #ret:保证一定返回合适类型的信息
    def dataTypeSeprator(self, expected:DATATYPE):
        while True:
            message = self.mainRead()
            if message.dataType == DATATYPE.askStatus:
                self.ioSendStatus(message.player)
                continue
            elif message.dataType == DATATYPE.askTalking:
                self.ioSendTalkings(message.player)
                continue
            elif message.dataType != expected:
                self.ioSendException(message.player, "我现在不要这种的信息啊岂可修")
                continue
            else:
                return message
    #ret:保证一定返回合适类型、由合适人发来的消息
    def mixSeperator(self, expected:List[Tuple[int,DATATYPE]]):
        while True:
            message = self.mainRead()
            if message.dataType == DATATYPE.askStatus:
                self.ioSendStatus(message.player)
                continue
            elif message.dataType == DATATYPE.askTalking:
                self.ioSendTalkings(message.player)
                continue
            elif (message.player, message.dataType) not in expected:
                self.ioSendException(message.player, "我现在不要这种的信息啊岂可修")
                continue
            else:
                return message       
    def ioGetStartSignal(self) -> GAME_SETTINGS:
        message = self.mixSeperator([(-1,DATATYPE.startSignal)])
        return message.data
    def ioGetCards(self) -> List[int]:
        while True:
            messgae = self.mixSeperator([(self.currentPlayer.num, DATATYPE.card)])
            try:
                return messgae.data
            except:
                self.ioSendException(messgae.player, "卡牌格式错误")
                continue
    def ioGetJokerNum(self) -> int:
        while True:
            l:List[Tuple[int,DATATYPE]] = [(i,DATATYPE.speak) for i in range(4)] 
            l = l + [(self.currentPlayer.num,DATATYPE.confirmJoker)]
            message = self.mixSeperator(l)
            if message.dataType == DATATYPE.speak:
                self.talkings.insert(message.data)
                for i in range(self.playerTotalNum):
                    self.ioSendTalkings(i)
            else:
                #TODO:bad logic
                return message.data
    

    def mainRead(self) -> MESSAGE:
        message:MESSAGE = self.web.gameGetMessage()
        logger.info("READ:" + message.dataType.name + str(message.data))
        return message
    def mainSend(self,message:MESSAGE):
        logger.info("SEND:" + message.dataType.name + str(message.data))
        self.web.gameSendMessage(message)