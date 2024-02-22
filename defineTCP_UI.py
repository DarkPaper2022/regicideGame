from defineMessage import FROZEN_STATUS_PARTLY,FROZEN_BOSS
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
#arg:strip outside
#ret:legal card
def bytesToCard(b:bytes) -> int:
    s = b.decode()
    if s[0] in [c.name for c in COLOR]:
        color = COLOR[s[0]].value
        sRest = s[1:]
        num =   1 if sRest == "A" else\
                11 if sRest == "J" else\
                12 if sRest == "Q" else\
                13 if sRest == "K" else\
                int(sRest) if ( int(sRest) >= 1 and int(sRest) <= 10) else\
                -1
        if num == -1:
            raise ValueError("输入处理出错")
        else:
            return color*13 + num - 1
    else:
        try:
            card = int(s)
            if card < 0 or card > 53:
                raise ValueError("输入处理出错")
            else:
                return card
        except:
            raise ValueError("输入处理出错")
        