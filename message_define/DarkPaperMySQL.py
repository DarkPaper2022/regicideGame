from typing import Tuple,List
import mysql.connector
import re
from defineError import AuthDenial,PasswordWrongDenial,UserNameNotFoundDenial
from myLogger import logger
from defineWebSystemMessage import playerWebSystemID,PLAYER_LEVEL
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
        cursor.execute('SELECT id, authority, password FROM accounts WHERE username=%s', 
                   (userName,))
        rows:List[Tuple[int,str,str]] = cursor.fetchall() # type: ignore
        logger.debug(f"""{rows}""")
        if len(rows) == 1:  
            p:str = str(rows[0][2]) 
            s:str = str(rows[0][1]) 
            if p != password:
                raise PasswordWrongDenial
            level:PLAYER_LEVEL = PLAYER_LEVEL.normal if s == "user" else\
                                 PLAYER_LEVEL.superUser if s == "super user" else\
                                 PLAYER_LEVEL.illegal
            return (playerWebSystemID(rows[0][0]), level)
        elif len(rows) == 0:
            raise UserNameNotFoundDenial
        else:
            logger.error(f"""select {userName, password}
recieve:{rows}""")
            raise AuthDenial("Wow")
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
            result:List[int] = cursor.fetchall()  #type:ignore
            if len(result) != 0:
                cursor.close()
                raise AuthDenial("有号就登,别注册了搁着儿")
            else:
                cursor.execute( "INSERT INTO accounts (username, password) VALUES (%s, %s);",(userName, password))
                self.connection.commit()
                cursor.close()
                return
        else:
            logger.error(f"{userName},{password}正则炸了")
            raise AuthDenial("不是什么东西都可以作用户名和密码哦")
    def end(self):
        self.connection.close()
        





if __name__ == "__main__":
    s = sqlSystem()
    s.adminRegister("a","a")
    #ree,l = s.checkPassword("darkpaper","114514")
    s.end()