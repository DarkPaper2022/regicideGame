#!/home/darkpaper/.conda/envs/regicide/bin/python
# type: ignore
from pwn import *   

from src.test.test_config import url as tu
user_c = remote(*tu)

user_c.recv()
user_c.sendline(b"log in#admin admin")


user_c.interactive()
