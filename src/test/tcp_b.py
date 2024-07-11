#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   

user_b = remote("127.0.0.1", 7000)

user_b.recv()
user_b.sendline(b"log in#b b")
user_b.recv()
user_b.sendline(b"join#15")
user_b.recv()
user_b.sendline(b"prepare#")

user_b.interactive()
