from typing import Tuple
import mysql.connector
from defineError import AuthError
import configparser
config = configparser.ConfigParser()
config.read('private/config')

host     = config["database"]["host"]          
user     = config["database"]["user"]          
password = config["database"]["password"]          
database = config["database"]["database"]          

class sqlSystem:
    def __init__(self) -> None:
        self.connection = mysql.connector.connect(
                            host=host,
                            user=user,
                            password=password,
                            database=database)
    def checkPassword(self, userName:str, password:str) -> int:
        cursor = self.connection.cursor()
        cursor.execute('SELECT id FROM accounts WHERE username=%s AND password=%s', 
                   (userName,password))
        rows = cursor.fetchall()
        if len(rows) == 1:
            return rows[0][0]   # type: ignore
        else:
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
    def end(self):
        self.connection.close()
        





if __name__ == "__main__":
    s = sqlSystem()
    #s.adminRegister("darkpaper","114514")
    re = s.checkPassword("darkpaper","114514")
    print(re)
    s.end()