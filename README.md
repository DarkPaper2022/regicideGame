# regicideGame
## 使用说明
- 请直接运行main.py, 参加的人数可在内部修改
- 玩家直接tcp连接指定端口即可,具体输入输出格式可暂时参见[defineMessage.py](defineMessage.py) 和 [tcpServer.py](tcpServer.py)，之后的版本会更新详细的说明

## 用户说明
目前可以使用的指令如下:
- websystem
    - register#\<username> \<password>
    - login#\<username> \<password>
    - join#\<roomID>
    - create#\<expected max player>
    - prepare#
    - quit#
    - logout#
    - roomstatus#
- room
    - status#
    - talk#
    - card#\<card> <card> ...  
    - speak#\<words>
    - joker#\<location>

## 开发说明
- 针对各种TODO,欢迎PR,
- 有其他问题也欢迎联系本人

## json格式说明
- 客户端发送信息:
    ```json
        {
            "dataType":"create",
            "data":{
                "maxPlayer":3
                }
        }
    ```
    ```json
        {
            "dataType":"register",
            "data":{
                "userName":"darkpaper",
                "password":"114514"
            }
        }
    ```
    ```json
        {
            "dataType":"log in",
            "data":{
                "userName":"darkpaper",
                "password":"114514"
            }
        }
    ```
    ```json
        {
            "dataType":"join",
            "data":{
                "roomID":100
            }
        }
    ```
    ```json
        {
            "dataType":"prepare"
        }
    ```
    ```json
        {
            "dataType":"card",
            "data":{
                "cards":["D4", "C4"]
            }
        }
    ```
    ```json
        {
            "dataType":"card",
            "data":{
                "cards":[]
            }
        }
    ```
    ```json
        {
            "dataType":"joker",
            "data":{
                "jokerLocation":3
            }
        }
    ```
    ```json
        {
            "dataType":"speak",
            "data":{
                "words":"哦shit"
            }
        }
    ```
- 客户端接收信息:
    ```json
    {
        "roomID": -1,
        "playerID": 1,
        "dataType": "ANSWER_ROOM_STATUS",
        "roomData": null,
        "webData": {
            "playerName": "darkpaper",
            "playerRoom": {
                "roomID": 0,
                "playerIndexs": [
                    {
                        "userName": "darkpaper",
                        "ready": false
                    }
                ],
                "maxPlayer": 2,
                "status": "preparing"
            },
            "playerLevel": "normal"
        }
    }
    ```

## TODO List
- webSystem 中register部分的线程安全性保障,使用sql
- 连续跳过
- 小写字母支持
- 中文支持
- ui美化：
    - joker J1 J2
    - 聊天不实时更新
- cookie的重用、game的重开、更多人的大厅与房间机制
    - cookie的重用 也即短线重连：
        - tcpServer应清除僵尸链接
            - 目前可以清除断线重连的旧线程,原理是cookie + 5min 轮询
    - 房间机制：
        - web   在设计时，要限制其逻辑功能
            - web的转发功能是足够线程安全的，这是因为其**足够多的分散设计**和**queue的线程安全性**
            - 分流是线程安全的,因为大部分是局部变量,对象变量的查询有些微妙：
                - 想清楚了我再来补充 
                - 线程锁，启动！
    - 房间功能:
        - 暂时房间不能结束,大概可以设一个timeout？
- 从tcp客户端直接注册账号密码
    - WARNING: **一定要注意安全性啊**
- 将websocket和API结合起来构造浏览器前端