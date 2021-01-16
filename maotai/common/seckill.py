import os
import time
import json
import random
import pickle
import functools

from lxml import etree
import requests
from timer import Timer
from concurrent.futures import ProcessPoolExecutor

from maotai.common.util import get_useragent, parse_json, wait_time
from maotai.common.config import env_params
from maotai.logger.logutil import logger
from maotai.common.exception import SKException

COOKIE_FOLDER = './cookies/'
QR_FILE = 'qr_code.png'


class SessionUtil(object):
    """
    Session util
    """

    def __init__(self):
        self.cookies_folder = COOKIE_FOLDER
        self.user_agent = get_useragent()
        self.session = self._init_session()

    def _init_session(self):
        session = requests.session()
        session.headers = self.get_headers()
        return session

    def get_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;"
                      "q=0.9,image/webp,image/apng,*/*;"
                      "q=0.8,application/signed-exchange;"
                      "v=b3",
            "Connection": "keep-alive"
        }

    def get_user_agent(self):
        return self.user_agent

    def get_session(self):
        """
        Retrieve current session
        :return:
        """
        return self.session

    def get_cookies(self):
        """
        Retrieve current cookie
        :return:
        """
        return self.get_session().cookies

    def set_cookies(self, cookies):
        self.session.cookies.update(cookies)

    def load_cookies_from_local(self):
        """
        Load cookies from local file
        :return:
        """
        cookies_file = ''
        if not os.path.exists(self.cookies_folder):
            return False
        for name in os.listdir(self.cookies_folder):
            if name.endswith('.cookies'):
                cookies_file = f"""{self.cookies_folder}{name}"""
                break
        if cookies_file == '':
            return False
        with open(cookies_file, 'rb') as f:
            local_cookies = pickle.load(f)
        self.set_cookies(local_cookies)

    def save_cookies_to_local(self, cookie_file_name):
        """
        Save cookies to local files
        :return:
        """
        cookies_file = f"""{self.cookies_folder}{cookie_file_name}.cookies"""
        directory = os.path.dirname(cookies_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cookies_file, 'wb') as f:
            pickle.dump(self.get_cookies(), f)


class QRLogin(object):
    """
    QR login util
    """
    def __init__(self, session_util: SessionUtil):
        self.qrcode_image_file = QR_FILE
        self.session_util = session_util
        self.session = self.session_util.get_session()

        self.is_login = False
        self.refresh_login_status()

    def refresh_login_status(self):
        """
        Refresh login status
        :return:
        """
        self.is_login = self._verify_cookies()

    def _verify_cookies(self):
        """
        Verify cookies are valid
        Make request to user order list page. https://order.jd.com/center/list.action
        :return:
        """
        payload = {
            'rid': str(int(time.time) * 1000)
        }
        try:
            resp = self.session.get(url=env_params.get('USER_ORDER_LIST'), params=payload, allow_redirects=False)
            if resp.status_code == requests.codes.OK:
                return True
        except Exception as e:
            logger.error(f"""Verify cookies error. Error - {str(e)}""")
        return False

    def _get_login_page(self):
        """
        Retrieve jd's login page
        :return:
        """
        page = self.session.get(url=env_params.get('USER_LOGIN_PAGE'), headers=self.session_util.get_headers())
        return page

    def _get_qrcode(self):
        """
        Retrieve QR image & display
        :return:
        """
        payload = {
            'appid': 133,
            'size': 147,
            't': str(int(time.time() * 1000))
        }
        headers = {
            'User-Agent': self.session_util.get_user_agent(),
            'Referer': env_params.get('QR_IMAGE_SHOW_REFER')
        }
        resp = self.session.get(url=env_params.get('QR_IMAGE_SHOW'), headers=headers, params=payload)

        if not (resp.status_code == requests.codes.OK):
            logger.error('Retrieve QR image error.')
            return False

        with open(self.qrcode_image_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024):
                f.write(chunk)

        logger.log('Retrieve QR image success. Please Open App to scan...')

        if os.name == "nt":
            os.system('start ' + self.qrcode_image_file)  # for Windows
        else:
            if os.uname()[0] == "Linux":
                if "deepin" in os.uname()[2]:
                    os.system("deepin-image-viewer " + self.qrcode_image_file)  # for deepin
                else:
                    os.system("eog " + self.qrcode_image_file)  # for Linux
            else:
                os.system("open " + self.qrcode_image_file)  # for Mac
        return True

    def _get_qrcode_ticket(self):
        """
        Retrieve ticket
        :return:
        """
        payload = {
            'appid': '133',
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'token': self.session.cookies.get('wlfstk_smdl'),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.session_util.get_user_agent(),
            'Referer': env_params.get('QR_TICKET_REFER'),
        }
        resp = self.session.get(url=env_params.get('QR_TICKET'), headers=headers, params=payload)

        if not (resp.status_code == requests.codes.OK):
            logger.error('Retrieve QR image scan status error.')
            return False

        resp_json = parse_json(resp.text)
        if resp_json['code'] != 200:
            logger.info('Code: %s, Message: %s', resp_json['code'], resp_json['msg'])
            return False
        else:
            logger.info('Mobile client confirmation has been completed.')
            return resp_json['ticket']

    def _verify_qr_ticket(self, ticket):
        """
        Use the ticket to do check with jd server
        :param ticket:
        :return:
        """
        headers = {
            'User-Agent': self.session_util.get_user_agent(),
            'Referer': env_params.get('QR_TICKET_VALIDATE_REFER'),
        }
        payload = {
            't': ticket
        }
        resp = self.session.get(url=env_params.get('QR_TICKET_VALIDATE'), headers=headers, params=payload)
        if not (resp.status_code == requests.codes.OK):
            logger.error('Verify QR scan ticket error.')
            return False
        resp_json = json.loads(resp.text)
        if resp_json['returnCode'] == 0:
            return True
        else:
            logger.info(resp_json)
            return False

    def login_by_qr(self):
        """
        Do QR login
        :return:
        """
        self._get_login_page()

        # Get QR code image
        if not self._get_qrcode():
            raise SKException('QR image download error.')

        # Get QR code's ticket
        ticket = None
        retry_times = 85
        for _ in range(retry_times):
            ticket = self._get_qrcode_ticket()
            if ticket:
                break
            time.sleep(4)

        if not ticket:
            raise SKException('The QR code has expired, please scan it again')

        # Verify QR code's ticket
        if not self._verify_qr_ticket(ticket):
            raise SKException('QR code verify failed...')

        self.refresh_login_status()
        logger.info('QR code login successful!!!')


class Seckill(object):
    def __init__(self):
        self.session_util = SessionUtil()
        self.session_util.load_cookies_from_local()
        self.qr_login = QRLogin(self.session_util)

        self.sku_id = env_params.get('SKU_ID')
        self.seckill_num = 2
        self.seckill_init_info = dict()
        self.seckill_url = dict()
        self.seckill_order_data = dict()
        self.timers = Timer()

        self.session = self.session_util.get_session()
        self.user_agent = self.session_util.get_user_agent()
        self.nick_name = None

    def login_by_qrcode(self):
        """
        QR code login
        :return:
        """
        if self.qr_login.is_login:
            logger.info('Login successful!!!')
            return

        self.qr_login.login_by_qr()

        if self.qr_login.is_login:
            self.nick_name = self.get_username()
            self.session_util.save_cookies_to_local(self.nick_name)
        else:
            raise SKException('QR code login failed...')

    def check_login(func):
        """
        User login status check decorator
        :return:
        """
        @functools.wraps(func)
        def new_func(self, *args, **kwargs):
            if not self.qrlogin.is_login:
                logger.info(f"""{func.__name__} need login before call, start QR code login...""")
                self.login_by_qrcode()
            return func(self, *args, **kwargs)
        return new_func

    @check_login
    def order(self):
        """
        Order
        :return:
        """
        self._order()

    @check_login
    def buy(self):
        """
        Buy
        :return:
        """
        self._buy()

    def buy_by_multi_process(self, work_count=5):
        """
        Multi process to seckill
        :param work_count:
        :return:
        """
        with ProcessPoolExecutor(work_count) as pool:
            for i in range(work_count):
                pool.submit(self.buy)

    def _order(self):
        """
        Order
        :return:
        """
        while True:
            try:
                self.make_order()
                break
            except Exception as e:
                logger.error(f"""Order occur error. Error - {str(e)}""")
            wait_time()

    def _buy(self):
        """
        Buy
        :return:
        """
        while True:
            try:
                self.request_seckill_url()
                while True:
                    self.request_seckill_checkout_page()
                    self.submit_seckill_order()
            except Exception as e:
                logger.error(f"""Buy occur error. Error - {str(e)}""")
            wait_time()

    def make_order(self):
        """
        Product Order
        :return:
        """
        logger.info(f"""商品名称: {self.get_sku_title()}""")
        url = env_params.get('YUSHOW')
        payload = {
            'callback': 'fetchJSON',
            'sku': self.sku_id,
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': env_params.get('YUSHOW_REFER').__str__().format(self.sku_id),
        }
        resp = self.session.get(url=url, params=payload, headers=headers)
        resp_json = parse_json(resp.text)
        reserve_url = resp_json.get('url')
        self.timers.start()
        while True:
            try:
                self.session.get(url='https:' + reserve_url)
                logger.info('预约成功，已获得抢购资格 / 您已成功预约过了，无需重复预约')
                # if global_config.getRaw('messenger', 'enable') == 'true':
                #     success_message = "预约成功，已获得抢购资格 / 您已成功预约过了，无需重复预约"
                #     send_wechat(success_message)
                # break
            except Exception as e:
                logger.error(f"""预约失败正在重试... {str(e)}""")

    def get_username(self):
        """
        Retrieve user info
        :return:
        """
        url = env_params.get('USER_INFO')
        payload = {
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': env_params.get('USER_INFO_REFER'),
        }
        resp = self.session.get(url=url, params=payload, headers=headers)
        try_count = 5
        while not resp.text.startswith("jQuery"):
            try_count = try_count - 1
            if try_count > 0:
                resp = self.session.get(url=url, params=payload, headers=headers)
            else:
                break
            wait_time()
        # 响应中包含了许多用户信息，现在在其中返回昵称
        # jQuery2381773({"imgUrl":"//storage.360buyimg.com/i.imageUpload/xxx.jpg","lastLoginTime":"","nickName":"xxx","plusStatus":"0","realName":"xxx","userLevel":x,"userScoreVO":{"accountScore":xx,"activityScore":xx,"consumptionScore":xxxxx,"default":false,"financeScore":xxx,"pin":"xxx","riskScore":x,"totalScore":xxxxx}})
        return parse_json(resp.text).get('nickName')

    def get_sku_title(self):
        """
        Retrieve Product title
        :return:
        """
        url = env_params.get('PRODUCT_INFO').__str__().format(self.sku_id)
        resp = self.session.get(url).content
        x_data = etree.HTML(resp)
        sku_title = x_data.xpath('/html/head/title/text()')
        return sku_title[0]

    def get_seckill_url(self):
        """获取商品的抢购链接
        点击"抢购"按钮后，会有两次302跳转，最后到达订单结算页面
        这里返回第一次跳转后的页面url，作为商品的抢购链接
        :return: 商品的抢购链接
        """
        url = env_params.get('GET_SECKILL_LINK')
        payload = {
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'skuId': self.sku_id,
            'from': 'pc',
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Host': 'itemko.jd.com',
            'Referer': env_params.get('GET_SECKILL_LINK_REFER').__str__().format(self.sku_id),
        }
        while True:
            resp = self.session.get(url=url, headers=headers, params=payload)
            resp_json = parse_json(resp.text)
            if resp_json.get('url'):
                # https://divide.jd.com/user_routing?skuId=8654289&sn=c3f4ececd8461f0e4d7267e96a91e0e0&from=pc
                router_url = 'https:' + resp_json.get('url')
                # https://marathon.jd.com/captcha.html?skuId=8654289&sn=c3f4ececd8461f0e4d7267e96a91e0e0&from=pc
                seckill_url = router_url.replace('divide', 'marathon').replace('user_routing', 'captcha.html')
                logger.info("抢购链接获取成功: %s", seckill_url)
                return seckill_url
            else:
                logger.info("抢购链接获取失败，稍后自动重试")
                wait_time()

    def request_seckill_url(self):
        """访问商品的抢购链接（用于设置cookie等"""
        logger.info(f"""用户: {self.get_username()}""")
        logger.info(f"""商品名称: {self.get_sku_title()}""")
        self.timers.start()
        self.seckill_url[self.sku_id] = self.get_seckill_url()
        logger.info('访问商品的抢购连接...')
        headers = {
            'User-Agent': self.user_agent,
            'Host': 'marathon.jd.com',
            'Referer': env_params.get('REQUEST_SECKILL_REFER').__str__().format(self.sku_id),
        }
        self.session.get(url=self.seckill_url.get(self.sku_id), headers=headers, allow_redirects=False)

    def request_seckill_checkout_page(self):
        """访问抢购订单结算页面"""
        logger.info('访问抢购订单结算页面...')
        url = env_params.get('REQUEST_SECKILL_CHECKOUT')
        payload = {
            'skuId': self.sku_id,
            'num': self.seckill_num,
            'rid': int(time.time())
        }
        headers = {
            'User-Agent': self.user_agent,
            'Host': 'marathon.jd.com',
            'Referer': env_params.get('REQUEST_SECKILL_CHECKOUT_REFER').__str__().format(self.sku_id),
        }
        self.session.get(url=url, params=payload, headers=headers, allow_redirects=False)

    def _get_seckill_init_info(self):
        """获取秒杀初始化信息（包括：地址，发票，token）
        :return: 初始化信息组成的dict
        """
        logger.info('获取秒杀初始化信息...')
        url = env_params.get('SECKILL_INIT')
        data = {
            'sku': self.sku_id,
            'num': self.seckill_num,
            'isModifyAddress': 'false',
        }
        headers = {
            'User-Agent': self.user_agent,
            'Host': 'marathon.jd.com',
        }
        resp = self.session.post(url=url, data=data, headers=headers)
        resp_json = None
        try:
            resp_json = parse_json(resp.text)
        except Exception:
            raise SKException('抢购失败，返回信息:{}'.format(resp.text[0: 128]))

        return resp_json

    def _get_seckill_order_data(self):
        """生成提交抢购订单所需的请求体参数
        :return: 请求体参数组成的dict
        """
        logger.info('生成提交抢购订单所需参数...')
        # 获取用户秒杀初始化信息
        self.seckill_init_info[self.sku_id] = self._get_seckill_init_info()
        init_info = self.seckill_init_info.get(self.sku_id)
        default_address = init_info['addressList'][0]  # 默认地址dict
        invoice_info = init_info.get('invoiceInfo', {})  # 默认发票信息dict, 有可能不返回
        token = init_info['token']
        data = {
            'skuId': self.sku_id,
            'num': self.seckill_num,
            'addressId': default_address['id'],
            'yuShou': 'true',
            'isModifyAddress': 'false',
            'name': default_address['name'],
            'provinceId': default_address['provinceId'],
            'cityId': default_address['cityId'],
            'countyId': default_address['countyId'],
            'townId': default_address['townId'],
            'addressDetail': default_address['addressDetail'],
            'mobile': default_address['mobile'],
            'mobileKey': default_address['mobileKey'],
            'email': default_address.get('email', ''),
            'postCode': '',
            'invoiceTitle': invoice_info.get('invoiceTitle', -1),
            'invoiceCompanyName': '',
            'invoiceContent': invoice_info.get('invoiceContentType', 1),
            'invoiceTaxpayerNO': '',
            'invoiceEmail': '',
            'invoicePhone': invoice_info.get('invoicePhone', ''),
            'invoicePhoneKey': invoice_info.get('invoicePhoneKey', ''),
            'invoice': 'true' if invoice_info else 'false',
            'password': env_params.get('PAYMENT_PWD'),
            'codTimeType': 3,
            'paymentType': 4,
            'areaCode': '',
            'overseas': 0,
            'phone': '',
            'eid': env_params.get('EID'),
            'fp': env_params.get('FP'),
            'token': token,
            'pru': ''
        }

        return data

    def submit_seckill_order(self):
        """提交抢购（秒杀）订单
        :return: 抢购结果 True/False
        """
        url = 'https://marathon.jd.com/seckillnew/orderService/pc/submitOrder.action'
        payload = {
            'skuId': self.sku_id,
        }
        try:
            self.seckill_order_data[self.sku_id] = self._get_seckill_order_data()
        except Exception as e:
            logger.info('抢购失败，无法获取生成订单的基本信息，接口返回:【{}】'.format(str(e)))
            return False

        logger.info('提交抢购订单...')
        headers = {
            'User-Agent': self.user_agent,
            'Host': 'marathon.jd.com',
            'Referer': 'https://marathon.jd.com/seckill/seckill.action?skuId={0}&num={1}&rid={2}'.format(
                self.sku_id, self.seckill_num, int(time.time())),
        }
        resp = self.session.post(
            url=url,
            params=payload,
            data=self.seckill_order_data.get(
                self.sku_id),
            headers=headers)
        resp_json = None
        try:
            resp_json = parse_json(resp.text)
        except Exception as e:
            logger.info('抢购失败，返回信息:{}'.format(resp.text[0: 128]))
            return False
        # 返回信息
        # 抢购失败：
        # {'errorMessage': '很遗憾没有抢到，再接再厉哦。', 'orderId': 0, 'resultCode': 60074, 'skuId': 0, 'success': False}
        # {'errorMessage': '抱歉，您提交过快，请稍后再提交订单！', 'orderId': 0, 'resultCode': 60017, 'skuId': 0, 'success': False}
        # {'errorMessage': '系统正在开小差，请重试~~', 'orderId': 0, 'resultCode': 90013, 'skuId': 0, 'success': False}
        # 抢购成功：
        # {"appUrl":"xxxxx","orderId":820227xxxxx,"pcUrl":"xxxxx","resultCode":0,"skuId":0,"success":true,"totalMoney":"xxxxx"}
        if resp_json.get('success'):
            order_id = resp_json.get('orderId')
            total_money = resp_json.get('totalMoney')
            pay_url = 'https:' + resp_json.get('pcUrl')
            logger.info('抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}'.format(order_id, total_money, pay_url))
            # if global_config.getRaw('messenger', 'enable') == 'true':
            #     success_message = "抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}".format(order_id, total_money, pay_url)
            #     send_wechat(success_message)
            return True
        else:
            logger.info('抢购失败，返回信息:{}'.format(resp_json))
            # if global_config.getRaw('messenger', 'enable') == 'true':
            #     error_message = '抢购失败，返回信息:{}'.format(resp_json)
            #     send_wechat(error_message)
            return False
