import configparser
from functools import lru_cache

@lru_cache()
def get_manager_config():
    config_path = "/web-manager/app/core/manager_config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

@lru_cache()
def get_server_config():
    config_path = "/web-manager/ai-server/server_config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

manager_config = get_manager_config()
server_config = get_server_config()
