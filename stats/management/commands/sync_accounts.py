from django.core.management.base import BaseCommand, CommandError

from stats.models import RiotAccount
from stats.riot import RiotAPIError
from stats.services import sync_account


class Command(BaseCommand):
    help = "Synchronize one or more Riot IDs, or every account already tracked."

    def add_arguments(self, parser):
        parser.add_argument("riot_ids", nargs="*", metavar="GAME#TAG")
        parser.add_argument(
            "--all",
            action="store_true",
            dest="sync_all",
            help="Synchronize every account already stored.",
        )

    def handle(self, *args, **options):
        riot_ids = options["riot_ids"]
        sync_all = options["sync_all"]
        if sync_all and riot_ids:
            raise CommandError("Use either --all or explicit Riot IDs, not both.")
        if not sync_all and not riot_ids:
            raise CommandError("Provide at least one GAME#TAG Riot ID or use --all.")

        targets = []
        if sync_all:
            targets = [
                (
                    account.game_name,
                    account.tag_line,
                    account.routing_region,
                    account.platform_region,
                )
                for account in RiotAccount.objects.all()
            ]
        else:
            for riot_id in riot_ids:
                game_name, separator, tag_line = riot_id.rpartition("#")
                if not separator or not game_name.strip() or not tag_line.strip():
                    raise CommandError(f"Invalid Riot ID: {riot_id!r}; expected GAME#TAG.")
                targets.append((game_name.strip(), tag_line.strip(), None, None))

        if not targets:
            self.stdout.write("No tracked accounts to synchronize.")
            return

        for game_name, tag_line, routing_region, platform_region in targets:
            try:
                result = sync_account(
                    game_name,
                    tag_line,
                    routing_region=routing_region,
                    platform_region=platform_region,
                )
            except (RiotAPIError, ValueError) as exc:
                raise CommandError(f"{game_name}#{tag_line}: {exc}") from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"{result.account.riot_id}: {result.fetched_matches} new, "
                    f"{result.cached_matches} cached"
                )
            )
