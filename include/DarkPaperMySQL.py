from typing import Tuple,List
import mysql.connector
import re
from include.defineError import AuthDenial,DINAL_TYPE,RegisterDenial,AuthError
from include.myLogger import logger
from include.defineWebSystemMessage import playerWebSystemID,PLAYER_LEVEL
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
        try:
            cursor = self.connection.cursor()
        except:
            self.reconnect()
        cursor.execute('SELECT id, authority, password FROM accounts WHERE username=%s', 
                   (userName,))
        rows:List[Tuple[int,str,str]] = cursor.fetchall() # type: ignore
        logger.debug(f"""{rows}""")
        if len(rows) == 1:  
            p:str = str(rows[0][2]) 
            s:str = str(rows[0][1]) 
            if p != password:
                raise AuthDenial(DINAL_TYPE.LOGIN_PASSWORD_WRONG)
            level:PLAYER_LEVEL = PLAYER_LEVEL.normal if s == "user" else\
                                 PLAYER_LEVEL.superUser if s == "super user" else\
                                 PLAYER_LEVEL.illegal
            return (playerWebSystemID(rows[0][0]), level)
        elif len(rows) == 0:
            raise AuthDenial(DINAL_TYPE.LOGIN_USERNAME_NOT_FOUND)
        else:
            logger.error(f"""select {userName, password}
recieve:{rows}""")
            raise AuthError
        cursor.close()
    def adminRegister(self,userName:str, password:str):
        try:
            cursor = self.connection.cursor()
        except:
            self.reconnect()
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
            try:
                cursor = self.connection.cursor()
            except:
                self.reconnect()
            cursor.execute('SELECT id FROM accounts WHERE username=%s', 
                   (userName,))
            result:List[int] = cursor.fetchall()  #type:ignore
            if len(result) != 0:
                cursor.close()
                raise RegisterDenial(DINAL_TYPE.REGISTER_ALREADY_EXIST)
            else:
                cursor.execute( "INSERT INTO accounts (username, password) VALUES (%s, %s);",(userName, password))
                self.connection.commit()
                cursor.close()
                return
        else:
            logger.error(f"{userName},{password}正则炸了")
            raise RegisterDenial(DINAL_TYPE.REGISTER_FORMAT_WRONG)
    def end(self):
        logger.info("sql come to its end.")
        if self.connection.is_connected():
            self.connection.close()
    def reconnect(self):
        if self.connection.is_connected():
            self.connection.close()
            logger.error("MYSQL connection is open, but now restarting...")
        else:
            logger.error("MYSQL FAILED, restarting...")
        self.connection = mysql.connector.connect(
                            host=host,
                            port=sqlport,
                            user=sqlUser,
                            password=sqlPassword,
                            database=database)