#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   

user_c = remote("127.0.0.1", 7000)

user_c.recv()
user_c.sendline(b"log in#admin admin")


user_c.interactive()
