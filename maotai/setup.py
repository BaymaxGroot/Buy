import sys
from maotai.logger.logutil import logger
from maotai.common.seckill import Seckill

if __name__ == '__main__':
    a = """
    京东茅台抢购
                                               
    功能列表：                                                                                
     1. 预约茅台 
     2. 抢购茅台
    """
    print(a)
    choice = input('请选择: ')

    seckill = Seckill()
    if choice == '1':
        seckill.order()
    elif choice == '2':
        # seckill.buy_by_multi_process()
        seckill.buy()
    else:
        logger.info('目前没有提供此功能...')
        sys.exit(1)
