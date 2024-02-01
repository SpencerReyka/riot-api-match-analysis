#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import json

def main():
    """Run administrative tasks."""
    read_secrets()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stat_losses.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

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

if __name__ == '__main__':
    main()
