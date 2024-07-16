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
    - loadroom#\<roomID> \<archieve name>
    - dumproom#\<roomID> \<archieve name>

- room
    - status#
    - talk#
    - card#\<card> <card> ...  
    - speak#\<words>
    - joker#\<location>

## 管理员说明
- 暂时只支持tcp连接，所以暂时使用共用管理员帐号吧，之后会出https客户端的
- 登录后可以普通地进行游戏，也可以使用管理员指令，管理员指令不局限于当前房间
- \<archieve name> 这一参数指定了文件的相对路径
- 之后会出对存档的编辑功能，现在只能手动打出来再存
- loadroom的指令会在当前游戏的下一轮次开始时生效，dumproom则会立即生效


## 开发说明
- 针对各种TODO,欢迎PR,
- 有其他问题也欢迎联系本人
- 在发送ASK_LOGIN包时,必须等待ANSWER_LOGIN

## API说明

1. update
    - 
2. ask
    - ask login
    - ask register
    - ask join room
3. answer
    - answer join room
        - success: true / false
    
4. action
    - leave room
    - create room
    - change prepare
    - log out


- 客户端发送信息:

    ```json
    {
        "dataType": "ASK",
        "dataName": "CONNECTION",
        "data": {
            "gameName": "regicide",
            "version": 0.1
        }
    }    
    ```
    ```json
    {
        "dataType": "ACTION",
        "dataName": "CREATE_ROOM",
        "data": {
            "maxPlayer": 4
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
        "dataType": "ASK",
        "dataName": "LOGIN",
        "data": {
            "username": "114514",
            "password": "114514"
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
        "dataType": "ACTION",
        "dataName": "CHANGE_PREPARE",
        "data": {}
    }
    ```
    ```json
    {
        "dataType": "ACTION",
        "dataName": "LEAVE_ROOM",
        "data": {}
    }
    ```
    ```json
        {
            "dataType":"card",
            "data":{
                "cards":[0, 32]
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
        "dataType": "ACTION",
        "dataName": "TALK_MESSAGE",
        "data": {
            "talkMessage": "test1"
        }
    }
    ```


    
- 客户端接收信息:
    ```json
    {
        "dataType": "UPDATE",
        "dataName": "ROOM_STATUS",
        "data": {
            "roomID": 201,
            "maxPlayer": 4,
            "playerList": [
                {
                    "playerName": "123456",
                    "playerPrepared": false
                }
            ]
        }
    }

    {
        "dataType": "UPDATE",
        "dataName": "ROOM_STATUS",
        "data": {
            "roomID": -1
        }
    }
    ```
    
    ```json
    {
        "roomID": -1,
        "playerID": 1,
        "dataType": "UPDATE_GAME_STATUS",
        "data": {
            "totalPlayer": 2,
            "yourLocation": 1,
            "currentRound": "defend",
            "currentPlayerLocation": 0,
            "yourCards": [8,29,46,9,0,20],
            "cardHeapLength": 19,
            "discardHeapLength": 15,
            "discardHeap": [10,1,42,32,5,39,16,48,36,43,14,45,27,7,13],
            "atkCardHeap": [],
            "defeatedBosses": [10,36,49],
            "currentBoss": {
                "name": 23,
                "atk": 10,
                "hp": 20,
                "color": "D",
                "tempWeakenAtk": 0
            },
            "players": [
                {
                    "playerName": "a",
                    "playerHandCardCnt": 5,
                    "playerLocation": 0
                }
            ]
        }
    }
    ```

    ```json
        {
            
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
- room 的建立：
    - HALL_CREATE_ROOM 
    - runRoom

- client与web的分割
    - client 管理链接