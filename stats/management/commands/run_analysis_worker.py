import time

import pika
from django.core.management.base import BaseCommand, CommandError

from stats.backbone_worker import run_worker


class Command(BaseCommand):
    help = "Relay analysis outbox events and consume them from Backbone"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        if options["once"]:
            try:
                run_worker(once=True)
            except RuntimeError as exc:
                raise CommandError(str(exc)) from exc
            return

        while True:
            try:
                run_worker()
            except (pika.exceptions.AMQPError, OSError) as exc:
                self.stderr.write(
                    f"Backbone connection unavailable ({type(exc).__name__}); retrying"
                )
                time.sleep(5)
