"""Utility helpers for synchronising person media folders."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Person, PersonAttachment


SKIP_PATTERNS = {".DS_Store", "Thumbs.db", ".gitkeep", ".gitignore"}

FILE_TYPE_MAP = {
    "photo": [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp", ".webp", ".heic", ".heif"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"],
    "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"],
    "audio": [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"],
}


def should_skip_file(filename: str) -> bool:
    """Return True when a filename should be ignored during sync."""

    return filename.startswith(".") or filename.startswith("_") or filename in SKIP_PATTERNS


def detect_file_type(filename: str) -> str:
    """Return a best-guess file type based on extension."""

    suffix = Path(filename).suffix.lower()
    for file_type, extensions in FILE_TYPE_MAP.items():
        if suffix in extensions:
            return file_type
    return "document"


def _gather_files(path: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from path.rglob("*")
    else:
        yield from path.glob("*")


def sync_person_attachments(person: "Person", recursive: bool = True, dry_run: bool = False) -> Dict[str, object]:
    """Synchronise files on disk with ``PersonAttachment`` records."""

    folder_path = person.get_attachment_folder_path()
    media_root = Path(settings.MEDIA_ROOT)
    full_path = media_root / folder_path
    full_path.mkdir(parents=True, exist_ok=True)

    existing_files = set(filter(None, person.attachments.values_list("file", flat=True)))

    stats: Dict[str, object] = {
        "files_found": 0,
        "files_created": 0,
        "files_existing": 0,
        "files_skipped": 0,
        "created_attachments": [],
        "pending_files": [],
        "dry_run": dry_run,
    }

    for file_path in _gather_files(full_path, recursive=recursive):
        if not file_path.is_file():
            continue

        if should_skip_file(file_path.name):
            stats["files_skipped"] += 1
            continue

        stats["files_found"] += 1
        relative_path = str(file_path.relative_to(media_root))

        if relative_path in existing_files:
            stats["files_existing"] += 1
            continue

        stats["files_created"] += 1
        stats["pending_files"].append(relative_path)

        if dry_run:
            continue

        from .models import PersonAttachment  # imported lazily to avoid circular imports

        file_type = detect_file_type(file_path.name)
        parent_folder = file_path.parent
        try:
            relative_parent = parent_folder.relative_to(full_path)
            if str(relative_parent):
                location = str(relative_parent)
            else:
                location = "root folder"
        except ValueError:
            location = parent_folder.name

        attachment = PersonAttachment.objects.create(
            person=person,
            file=relative_path,
            original_filename=file_path.name,
            file_type=file_type,
            description=f"Auto-detected from {location}/",
        )

        # Preserve filesystem modified time when possible
        modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        if timezone.is_naive(modified):
            modified = timezone.make_aware(modified, timezone.get_current_timezone())
        attachment.uploaded_at = modified
        attachment.save(update_fields=["uploaded_at"])
        stats["created_attachments"].append(attachment)

    return stats


def sync_all_persons(verbose: bool = False, dry_run: bool = False) -> Dict[str, object]:
    """Run ``sync_person_attachments`` for every person in the database."""

    from .models import Person

    total_stats: Dict[str, object] = {
        "persons_synced": 0,
        "total_files_created": 0,
        "total_files_existing": 0,
        "pending_files": 0,
        "errors": [],
    }

    for person in Person.objects.all():
        try:
            stats = sync_person_attachments(person, recursive=True, dry_run=dry_run)
            total_stats["persons_synced"] += 1
            total_stats["total_files_created"] += stats["files_created"] if not dry_run else 0
            total_stats["total_files_existing"] += stats["files_existing"]
            total_stats["pending_files"] += len(stats.get("pending_files", []))

            if verbose and (stats["files_created"] or stats.get("pending_files")):
                created = stats["files_created"]
                if dry_run:
                    self_report = f"would create {len(stats['pending_files'])} file(s)"
                else:
                    self_report = f"created {created} file(s)"
                print(f"✓ {person.name} (ID: {person.pk}): {self_report}")

        except Exception as exc:  # pragma: no cover - defensive logging
            message = f"Error syncing {person} (ID: {person.pk}): {exc}"
            total_stats["errors"].append(message)
            if verbose:
                print(f"✗ {message}")

    return total_stats
