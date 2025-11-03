"""Management command to synchronise media folders with attachments."""

from django.core.management.base import BaseCommand

from person.models import Person
from person.utils import sync_all_persons, sync_person_attachments


class Command(BaseCommand):
    help = "Sync media folders with PersonAttachment database records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--person-id",
            type=int,
            help="Sync a single person by primary key",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Sync all persons (default behaviour)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without saving changes",
        )

    def handle(self, *args, **options):
        person_id = options.get("person_id")
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))

        if person_id:
            self._sync_single_person(person_id, dry_run=dry_run)
            return

        self._sync_all(dry_run=dry_run, verbose=not dry_run)

    def _sync_single_person(self, person_id: int, *, dry_run: bool = False) -> None:
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Person with ID {person_id} not found"))
            return

        self.stdout.write(f"Syncing: {person.name} (ID: {person.pk})")
        stats = sync_person_attachments(person, dry_run=dry_run)

        if dry_run:
            pending = len(stats.get("pending_files", []))
            self.stdout.write(
                self.style.WARNING(
                    f"Would create {pending} new attachment(s); {stats['files_existing']} file(s) already tracked"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Created {created} new attachment(s) ({existing} already tracked)".format(
                        created=stats["files_created"],
                        existing=stats["files_existing"],
                    )
                )
            )

    def _sync_all(self, *, dry_run: bool = False, verbose: bool = True) -> None:
        if dry_run:
            self.stdout.write("Scanning all persons (dry run)...")
        else:
            self.stdout.write("Syncing all persons...")

        stats = sync_all_persons(verbose=verbose, dry_run=dry_run)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nWould sync {count} person(s). Pending attachments: {pending}. Already tracked: {existing}".format(
                        count=stats["persons_synced"],
                        pending=stats["pending_files"],
                        existing=stats["total_files_existing"],
                    )
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ Synced {persons} person(s)\n"
                    "  Created: {created} new attachment(s)\n"
                    "  Existing: {existing} file(s) already tracked\n"
                    "  Errors: {errors}".format(
                        persons=stats["persons_synced"],
                        created=stats["total_files_created"],
                        existing=stats["total_files_existing"],
                        errors=len(stats["errors"]),
                    )
                )
            )

        if stats["errors"]:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for error in stats["errors"]:
                self.stdout.write(f"  - {error}")
