from collections import deque
from typing import List,Union,Deque,Tuple
from queue import Queue as LockQueue
from defineMessage import MESSAGE,DATATYPE,STATUS,FROZEN_BOSS,GAME_SETTINGS,TALKING_MESSAGE
from defineError import CardError
from defineColor import COLOR
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
        if self.messages[0].time < message.time:
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
    num = card%13 + 1
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
    #TODO 聊天列表
    currentBoss:BOSS
    playerList:List[PLAYER]
    discardHeap:Deque[int]
    atkHeap:Deque[int]
    web:WEB
    def __init__(self, maxPlayer, web):
        self.maxHandSize = 9 - maxPlayer
        self.playerTotalNum = maxPlayer
        self.talkings = TALKING()
        self.talkableFlag = False
        self.overFlag = False
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

    def joker(self) -> int:
        return self.ioGetJokerNum()

    def atkRound(self) ->  Union[int, None]:
        while True:
            cards = self.ioGetCards()
            try:
                self._atkRoundCheckLegalCards(cards)
                break
            except CardError as e:
                self.ioSendException(self.currentPlayer.num, str(e))
        return self._atkRoundHandleLegalCards(cards)   
    def _atkRoundHandleLegalCardsWithoutJoker(self, cards:List[int]) -> None:
        cardColors = []
        if len(cards) == 0:
            return
        else:
            cardNum = sum((card % 13 + 1) for card in cards)
            cardColors = [COLOR(math.floor(card / 13)) for card in cards]
            #重复问题
            #顺序问题
        for cardColor in cardColors:
            if cardColor == self.currentBoss.color:
                continue
            if cardColor == COLOR.colorC:
                self.weaken(cardNum)
            elif cardColor == COLOR.colorD:
                self.getCard_cardHeap(cardNum)
            elif cardColor == COLOR.colorH:
                self.update_cardHeap(cardNum)
            elif cardColor == COLOR.colorS:
                self.atkBoss(cardNum)
            else:
                raise ValueError("Wrong card color")            
        self.atkBoss(cardNum)
        self.bossKilledCheck()
        return      
    def _atkRoundHandleLegalCards(self, cards:List[int]) -> Union[int, None]:
        #return None or PlayerIndex
        self.currentPlayer.deleteCards(cards)
        for card in cards:
            self.atkHeap.appendleft(card)
        if (len(cards) == 1 and (cards[0] == 53 or cards[0] == 52)):
            return self.joker()
        else:
            self._atkRoundHandleLegalCardsWithoutJoker(cards)
            return None
    def _atkRoundCheckLegalCards(self,cards:List[int]) -> bool:
        #TODO
        return True

    def defendRound(self):
        cards = self.ioGetCards()
        #TODO:失败逻辑混乱
        if sum(self.currentPlayer.cards) < self.currentBoss.atk:
            self.fail()
        elif self._defendRoundCheckLegalCards(cards):
            self.currentPlayer.deleteCards(cards)
        else:
            raise ValueError("Wrong card selection")
    def bossKilledCheck(self):
        currentBoss:BOSS = self.currentBoss
        if currentBoss.hp > 0:
            return
        elif currentBoss.hp == 0:
            self.cardHeap.append(currentBoss.name)
        else:
            self.discardHeap.appendleft(currentBoss.name)
            self.discardHeap = self.atkHeap
        if len(self.bossHeap) == 0:
            self.congratulations()
        else:
            self.currentBoss = self.bossHeap.popleft()
        return


    def _defendRoundCheckLegalCards(self,cards:List[int]) -> bool:
        #TODO
        return True


    def run(self):
        settings = self.ioGetStartSignal()
        self.start(settings)

    def start(self,settings:GAME_SETTINGS):
        self.startGame(settings)
        while True:
            self.ioSendStatus(self.currentPlayer.num)
            nextPlayer = self.atkRound()
            if self.overFlag:
                return
            if nextPlayer == None:
                self.ioSendStatus(self.currentPlayer.num)
                self.defendRound()
                if self.overFlag:
                    return
                self.changePlayer((self.currentPlayer.num + 1) % self.playerTotalNum)
            else:
                self.changePlayer(nextPlayer)          
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
        self.getCard_cardHeap(self.playerTotalNum * self.maxHandSize)
        self.startFlag = True
        return         

    def changePlayer(self,playerIndex:int) -> None:
        self.currentPlayer = self.playerList[playerIndex]
        return

    def congratulations(self):
        print("YOU ARE SO NB, BOYS!")
        self.overFlag = True
    def fail(self):
        print("LET'S TRY IT AGAIN, BOYS")
        self.overFlag = True





    def ioSendStatus(self, playerIndex:int):
        if self.startFlag:
            state = (self.startFlag,
                     STATUS(
                        yourCards=tuple(self.playerList[playerIndex].cards), 
                        currentBoss=self.currentBoss.final(),
                        elsedata=1))
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
    def datatypeSeprator(self, expected:DATATYPE):
        #ret：此函数保证一定可以返回合适类型的信息
        #TODO:是否要支持针对playerIndex的复杂筛选
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
        message = self.datatypeSeprator(DATATYPE.startSignal)
        return message.data
    def ioGetCards(self) -> List[int]:
        while True:
            messgae = self.datatypeSeprator(DATATYPE.card)
            try:
                return messgae.data
            except:
                self.ioSendException(messgae.player, "卡牌格式错误")
                continue
    def ioGetJokerNum(self) -> int:
        while True:
            l:List[Tuple[int,DATATYPE]] = [(i,DATATYPE.speak) for i in range(4)] 
            l = l + [(-1,DATATYPE.startSignal)]
            message = self.mixSeperator(l)
            if message.dataType == DATATYPE.speak:
                self.talkings.insert(message.data)
            else:
                if message.player != self.currentPlayer.num:
                    self.ioSendException(message.player, "这事儿您可说了不算")
                return message.data
    

    def mainRead(self) -> MESSAGE:
        message:MESSAGE = self.web.gameGetMessage()
        logger.info("READ:" + message.dataType.name + str(message.data))
        return message
    def mainSend(self,message:MESSAGE):
        logger.info("SEND:" + message.dataType.name + str(message.data))
        self.web.gameSendMessage(message)