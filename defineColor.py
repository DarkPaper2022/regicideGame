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