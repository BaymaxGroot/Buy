import json
import time
from datetime import datetime

import requests

from maotai.common.config import env_params
from maotai.logger.logutil import logger


class Adjuster(object):
    def __init__(self, sleep_interval=0.5):
        # 抢购时间 09:59:59.500
        buy_time_everyday = env_params.get('BUY_TIME').__str__()
        localtime = time.localtime(time.time())
        self.buy_time = datetime.strptime(
            f"""{localtime.tm_year.__str__()}-{localtime.tm_mon.__str__()}-{localtime.tm_mday.__str__()} {buy_time_everyday}""",
            "%Y-%m-%d %H:%M:%S.%f")
        self.buy_time_ms = int(time.mktime(self.buy_time.timetuple()) * 1000.0 + self.buy_time.microsecond / 1000)
        self.sleep_interval = sleep_interval
        self.diff_time = self.local_jd_time_diff()

    @staticmethod
    def jd_time():
        """
        得到京东服务器的时间戳
        :return:
        """
        url = env_params.get('JD_TIME_API')
        try:
            res = requests.get(url, timeout=1)
            resp = json.load(res.text)
            return int(resp['serverTime'] + res.elapsed.microseconds / 2)
        except Exception as e:
            logger.error(f"""获取京东服务器时间戳失败. Error - {str(e)}.""")
            raise

    @staticmethod
    def local_time():
        """
        得到本地时间戳
        :return:
        """
        return int(round(time.time() * 1000))

    def local_jd_time_diff(self):
        """
        计算本地时间戳 与 京东服务器时间戳之间的差值 即时延 ' local - jd '
        :return:
        """
        return self.local_time() - self.jd_time()

    def start(self):
        logger.info(f"""等待到达抢购时间: {self.buy_time}, 检测到本地与京东服务器时间差为 - {self.local_jd_time_diff()} ms""")
        while True:
            if self.local_time() - self.local_jd_time_diff() >= self.buy_time_ms:
                logger.info('抢购时间到达, 开始执行...')
                break
            else:
                time.sleep(self.sleep_interval)
