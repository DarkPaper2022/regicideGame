from src.include.defineError import CardDenial
from src.include.defineRegicideMessage import (
    FROZEN_STATUS_PARTLY,
    FROZEN_BOSS,
    REGICIDE_DATATYPE,
)
from src.include.defineWebSystemMessage import WEB_SYSTEM_DATATYPE, DATATYPE
from typing import Optional, Tuple
from src.include.defineColor import COLOR
from src.include.defineRound import ROUND
from src.include.JSON_tools import str_to_card
import math


def cards_to_str_TCP(cards: Tuple[int, ...]) -> str:
    return ", ".join([card_to_str_TCP(card) for card in cards])


def card_to_str_TCP(card: int) -> str:
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
    name:{card_to_str_TCP(boss.name)}
    atk:{boss.atk}
    hp:{boss.hp}
    免疫:{boss.color}
"""


# arg:strip outside
# ret:legal card


translate_dict: dict[str, DATATYPE] = {
    "join": WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM,
    "create": WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM,
    "prepare": WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE,
    "quit": WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM,
    "log out": WEB_SYSTEM_DATATYPE.LOG_OUT,
    "room status": WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
    "load": WEB_SYSTEM_DATATYPE.LOAD_ROOM,
    "status": REGICIDE_DATATYPE.askStatus,
    "talk log": REGICIDE_DATATYPE.REGICIDE_ACTION_TALKING_MESSAGE,
    "card": REGICIDE_DATATYPE.card,
    "speak": REGICIDE_DATATYPE.SPEAK,
    "joker": REGICIDE_DATATYPE.confirmJoker,
}
