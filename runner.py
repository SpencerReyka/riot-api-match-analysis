import os
import json
from losses import set_up_code


def read_secrets() -> dict:
    filename = os.path.join('config.txt')
    try:
        with open(filename, mode='r') as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return {}
        
secrets = read_secrets()

set_up_code()