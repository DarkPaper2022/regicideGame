from include.defineRegicideMessage import FROZEN_STATUS_PARTLY, FROZEN_BOSS,REGICIDE_DATATYPE
from include.defineWebSystemMessage import WEB_SYSTEM_DATATYPE,DATATYPE
from typing import Optional, Tuple
from include.defineColor import COLOR
from include.defineRound import ROUND
import math


def cardsToStr(cards: Tuple[int, ...]) -> str:
    return ", ".join([cardToStr(card) for card in cards])


def cardToStr(card: int) -> str:
    if card == 52:
        return "小王" + f"({str(card)})"
    elif card == 53:
        return "大王" + f"({str(card)})"
    else:
        num = card % 13 + 1
        numStr = (
            "A"
            if (num == 1)
            else (
                "J"
                if (num == 11)
                else "Q" if (num == 12) else "K" if (num == 13) else str(num)
            )
        )
        color = COLOR(math.floor(card / 13))
        colorStr = str(color)
        return colorStr + numStr + f"({color.name+numStr})"


def bossToStr(boss: FROZEN_BOSS) -> str:
    return f"""
Boss:
    name:{cardToStr(boss.name)}
    atk:{boss.atk}
    hp:{boss.hp}
    免疫:{boss.color}
"""


# arg:strip outside
# ret:legal card
def strToCard(b: bytes) -> int:
    s = b.decode()
    if s[0] in [c.name for c in COLOR]:
        color = COLOR[s[0]].value
        sRest = s[1:]
        card_str_dict = {"A": 1, "J": 11, "Q": 12, "K": 13}
        num:Optional[int] = card_str_dict.get(sRest)
        if num == None:
            num = int(sRest) if 1 <= int(sRest) <= 10 else None
        
        if num == None:
            raise ValueError("输入处理出错")
        else:
            return color * 13 + num - 1
    else:
        try:
            card = int(s)
            if card < 0 or card > 53:
                raise ValueError("输入处理出错")
            else:
                return card
        except:
            raise ValueError("输入处理出错")
        
        
translate_dict:dict[str,DATATYPE] = {
    "join":WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM,
    "create":WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM,
    "prepare":WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE,
    "quit":WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM,
    "log out":WEB_SYSTEM_DATATYPE.LOG_OUT,
    "room status":WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
    
    "status":REGICIDE_DATATYPE.askStatus,
    "talk log":REGICIDE_DATATYPE.REGICIDE_ACTION_TALKING_MESSAGE,
    "card":REGICIDE_DATATYPE.card,
    "speak":REGICIDE_DATATYPE.speak,
    "joker":REGICIDE_DATATYPE.confirmJoker 
}

