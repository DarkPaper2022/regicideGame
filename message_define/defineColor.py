from enum import Enum
class COLOR(Enum):
    #红桃先于方片,如果key=lambda x:-x.value
    C = 0
    D = 1
    H = 2
    S = 3
    def __str__(self) -> str:
        return  "梅花" if (self == COLOR.C) else\
                "黑桃" if (self == COLOR.S) else\
                "方片" if (self == COLOR.D) else\
                "红桃" if (self == COLOR.H) else\
                "无"
    
def cardToNum(card:int) -> int:
    #num is only about how big it is, it don't care J or 10
    if 0 <= card <= 51:
        preNum = (card % 13 + 1)
        if preNum in [11,12,13]:
            num =   10 if preNum == 11 else\
                    15 if preNum == 12 else\
                    20
            return num
        else:
            return preNum
    elif card in [52,53]:
        return 0
    else:
        raise ValueError(f"wrong card number: {card}")