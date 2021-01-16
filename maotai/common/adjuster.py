import json
import time
from datetime import datetime

import requests

from maotai.common.config import env_params
from maotai.logger.logutil import logger


class Adjuster(object):
    def __init__(self, sleep_interval=0.5):
        # buy_time format 09:59:59.500
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
        Get JD's server timestamp
        :return:
        """
        url = env_params.get('JD_TIME_API')
        try:
            res = requests.get(url, timeout=1)
            resp = json.load(res.text)
            return int(resp['serverTime'] + res.elapsed.microseconds / 2)
        except Exception as e:
            logger.error(f"""Failed to retrieve JD's server timestamp. Error - {str(e)}.""")
            raise

    @staticmethod
    def local_time():
        """
        Get local timestamp
        :return:
        """
        return int(round(time.time() * 1000))

    def local_jd_time_diff(self):
        """
        Calculate the time difference between ' local - jd '
        :return:
        """
        return self.local_time() - self.jd_time()

    def start(self):
        logger.info(f"""Waiting for time: {self.buy_time}, detected time diff - {self.local_jd_time_diff()} ms""")
        while True:
            if self.local_time() - self.local_jd_time_diff() >= self.buy_time_ms:
                logger.info('Time of arrival, start execute...')
                break
            else:
                time.sleep(self.sleep_interval)
