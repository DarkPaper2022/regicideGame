```python
class WEB{
    def playerGetMessage(self, playerIndex, cookie:uuid.UUID)-> MESSAGE:
        pass
    def playerSendMessage(self, message:MESSAGE, cookie:uuid.UUID):
        pass
    def register(self, playerName, password) -> (playerIndex:int, cookie:uuid.UUID):    
        #WARNING: if player use TCP, thier password is VERY easy to leak, keep it in mind
        #passwords are saved locally, please call the administer to add your own user
        pass
}
```

```python
from dataclasses import dataclass
from typing import Any
from enum import Enum
class DATATYPE(Enum):
    askStatus = 1
    askTalking = 2
    answerStatus = 3
    answerTalking = 4
    card = 5
@dataclass
class MESSAGE:
    player: int
    dataType: DATATYPE
    """
    ask**时，data 会被忽略
    card时，data 应为 List[int]
    answerStatus data为一个结构体status，前端自行决定要不要diff，如果diff过于困难则可等待版本更新，会加一个Type
    answerTalking data为一个列表，表中含有一些聊天信息
    暂时不支持撤回，请等待版本更新
    """
    data: Any
```

你应该提供这样一个client的class
- 它引用web对象,并调用它的这三种方法来交互，它们都是线程安全的
- 它应当与game也与其它player位于不同的线程中
- 调用方法是在main.py中:
    - 启动game线程
    - 启动你的class的线程，并在合适的地方等待web的回应
    - （还可以再启动网络线程来等待其它用户）

编写client时有用的tip:
- 如果报错让你的用户感到迷惑，请尽管ask state
    - 断线重连的时候可以ask
    - 如果你的用户狂暴输入，那么他的一些输入不会得到响应，另一些会得到同样狂暴的报错信息，这时一个ask state是很有必要的
- 短线重连时，同样的username和password理应在register的时候拿到相同的cookie，但这暂时不受支持，所以请找个地方存存你的cookie


