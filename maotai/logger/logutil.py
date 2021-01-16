import logging
import logging.handlers

LOG_FILE = "running.log"
logger = logging.getLogger()


def setup_logger():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(process)d - %(threadName)s - %(funcName)s'
                                  '%(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=4, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


setup_logger()
