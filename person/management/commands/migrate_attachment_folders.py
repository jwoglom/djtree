"""Command to migrate legacy attachment folders to the new structure."""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from person.models import Person


class Command(BaseCommand):
    help = "Migrate attachment folders from the legacy structure to media/people/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show actions without moving files",
        )
        parser.add_argument(
            "--delete-old",
            action="store_true",
            help="Delete old person_attachments folders after a successful migration",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delete_old = options["delete_old"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))

        media_root = Path(settings.MEDIA_ROOT)
        old_base = media_root / "person_attachments"
        new_base = media_root / "people"

        if not old_base.exists():
            self.stdout.write(self.style.WARNING("No legacy folders found to migrate."))
            return

        if not dry_run:
            new_base.mkdir(parents=True, exist_ok=True)

        stats = {
            "persons_processed": 0,
            "files_moved": 0,
            "folders_created": 0,
            "errors": [],
        }

        for person in Person.objects.all():
            try:
                result = self.migrate_person(person, old_base, media_root, dry_run=dry_run)
                stats["persons_processed"] += 1
                stats["files_moved"] += result["files_moved"]
                stats["folders_created"] += result["folder_created"]
            except Exception as exc:  # pragma: no cover - defensive
                message = f"{person.name} (ID: {person.pk}): {exc}"
                stats["errors"].append(message)
                self.stdout.write(self.style.ERROR(f"✗ {message}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                "Migration complete!\n"
                "  Persons processed: {persons}\n"
                "  Files moved: {files}\n"
                "  Folders created: {folders}\n"
                "  Errors: {errors}".format(
                    persons=stats["persons_processed"],
                    files=stats["files_moved"],
                    folders=stats["folders_created"],
                    errors=len(stats["errors"]),
                )
            )
        )

        if delete_old and not dry_run:
            self.stdout.write("\nDeleting old folders...")
            self.delete_old_folders(old_base)

    def migrate_person(self, person: Person, old_base: Path, media_root: Path, *, dry_run: bool) -> dict:
        result = {"files_moved": 0, "folder_created": 0}

        old_folder_path = self.get_old_folder_path(person)
        old_full_path = old_base / old_folder_path

        if not old_full_path.exists():
            return result

        new_folder_relative = Path(person.get_attachment_folder_path())
        new_full_path = media_root / new_folder_relative

        self.stdout.write(f"Migrating: {person.name} (ID: {person.pk})")
        self.stdout.write(f"  From: {old_full_path}")
        self.stdout.write(f"  To:   {new_full_path}")

        if dry_run:
            file_count = sum(1 for item in old_full_path.rglob("*") if item.is_file())
            self.stdout.write(f"  Would move {file_count} file(s)")
            return result

        if not new_full_path.exists():
            new_full_path.mkdir(parents=True, exist_ok=True)
            result["folder_created"] = 1

        for item in old_full_path.rglob("*"):
            if not item.is_file():
                continue

            relative_item = item.relative_to(old_full_path)
            destination = new_full_path / relative_item
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(destination))
            result["files_moved"] += 1

        old_prefix = Path("person_attachments") / old_folder_path
        for attachment in person.attachments.all():
            old_file_name = Path(attachment.file.name)
            try:
                relative = old_file_name.relative_to(old_prefix)
            except ValueError:
                continue

            new_file_name = new_folder_relative / relative
            attachment.file.name = str(new_file_name)
            attachment.save(update_fields=["file"])

        self.stdout.write(self.style.SUCCESS(f"  ✓ Moved {result['files_moved']} file(s)"))
        return result

    def get_old_folder_path(self, person: Person) -> str:
        name = person.name
        if not name:
            return f"unknown_person_{person.pk}"

        parts = []
        if name.last_name:
            parts.append(name.last_name.lower())
        if name.middle_name:
            parts.append(name.middle_name.lower())
        if name.first_name:
            parts.append(name.first_name.lower())

        if not parts:
            return f"unknown_person_{person.pk}"

        folder_name = "_".join(parts)

        birth = person.birth
        if birth and birth.date:
            folder_name += f"_{birth.date.year}"

        from django.utils.text import slugify

        return slugify(folder_name)

    def delete_old_folders(self, old_base: Path) -> None:
        if old_base.exists():
            shutil.rmtree(old_base)
            self.stdout.write(self.style.SUCCESS(f"✓ Deleted {old_base}"))
