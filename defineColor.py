from enum import Enum
class COLOR(Enum):
    colorC = 0
    colorD = 1
    colorH = 2
    colorS = 3
    def __str__(self) -> str:
        return  "梅花" if (self == COLOR.colorC) else\
                "黑桃" if (self == COLOR.colorS) else\
                "方片" if (self == COLOR.colorD) else\
                "红桃" if (self == COLOR.colorH) else\
                "无"
    
def cardToNum(card:int) -> int:
    #num is only about how big it is, it don't care J or 10
    if 0 <= card <= 51:
        preNum = (card % 13 + 1)
        if preNum in [10,11,12]:
            num =   10 if preNum == 10 else\
                    15 if preNum == 11 else\
                    20
            return num
        else:
            return preNum
    else:
        raise ValueError(f"card wrong {card}")