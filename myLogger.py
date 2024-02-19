import logging
logging.basicConfig(level=logging.INFO,  # 设置日志级别为 INFO
                    format='%(asctime)s - %(levelname)s - %(message)s',  # 设置日志格式
                    filename='example.log',  # 指定日志文件名
                    filemode='a')  # 设置日志文件模式为追加模式
logger = logging.getLogger()