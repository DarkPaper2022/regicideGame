#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   

user_a = remote("127.0.0.1", 7000)


user_a.recv()
user_a.sendline(b"log in#a a")
user_a.recv()
user_a.sendline(b"create#2")
user_a.recv()
user_a.sendline(b"prepare#")

user_a.interactive()

        