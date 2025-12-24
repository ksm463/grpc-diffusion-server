import configparser
import os
from functools import lru_cache

@lru_cache()
def get_manager_config():
    config_path = "/web-manager/app/core/manager_config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)

    # Override with environment variables if present
    if 'SUPABASE' in config:
        if os.getenv('SUPABASE_KEY'):
            config['SUPABASE']['KEY'] = os.getenv('SUPABASE_KEY')
        if os.getenv('SUPABASE_SERVICE_KEY'):
            config['SUPABASE']['SERVICE_KEY'] = os.getenv('SUPABASE_SERVICE_KEY')

    return config

@lru_cache()
def get_server_config():
    config_path = "/web-manager/ai-server/server_config.ini"
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

manager_config = get_manager_config()
server_config = get_server_config()
