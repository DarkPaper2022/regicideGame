# regicideGame
## 使用说明
- 请直接运行main.py, 参加的人数可在内部修改
- 玩家直接tcp连接指定端口即可,具体输入输出格式可暂时参见[defineMessage.py](defineMessage.py) 和 [tcpServer.py](tcpServer.py)，之后的版本会更新详细的说明
## 开发说明
- 针对各种TODO,欢迎PR,
- 有其他问题也欢迎联系本人
## TODO List
- webSystem 中register部分的线程安全性保障,使用sql
- 黑桃的无效化
- cookie的重用、game的重开、更多人的大厅与房间机制
    - cookie的重用 也即短线重连：
        - 如果game和web始终保留着cookie的话，关键问题是让相同的账号拿到相同的cookie
        - 这是一个普通的异步加锁型问题，还好
    - 房间机制：
        - GameServer 也拥有一个线程、并且在逻辑上是主线程
        - GameServer 根据客户端发来的message来决定是否要启动game线程、未启动game时要作出什么反馈
        - Game这一方也要向Web注册转发通道
            - game可能不唯一，得考虑game的message经web的路由表来转发，得注意这个路由表必须是fianl的，不然也会有线程问题
        - TCPServer要向GameServer发送内容，这样用来通知某些客户端的退出，以免完全阻塞Game
            - 当然也可以使用限时机制来解决，但也挺阴间的，有时候直接阻塞掉甚至是更合适的选择？
        - web   在设计时，要限制其逻辑功能
            - web的转发功能是足够线程安全的，这是因为其**足够多的分散设计**和**queue的线程安全性** 
            - 现有的逻辑功能是发送开始信号，这个是线程不太安全的，需修正或论证
            - 目前还有需求的功能是清除cookie，也许可以获取锁来Stop the World来解决？注意锁的颗粒度
- 从tcp客户端直接注册账号密码
    - WARNING: **一定要注意安全性啊**
- 将websocket和API结合起来构造浏览器前端