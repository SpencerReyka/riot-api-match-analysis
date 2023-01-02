import os
import json
from losses import set_up_code


def read_secrets() -> dict:
    filename = os.path.join('config.txt')
    try:
        with open(filename, mode='r') as f:
            config = json.loads(f.read())
            for env in config["EnvVar"]:
                if env not in os.environ: 
                    os.environ[env] = config["EnvVar"][env]
    except FileNotFoundError:
        return {}
        
secrets = read_secrets()

set_up_code()