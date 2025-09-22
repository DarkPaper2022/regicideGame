#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   
from src.test.test_config import url as tu
user_b = remote(*tu)

user_b.recv()
user_b.sendline(b"log in#b b")
user_b.recv()
user_b.sendline(b"join#15")
user_b.recv()
user_b.sendline(b"prepare#")

user_b.interactive()
