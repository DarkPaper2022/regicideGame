from defineMessage import STATUS,FROZEN_BOSS
from typing import Tuple
from defineColor import COLOR
import math
def cardsToStr(cards:Tuple[int,...]) -> str:
    return ', '.join([cardToStr(card) for card in cards])
def cardToStr(card:int) -> str:
    if (card == 52):
        return "小王"+f"({str(card)})"
    elif (card == 53):
        return "大王"+f"({str(card)})"
    else:
        num = card % 13 + 1
        numStr =    'A' if (num == 1) else\
                    'J' if (num == 11) else\
                    'Q' if (num == 12) else\
                    'K' if (num == 13) else\
                    str(num)
        color = COLOR(math.floor(card / 13))
        colorStr = str(color)
        return colorStr+numStr+f"({str(card)})"
def bossToStr(boss:FROZEN_BOSS) -> str:
        return f"""Boss
    name:{cardToStr(boss.name)}
    atk:{boss.atk}
    hp:{boss.hp}
    免疫:{boss.color}
"""
def statusToStr(status:STATUS) -> str:
    cardHeapLengthStr:str = f"牌堆还剩{status.cardHeapLength}张牌\n"
    discardHeapLengthStr = f"弃牌堆有{status.discardHeapLength}张牌\n"
    defeatedBossesStr = f"您已经打败了{cardsToStr(status.defeatedBosses)},还有{12 - len(status.defeatedBosses)}个哦"
    playersStr:str = "您的队友:"
    for player in status.players:
        preDelta = player.playerLocation - status.yourLocation
        delta =  preDelta if preDelta >= 1 else preDelta + status.totalPlayer 
        #TODO:防御性编程
        playersStr += f"""
用户名:{player.playerName}
手牌数目:{player.playerHandCardCnt}/{9 - status.totalPlayer}
用户位置:{player.playerLocation}号位，你的{delta*"下"}家
"""
    yourCardsStr = f"""{"YourCards"}:
    {cardsToStr(status.yourCards)}
"""
    currentBossStr = bossToStr(status.currentBoss)
    re:str =  yourCardsStr + currentBossStr + playersStr
    return re
