#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   

from src.test.test_config import url as tu
user_a = remote(*tu)

user_a.recv()
user_a.sendline(b"log in#a a")
user_a.recv()
user_a.sendline(b"create#2")
user_a.recv()
user_a.sendline(b"prepare#")

user_a.interactive()

        