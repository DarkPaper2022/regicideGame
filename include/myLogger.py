import logging
from logging.handlers import TimedRotatingFileHandler

# 创建日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建 TimedRotatingFileHandler，并配置日志文件格式和日期格式
handler = TimedRotatingFileHandler(filename='logs/log', when='midnight', interval=1, backupCount=7)
handler.suffix = '%Y-%m-%d.log'
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 将处理器添加到日志记录器中
logger.addHandler(handler)

