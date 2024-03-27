import os
from setuptools import setup, find_packages

def get_version():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join (current_dir,"VERSION"),"r") as f:
        version = f.read().strip()
    return version

setup(
    name="regicide",
    version=get_version(),
    packages=find_packages(),
    author="DarkPaper",
    author_email="darkpaper2024@gmail.com",
    description="a game, can play using either netcat or a frontend using json",
    long_description="No long description now",
    url="https://github.com/DarkPaper2022/regicideGame",
    install_requires=["websockets==10.4", "mysql-connector-python==8.0.31"],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
)
