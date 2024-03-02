from typing import Tuple
import mysql.connector
import re
from defineError import AuthError
from myLogger import logger
from defineRegicideMessage import playerWebSystemID,PLAYER_LEVEL
import configparser
config = configparser.ConfigParser()
config.read('private/config')

host     =      config["database"]["host"]
sqlport=        config["database"]["port"]
sqlUser  =      config["database"]["user"]          
sqlPassword =   config["database"]["password"]          
database =      config["database"]["database"]          

class sqlSystem:
    def __init__(self) -> None:
        self.connection = mysql.connector.connect(
                            host=host,
                            port=sqlport,
                            user=sqlUser,
                            password=sqlPassword,
                            database=database)
    #raise error
    def checkPassword(self, userName:str, password:str) -> Tuple[playerWebSystemID, PLAYER_LEVEL]:
        cursor = self.connection.cursor()
        cursor.execute('SELECT id, authority FROM accounts WHERE username=%s AND password=%s', 
                   (userName,password))
        rows = cursor.fetchall()
        if len(rows) == 1:
            s:str = str(rows[0][1]) # type: ignore
            level:PLAYER_LEVEL = PLAYER_LEVEL.normal if s == "user" else\
                                 PLAYER_LEVEL.superUser if s == "super user" else\
                                 PLAYER_LEVEL.illegal
            return (rows[0][0], level)   # type: ignore
        else:
            logger.info(f"错误的密码?\n{rows}")
            raise AuthError("密码乱输?")
        cursor.close()
    def adminRegister(self,userName:str, password:str):
        cursor = self.connection.cursor()
        sql = "INSERT INTO accounts (username, password) VALUES (%s, %s);"
        cursor.execute(sql, (userName, password))
        self.connection.commit()
        cursor.close()
    def adminDelete(self,userName:str):
        cursor = self.connection.cursor()
        sql = "DELETE FROM accounts WHERE username=%s;"
        cursor.execute(sql, (userName,))
        self.connection.commit()
        cursor.close()
    #check inside, error inside
    def userRegister(self,userName:str, password:str):
        pattern = r'^[a-zA-Z0-9_]{6,16}$'
        if re.match(pattern, userName) and re.match(pattern, password):
            cursor = self.connection.cursor()
            cursor.execute('SELECT id FROM accounts WHERE username=%s', 
                   (userName,))
            result = cursor.fetchall()
            if len(result) != 0:
                cursor.close()
                raise AuthError("有号就登,别注册了搁着儿")
            else:
                cursor.execute( "INSERT INTO accounts (username, password) VALUES (%s, %s);",(userName, password))
                self.connection.commit()
                cursor.close()
                return
        else:
            logger.error(f"{userName},{password}正则炸了")
            raise AuthError("不是什么东西都可以作用户名和密码哦")
    def end(self):
        self.connection.close()
        





if __name__ == "__main__":
    s = sqlSystem()
    #s.adminRegister("darkpaper","114514")
    ree,l = s.checkPassword("darkpaper","114514")
    print(ree,l)
    s.end()