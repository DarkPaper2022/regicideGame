from defineMessage import STATUS,FROZEN_BOSS
from typing import Tuple
from defineColor import COLOR
from defineRound import ROUND
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
        return colorStr+numStr+f"({color.name+numStr})"
def bossToStr(boss:FROZEN_BOSS) -> str:
        return f"""
Boss:
    name:{cardToStr(boss.name)}
    atk:{boss.atk}
    hp:{boss.hp}
    免疫:{boss.color}
"""
