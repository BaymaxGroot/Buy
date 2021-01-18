import os

import yaml

config_params = {}


def init_config_params(file):
    """
    从配置文件初始化系统运行配置参数
    :param file: config file name
    :return: config obj
    """
    global config_params
    if config_params:
        return config_params
    try:
        with open(file, 'r', encoding='utf-8') as stream:
            config_params = yaml.load(stream, Loader=yaml.FullLoader)
        return config_params
    except Exception as e:
        raise


env_params = init_config_params(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config/config.yml"))
