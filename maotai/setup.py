import sys
from maotai.logger.logutil import logger
from maotai.common.seckill import Seckill

if __name__ == '__main__':
    a = """

       oooo oooooooooo.            .oooooo..o                     oooo         o8o  oooo  oooo  
       `888 `888'   `Y8b          d8P'    `Y8                     `888         `"'  `888  `888  
        888  888      888         Y88bo.       .ooooo.   .ooooo.   888  oooo  oooo   888   888  
        888  888      888          `"Y8888o.  d88' `88b d88' `"Y8  888 .8P'   `888   888   888  
        888  888      888 8888888      `"Y88b 888ooo888 888        888888.     888   888   888  
        888  888     d88'         oo     .d8P 888    .o 888   .o8  888 `88b.   888   888   888  
    .o. 88P o888bood8P'           8""88888P'  `Y8bod8P' `Y8bod8P' o888o o888o o888o o888o o888o 
    `Y888P                                                                                                                                                  
                                               
    功能列表：                                                                                
     1. 预约茅台 
     2. 抢购茅台
    """
    print(a)
    seckill = Seckill()
    choice = input('请选择: ')

    if choice == '1':
        seckill.order()
    elif choice == '2':
        seckill.buy_by_multi_process()
    else:
        logger.info('目前没有提供此功能...')
        sys.exit(1)
