# type: ignore
from pwn import *   
from src.test.test_config import url as tu
import re

user_a = remote(*tu)


user_a.recv()
user_a.sendline(b"log in#a a")
user_a.recv()
user_a.sendline(b"create#2")

content_with_id = user_a.recv().decode()
print(content_with_id)
room_id = int(re.search(r"房间号为:(\d+)", content_with_id).group(1))
user_a.sendline(b"prepare#")

user_c = remote(*tu)

user_c.recv()
user_c.sendline(b"log in#admin admin")
user_c.recv()
user_c.sendline(f"load#{room_id} before_joker".encode())


print(f"room_id: {room_id}， 用这个来加入房间吧")
user_c.interactive()
user_a.close()
