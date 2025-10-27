# Person Media Folders Implementation Plan

## Overview

Redesign media file management so each person has a designated folder (`media/people/Lastname_Firstname_ID/`) containing all their media files. Files can be uploaded via Django admin or manually placed in the folder - both methods create/sync PersonAttachment model objects automatically.

## Design Decisions

### Folder Structure
- **Format:** `media/people/Lastname_Firstname_42/`
- **Location:** All person folders grouped under `media/people/`
- **Naming:** Capitalized last name, capitalized first name, person ID
- **Subfolders:** Allowed (e.g., `photos/`, `documents/`, `certificates/`)

### Auto-Sync Strategy
- **Management command:** `python manage.py sync_attachments` for manual/scheduled sync
- **Server startup:** Automatic sync of all persons when Django server starts
- **Admin action:** Bulk sync for selected persons in admin list view
- **No signals:** Avoid performance impact on individual model saves/loads

### Migration Strategy
- **Immediate migration:** One-time migration command to move files from old to new structure
- **Old structure:** `media/person_attachments/lastname_firstname_1956/`
- **New structure:** `media/people/Lastname_Firstname_42/`
- **Conflict handling:** Not expected after one-time migration (unique person IDs)

---

## Current State Analysis

### Existing Implementation
- **PersonAttachment model** (`person/models.py:117-142`)
  - ForeignKey to Person
  - FileField with `upload_to='person_attachments/'`
  - Tracks original_filename, description, file_type, uploaded_at

- **get_attachment_folder_path()** (`person/models.py:78-102`)
  - Current format: `lastname_middlename_firstname_1956`
  - Uses birth year for uniqueness
  - Slugifies names for filesystem safety

- **Custom admin upload** (`person/admin.py:373-438`)
  - Drag-and-drop interface
  - Handles multiple files
  - Custom save_formset() for file processing

### Current Folder Structure
```
media/
└── person_attachments/
    ├── smith_john_1956/
    ├── doe_jane_marie_1967/
    └── unknown_person_5/
```

### Target Folder Structure
```
media/
└── people/
    ├── Smith_John_42/
    │   ├── birth_certificate.pdf
    │   ├── photos/
    │   │   ├── portrait.jpg
    │   │   └── family_photo.png
    │   └── documents/
    │       └── immigration_papers.pdf
    ├── Doe_Jane_108/
    └── Unknown_Person_5/
```

---

## Implementation Phases

### Phase 1: Update Folder Naming Convention

**File:** `person/models.py`

#### Changes to `get_attachment_folder_path()` (Lines 78-102)

**Current implementation:**
```python
def get_attachment_folder_path(self):
    """Generate folder path: lastname_middlename_firstname_1956"""
    # Uses birth year for uniqueness
    # Returns: 'smith_john_1956' or 'unknown_person_5'
```

**New implementation:**
```python
def get_attachment_folder_path(self):
    """Generate folder path: people/Lastname_Firstname_42"""
    name = self.name
    if name:
        parts = []
        if name.last_name:
            parts.append(name.last_name.capitalize())
        if name.first_name:
            parts.append(name.first_name.capitalize())

        if parts:
            folder_name = '_'.join(parts) + f'_{self.pk}'
        else:
            folder_name = f'Unknown_Person_{self.pk}'
    else:
        folder_name = f'Unknown_Person_{self.pk}'

    return f'people/{folder_name}'
```

**Example outputs:**
- `people/Smith_John_42`
- `people/Doe_Jane_Marie_108`
- `people/Unknown_Person_5`

#### Update `PersonAttachment.save()` (Lines 125-135)

Ensure the save method uses the new path format:
```python
def save(self, *args, **kwargs):
    if self.file:
        self.original_filename = os.path.basename(self.file.name)
        folder_path = self.person.get_attachment_folder_path()
        # Construct full path: people/Smith_John_42/filename.pdf
        self.file.name = os.path.join(folder_path, self.original_filename)
    super().save(*args, **kwargs)
```

**Migration:** No database migration needed (only FileField paths change)

---

### Phase 2: Directory Sync Utility Function

**New file:** `person/utils.py`

#### Core Function: `sync_person_attachments(person, recursive=True)`

**Purpose:** Scan person's media folder and create PersonAttachment records for orphaned files

**Algorithm:**
```python
import os
from pathlib import Path
from django.conf import settings
from .models import Person, PersonAttachment

def sync_person_attachments(person, recursive=True):
    """
    Sync person's media folder with database.

    Args:
        person: Person instance
        recursive: If True, scan subfolders

    Returns:
        dict with sync statistics
    """
    folder_path = person.get_attachment_folder_path()
    full_path = os.path.join(settings.MEDIA_ROOT, folder_path)

    # Create folder if it doesn't exist
    os.makedirs(full_path, exist_ok=True)

    stats = {
        'files_found': 0,
        'files_created': 0,
        'files_existing': 0,
        'files_skipped': 0,
        'created_attachments': []
    }

    # Get all existing attachment file paths for this person
    existing_files = set(
        att.file.name for att in person.attachments.all()
    )

    # Scan directory
    if recursive:
        file_iterator = Path(full_path).rglob('*')
    else:
        file_iterator = Path(full_path).glob('*')

    for file_path in file_iterator:
        if not file_path.is_file():
            continue

        # Skip system files
        if should_skip_file(file_path.name):
            stats['files_skipped'] += 1
            continue

        stats['files_found'] += 1

        # Get relative path from MEDIA_ROOT
        relative_path = str(file_path.relative_to(settings.MEDIA_ROOT))

        # Check if already tracked
        if relative_path in existing_files:
            stats['files_existing'] += 1
            continue

        # Create new attachment
        file_type = detect_file_type(file_path.name)
        attachment = PersonAttachment.objects.create(
            person=person,
            file=relative_path,
            original_filename=file_path.name,
            file_type=file_type,
            description=f"Auto-detected from {file_path.parent.name}/",
            uploaded_at=datetime.fromtimestamp(file_path.stat().st_mtime)
        )

        stats['files_created'] += 1
        stats['created_attachments'].append(attachment)

    return stats


def should_skip_file(filename):
    """Skip system and hidden files"""
    skip_patterns = [
        '.DS_Store',
        'Thumbs.db',
        '.gitkeep',
        '.gitignore',
    ]
    return (
        filename.startswith('.') or
        filename.startswith('_') or
        filename in skip_patterns
    )


def detect_file_type(filename):
    """Detect file type category from extension"""
    from pathlib import Path

    FILE_TYPE_MAP = {
        'photo': ['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp', '.heic', '.heif'],
        'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages'],
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv'],
        'audio': ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'],
        'certificate': [],  # User manually categorizes
    }

    ext = Path(filename).suffix.lower()

    for category, extensions in FILE_TYPE_MAP.items():
        if ext in extensions:
            return category

    return 'document'  # Default fallback
```

#### Helper Function: `sync_all_persons(verbose=False)`

**Purpose:** Bulk sync all persons in database

```python
def sync_all_persons(verbose=False):
    """
    Sync all persons in database.

    Args:
        verbose: Print progress messages

    Returns:
        dict with aggregate statistics
    """
    from .models import Person

    total_stats = {
        'persons_synced': 0,
        'total_files_created': 0,
        'total_files_existing': 0,
        'errors': []
    }

    persons = Person.objects.all()

    for person in persons:
        try:
            stats = sync_person_attachments(person)
            total_stats['persons_synced'] += 1
            total_stats['total_files_created'] += stats['files_created']
            total_stats['total_files_existing'] += stats['files_existing']

            if verbose and stats['files_created'] > 0:
                print(f"✓ {person.name} (ID: {person.pk}): {stats['files_created']} new files")

        except Exception as e:
            error_msg = f"Error syncing {person.name} (ID: {person.pk}): {str(e)}"
            total_stats['errors'].append(error_msg)
            if verbose:
                print(f"✗ {error_msg}")

    return total_stats
```

---

### Phase 3: Management Command for Sync

**New file:** `person/management/commands/sync_attachments.py`

```python
from django.core.management.base import BaseCommand
from person.models import Person
from person.utils import sync_person_attachments, sync_all_persons


class Command(BaseCommand):
    help = 'Sync media folders with PersonAttachment database records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--person-id',
            type=int,
            help='Sync specific person by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all persons (default)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without creating',
        )

    def handle(self, *args, **options):
        person_id = options.get('person_id')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        if person_id:
            # Sync single person
            try:
                person = Person.objects.get(pk=person_id)
                self.stdout.write(f'Syncing: {person.name} (ID: {person.pk})')

                if not dry_run:
                    stats = sync_person_attachments(person)
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Created {stats["files_created"]} new attachments '
                        f'({stats["files_existing"]} already tracked)'
                    ))
                else:
                    # TODO: Implement dry-run logic
                    self.stdout.write('Would create attachments for files in folder')

            except Person.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Person with ID {person_id} not found'))
                return

        else:
            # Sync all persons
            self.stdout.write('Syncing all persons...')

            if not dry_run:
                stats = sync_all_persons(verbose=True)

                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Synced {stats["persons_synced"]} persons\n'
                    f'  Created: {stats["total_files_created"]} new attachments\n'
                    f'  Existing: {stats["total_files_existing"]} already tracked\n'
                    f'  Errors: {len(stats["errors"])}'
                ))

                if stats['errors']:
                    self.stdout.write(self.style.ERROR('\nErrors:'))
                    for error in stats['errors']:
                        self.stdout.write(f'  - {error}')
            else:
                # TODO: Implement dry-run logic
                self.stdout.write('Would sync all persons')
```

**Usage:**
```bash
# Sync all persons
python manage.py sync_attachments

# Sync specific person
python manage.py sync_attachments --person-id 42

# Dry run to see what would happen
python manage.py sync_attachments --dry-run
```

---

### Phase 4: Auto-Sync on Server Startup

**File:** `person/apps.py`

#### Update PersonConfig

```python
from django.apps import AppConfig


class PersonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'person'

    def ready(self):
        """Run on Django startup"""
        import os
        from django.conf import settings

        # Only run sync in production/development servers, not during migrations
        if not os.environ.get('RUN_MAIN') == 'true':
            # Avoid running twice in development (Django's auto-reloader)
            return

        # Skip during migrations
        if 'migrate' in os.sys.argv or 'makemigrations' in os.sys.argv:
            return

        # Run sync
        self.sync_on_startup()

    def sync_on_startup(self):
        """Sync all person attachments on server startup"""
        from .utils import sync_all_persons
        import logging

        logger = logging.getLogger(__name__)
        logger.info('Starting attachment sync on server startup...')

        try:
            stats = sync_all_persons(verbose=False)
            logger.info(
                f'Attachment sync complete: '
                f'{stats["total_files_created"]} new files, '
                f'{stats["persons_synced"]} persons synced'
            )
        except Exception as e:
            logger.error(f'Error during startup sync: {str(e)}')
```

**Environment considerations:**
- Uses `RUN_MAIN` check to avoid double-execution in development
- Skips sync during migrations
- Uses logging instead of print statements
- Handles errors gracefully (doesn't crash server startup)

**Performance optimization:**
- Consider adding a flag to disable startup sync: `DISABLE_STARTUP_SYNC=1`
- For large datasets, consider using background task (Celery)
- Add caching to track last sync time per person

---

### Phase 5: Admin Action for Manual Sync

**File:** `person/admin.py`

#### Add Admin Action

**Location:** In `PersonAdmin` class (around line 291)

```python
class PersonAdmin(admin.ModelAdmin):
    # ... existing code ...

    actions = ['sync_selected_attachments']

    @admin.action(description='🔄 Sync media folders with database')
    def sync_selected_attachments(self, request, queryset):
        """
        Sync attachments for selected persons.
        Scans each person's media folder and creates database records
        for any files that aren't already tracked.
        """
        from .utils import sync_person_attachments

        total_created = 0
        total_existing = 0
        errors = []

        for person in queryset:
            try:
                stats = sync_person_attachments(person)
                total_created += stats['files_created']
                total_existing += stats['files_existing']
            except Exception as e:
                errors.append(f'{person.name}: {str(e)}')

        # Build success message
        message_parts = [
            f"Synced {queryset.count()} person(s).",
            f"Created {total_created} new attachment record(s).",
            f"{total_existing} file(s) already tracked."
        ]

        if errors:
            message_parts.append(f"{len(errors)} error(s) occurred.")

        message = ' '.join(message_parts)

        if errors:
            self.message_user(request, message, level='WARNING')
            for error in errors:
                self.message_user(request, f"Error: {error}", level='ERROR')
        else:
            self.message_user(request, message, level='SUCCESS')
```

**User experience:**
1. Go to Person admin list: `/admin/person/person/`
2. Select one or more persons using checkboxes
3. Choose "🔄 Sync media folders with database" from Actions dropdown
4. Click "Go"
5. See success message with statistics
6. Errors shown individually if any occur

---

### Phase 6: File Migration Command

**New file:** `person/management/commands/migrate_attachment_folders.py`

#### Purpose
One-time migration to move files from old structure to new structure:
- **Old:** `media/person_attachments/lastname_firstname_1956/`
- **New:** `media/people/Lastname_Firstname_42/`

#### Implementation

```python
import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from person.models import Person, PersonAttachment


class Command(BaseCommand):
    help = 'Migrate attachment folders from old structure to new structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--delete-old',
            action='store_true',
            help='Delete old folders after successful migration',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_old = options['delete_old']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        old_base = os.path.join(settings.MEDIA_ROOT, 'person_attachments')
        new_base = os.path.join(settings.MEDIA_ROOT, 'people')

        # Create new base directory
        if not dry_run:
            os.makedirs(new_base, exist_ok=True)

        stats = {
            'persons_processed': 0,
            'files_moved': 0,
            'folders_created': 0,
            'errors': [],
        }

        persons = Person.objects.all()

        for person in persons:
            try:
                result = self.migrate_person(person, old_base, new_base, dry_run)
                stats['persons_processed'] += 1
                stats['files_moved'] += result['files_moved']
                stats['folders_created'] += result['folder_created']

            except Exception as e:
                error_msg = f'{person.name} (ID: {person.pk}): {str(e)}'
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'✗ {error_msg}'))

        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(
            f'Migration complete!\n'
            f'  Persons processed: {stats["persons_processed"]}\n'
            f'  Files moved: {stats["files_moved"]}\n'
            f'  Folders created: {stats["folders_created"]}\n'
            f'  Errors: {len(stats["errors"])}'
        ))

        if delete_old and not dry_run:
            self.stdout.write('\nDeleting old folders...')
            self.delete_old_folders(old_base)

    def migrate_person(self, person, old_base, new_base, dry_run):
        """Migrate single person's files"""
        result = {'files_moved': 0, 'folder_created': 0}

        # Get old folder path (birth year based)
        old_folder_path = self.get_old_folder_path(person)
        old_full_path = os.path.join(old_base, old_folder_path)

        # Check if old folder exists
        if not os.path.exists(old_full_path):
            return result

        # Get new folder path (ID based)
        new_folder_path = person.get_attachment_folder_path()  # people/Smith_John_42
        new_full_path = os.path.join(settings.MEDIA_ROOT, new_folder_path)

        self.stdout.write(f'Migrating: {person.name} (ID: {person.pk})')
        self.stdout.write(f'  From: {old_full_path}')
        self.stdout.write(f'  To:   {new_full_path}')

        if not dry_run:
            # Create new folder
            os.makedirs(new_full_path, exist_ok=True)
            result['folder_created'] = 1

            # Move all files (including subfolders)
            for item in Path(old_full_path).rglob('*'):
                if item.is_file():
                    # Calculate relative path within person folder
                    relative_path = item.relative_to(old_full_path)
                    new_file_path = Path(new_full_path) / relative_path

                    # Create parent directories if needed
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move file
                    shutil.move(str(item), str(new_file_path))
                    result['files_moved'] += 1

            # Update PersonAttachment records
            for attachment in person.attachments.all():
                old_file_path = attachment.file.name
                # Replace old path with new path
                new_file_path = old_file_path.replace(
                    f'person_attachments/{old_folder_path}',
                    new_folder_path
                )
                attachment.file.name = new_file_path
                attachment.save(update_fields=['file'])

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Moved {result["files_moved"]} file(s)'
            ))
        else:
            # Count files for dry run
            file_count = sum(1 for _ in Path(old_full_path).rglob('*') if _.is_file())
            self.stdout.write(f'  Would move {file_count} file(s)')

        return result

    def get_old_folder_path(self, person):
        """
        Generate old folder path format (birth year based).
        Replicates old get_attachment_folder_path() logic.
        """
        name = person.name
        if not name:
            return f'unknown_person_{person.pk}'

        parts = []
        if name.last_name:
            parts.append(name.last_name.lower())
        if name.middle_name:
            parts.append(name.middle_name.lower())
        if name.first_name:
            parts.append(name.first_name.lower())

        if not parts:
            return f'unknown_person_{person.pk}'

        folder_name = '_'.join(parts)

        # Add birth year if available
        birth = person.birth
        if birth and birth.date:
            folder_name += f'_{birth.date.year}'

        # Slugify
        from django.utils.text import slugify
        return slugify(folder_name)

    def delete_old_folders(self, old_base):
        """Delete old person_attachments folder after migration"""
        if os.path.exists(old_base):
            shutil.rmtree(old_base)
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {old_base}'))
```

**Usage:**
```bash
# Preview what will happen
python manage.py migrate_attachment_folders --dry-run

# Run migration
python manage.py migrate_attachment_folders

# Run migration and delete old folders
python manage.py migrate_attachment_folders --delete-old
```

**Safety features:**
- Dry run mode to preview changes
- Preserves subfolder structure
- Updates database FileField paths
- Error handling per person (one failure doesn't stop migration)
- Summary statistics at end
- Optional deletion of old folders (requires explicit flag)

---

### Phase 7: Admin Interface Enhancements

**File:** `templates/admin/person/person/change_form.html`

#### Add Folder Path Display

**Location:** After existing attachments section (around line 60)

```html
<!-- Folder Path Info -->
<div class="folder-info" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #007cba; border-radius: 4px;">
    <h3 style="margin-top: 0;">📁 Media Folder</h3>
    <div style="display: flex; align-items: center; gap: 10px;">
        <code style="padding: 8px 12px; background: white; border: 1px solid #ddd; border-radius: 4px; flex: 1;">
            {{ original.get_attachment_folder_path }}
        </code>
        <button type="button"
                onclick="navigator.clipboard.writeText('{{ original.get_attachment_folder_path }}')"
                style="padding: 8px 16px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer;">
            📋 Copy Path
        </button>
    </div>
    <p style="margin: 10px 0 0; color: #666; font-size: 13px;">
        Files placed in this folder will be automatically detected and added to this person.
        Subfolders are supported.
    </p>
</div>

<!-- Sync Status -->
<div class="sync-controls" style="margin: 20px 0;">
    <button type="button"
            onclick="syncAttachmentsNow()"
            style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
        🔄 Sync Folder Now
    </button>
    <span id="sync-status" style="margin-left: 15px; color: #666;"></span>
</div>

<script>
function syncAttachmentsNow() {
    const statusEl = document.getElementById('sync-status');
    statusEl.textContent = 'Syncing...';
    statusEl.style.color = '#007cba';

    fetch(`/admin/person/person/{{ original.pk }}/sync/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.files_created > 0) {
            statusEl.textContent = `✓ Created ${data.files_created} new attachment(s)`;
            statusEl.style.color = '#28a745';
            // Reload page to show new attachments
            setTimeout(() => location.reload(), 1500);
        } else {
            statusEl.textContent = `✓ All files already synced (${data.files_existing} file(s))`;
            statusEl.style.color = '#28a745';
        }
    })
    .catch(error => {
        statusEl.textContent = '✗ Sync failed';
        statusEl.style.color = '#dc3545';
        console.error('Sync error:', error);
    });
}
</script>
```

#### Add Source Indicator for Attachments

**Location:** In existing attachments display (around line 30)

```html
<div class="attachment-card" style="...">
    <!-- ... existing content ... -->

    {% if attachment.description and 'Auto-detected' in attachment.description %}
        <span class="source-badge" style="display: inline-block; padding: 2px 8px; background: #ffc107; color: #000; border-radius: 3px; font-size: 11px; margin-top: 5px;">
            🤖 Auto-detected
        </span>
    {% else %}
        <span class="source-badge" style="display: inline-block; padding: 2px 8px; background: #007cba; color: white; border-radius: 3px; font-size: 11px; margin-top: 5px;">
            📤 Uploaded
        </span>
    {% endif %}
</div>
```

---

### Phase 8: Admin URL for Sync Endpoint

**File:** `person/admin.py`

#### Add Custom URL

**Location:** In `PersonAdmin` class

```python
from django.urls import path
from django.http import JsonResponse

class PersonAdmin(admin.ModelAdmin):
    # ... existing code ...

    def get_urls(self):
        """Add custom admin URLs"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/sync/',
                self.admin_site.admin_view(self.sync_attachments_view),
                name='person_person_sync',
            ),
        ]
        return custom_urls + urls

    def sync_attachments_view(self, request, pk):
        """AJAX endpoint to sync attachments for a person"""
        from .utils import sync_person_attachments

        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)

        try:
            person = Person.objects.get(pk=pk)
            stats = sync_person_attachments(person)

            return JsonResponse({
                'success': True,
                'files_created': stats['files_created'],
                'files_existing': stats['files_existing'],
                'files_found': stats['files_found'],
            })

        except Person.DoesNotExist:
            return JsonResponse({'error': 'Person not found'}, status=404)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
```

---

### Phase 9: Update Settings

**File:** `djtree/settings.py`

#### Add Media Configuration

```python
# Media files (Lines 140-141, update if needed)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Attachment sync settings (new)
DISABLE_STARTUP_SYNC = os.environ.get('DISABLE_STARTUP_SYNC', 'false').lower() == 'true'
```

#### Add to .gitignore

**File:** `.gitignore`

```
# Media files
media/people/
media/person_attachments/  # Old structure (can remove after migration)
```

---

## Testing Strategy

### Unit Tests

**File:** `person/tests.py`

```python
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from person.models import Person, PersonAttachment, Name
from person.utils import sync_person_attachments, detect_file_type
import os
from django.conf import settings


class PersonAttachmentFolderTests(TestCase):

    def setUp(self):
        """Create test person"""
        name = Name.objects.create(
            first_name='John',
            last_name='Smith'
        )
        self.person = Person.objects.create(gender='M')
        self.person.names.add(name)

    def test_folder_path_format(self):
        """Test new folder path format includes ID"""
        expected = f'people/Smith_John_{self.person.pk}'
        self.assertEqual(self.person.get_attachment_folder_path(), expected)

    def test_folder_path_no_name(self):
        """Test folder path when person has no name"""
        person = Person.objects.create(gender='U')
        expected = f'people/Unknown_Person_{person.pk}'
        self.assertEqual(person.get_attachment_folder_path(), expected)

    def test_file_type_detection(self):
        """Test file type auto-detection"""
        self.assertEqual(detect_file_type('photo.jpg'), 'photo')
        self.assertEqual(detect_file_type('document.pdf'), 'document')
        self.assertEqual(detect_file_type('video.mp4'), 'video')
        self.assertEqual(detect_file_type('unknown.xyz'), 'document')

    def test_sync_creates_missing_attachments(self):
        """Test that sync creates attachments for orphaned files"""
        # Create test file in person's folder
        folder_path = self.person.get_attachment_folder_path()
        full_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        os.makedirs(full_path, exist_ok=True)

        test_file = os.path.join(full_path, 'test.pdf')
        with open(test_file, 'w') as f:
            f.write('test content')

        # Run sync
        stats = sync_person_attachments(self.person)

        # Verify attachment created
        self.assertEqual(stats['files_created'], 1)
        self.assertTrue(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='test.pdf'
            ).exists()
        )

        # Cleanup
        os.remove(test_file)

    def test_sync_ignores_existing_attachments(self):
        """Test that sync doesn't duplicate existing records"""
        # Create attachment
        attachment = PersonAttachment.objects.create(
            person=self.person,
            file='people/Smith_John_1/existing.pdf',
            original_filename='existing.pdf'
        )

        # Run sync (file already tracked)
        stats = sync_person_attachments(self.person)

        # Verify no duplicates
        self.assertEqual(stats['files_created'], 0)
        self.assertEqual(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='existing.pdf'
            ).count(),
            1
        )

    def test_sync_with_subfolders(self):
        """Test that sync handles subfolders"""
        folder_path = self.person.get_attachment_folder_path()
        full_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        os.makedirs(os.path.join(full_path, 'photos'), exist_ok=True)

        test_file = os.path.join(full_path, 'photos', 'portrait.jpg')
        with open(test_file, 'w') as f:
            f.write('test')

        stats = sync_person_attachments(self.person, recursive=True)

        self.assertEqual(stats['files_created'], 1)
        self.assertTrue(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='portrait.jpg',
                file_type='photo'
            ).exists()
        )

        # Cleanup
        os.remove(test_file)
```

### Integration Tests

**Manual testing checklist:**

1. **Folder creation:**
   - [ ] Create new person
   - [ ] Verify folder created at `media/people/Lastname_Firstname_ID/`
   - [ ] Upload file via admin
   - [ ] Verify file appears in correct folder

2. **Manual file placement:**
   - [ ] Manually place PDF in person's folder
   - [ ] Run `python manage.py sync_attachments --person-id X`
   - [ ] Verify PersonAttachment created
   - [ ] Verify file_type auto-detected correctly

3. **Subfolder support:**
   - [ ] Create subfolder `photos/` in person's folder
   - [ ] Place image in subfolder
   - [ ] Run sync
   - [ ] Verify attachment created with correct path

4. **Admin action:**
   - [ ] Select multiple persons in admin list
   - [ ] Run "Sync media folders" action
   - [ ] Verify success message shows statistics

5. **Server startup sync:**
   - [ ] Place files in multiple person folders
   - [ ] Restart Django server
   - [ ] Check logs for sync completion message
   - [ ] Verify attachments created

6. **Migration:**
   - [ ] Run `migrate_attachment_folders --dry-run`
   - [ ] Verify output shows correct old -> new paths
   - [ ] Run actual migration
   - [ ] Verify files moved to new structure
   - [ ] Verify PersonAttachment paths updated
   - [ ] Verify old files accessible via admin

---

## Implementation Timeline

### Week 1: Core Functionality
**Days 1-2:**
- ✅ Phase 1: Update `get_attachment_folder_path()` to use ID format
- ✅ Phase 2: Create `person/utils.py` with sync functions
- ✅ Phase 7 (partial): Add file type detection

**Days 3-4:**
- ✅ Phase 3: Create `sync_attachments` management command
- ✅ Write unit tests for sync functionality
- ✅ Manual testing: file placement and sync

**Day 5:**
- ✅ Phase 4: Add auto-sync on server startup in `apps.py`
- ✅ Test startup sync behavior

### Week 2: Admin & Migration
**Days 6-7:**
- ✅ Phase 5: Add admin action for bulk sync
- ✅ Phase 8: Add custom admin sync endpoint
- ✅ Phase 7 (complete): Admin UI enhancements (folder path, sync button)

**Days 8-9:**
- ✅ Phase 6: Create migration command
- ✅ Test migration with dry-run
- ✅ Run actual migration on copy of production data

**Day 10:**
- ✅ Integration testing
- ✅ Documentation
- ✅ Code review

### Week 3: Production Deployment
**Day 11:**
- ✅ Create backup of media files
- ✅ Run migration on production (with `--dry-run` first)
- ✅ Verify all files migrated successfully

**Day 12:**
- ✅ Monitor startup sync performance
- ✅ Test manual file placement workflow
- ✅ Train users on new folder structure

**Day 13:**
- ✅ Clean up old folders (if migration successful)
- ✅ Final testing and verification

---

## Deployment Checklist

### Pre-Deployment
- [ ] Backup entire `media/` directory
- [ ] Export database (especially PersonAttachment table)
- [ ] Test migration on copy of production data
- [ ] Review all code changes
- [ ] Update documentation

### Deployment Steps
1. [ ] Deploy code changes
2. [ ] Run migrations (if any database schema changes)
3. [ ] Run `python manage.py migrate_attachment_folders --dry-run`
4. [ ] Review dry-run output
5. [ ] Run `python manage.py migrate_attachment_folders`
6. [ ] Verify files moved successfully
7. [ ] Run `python manage.py sync_attachments --all`
8. [ ] Restart Django server (triggers startup sync)
9. [ ] Check logs for errors

### Post-Deployment
- [ ] Test file uploads via admin
- [ ] Test manual file placement and sync
- [ ] Verify existing attachments accessible
- [ ] Monitor server startup time (ensure sync doesn't slow down)
- [ ] Train users on new workflow

### Rollback Plan
If issues occur:
1. [ ] Revert code changes
2. [ ] Restore media files from backup
3. [ ] Restore database from backup
4. [ ] Restart server

---

## Performance Considerations

### Startup Sync Optimization
- **Current approach:** Sync all persons on every startup
- **Concern:** May slow down server startup with many persons/files
- **Solutions:**
  1. Add caching: Track last sync time per person, skip if recent
  2. Add timeout: Limit startup sync to X seconds
  3. Make async: Use background task queue (Celery)
  4. Add flag: `DISABLE_STARTUP_SYNC=1` for development

### Database Queries
- **N+1 queries:** Sync iterates through all persons
- **Solution:** Use `select_related('names')` when querying persons
- **File existence checks:** Each file checked against database
- **Solution:** Bulk fetch all attachment paths upfront

### File System Operations
- **Recursive directory traversal:** Can be slow for large folders
- **Solution:** Add depth limit option
- **File metadata reads:** `stat()` called for each file
- **Solution:** Batch file operations where possible

---

## Security Considerations

### Path Traversal Prevention
```python
def sync_person_attachments(person):
    folder_path = person.get_attachment_folder_path()
    full_path = os.path.join(settings.MEDIA_ROOT, folder_path)

    # Verify path is within MEDIA_ROOT
    if not full_path.startswith(settings.MEDIA_ROOT):
        raise ValueError('Invalid folder path')
```

### File Name Sanitization
```python
def should_skip_file(filename):
    # Skip malicious patterns
    dangerous_patterns = ['..', '/', '\\', '\0']
    return any(pattern in filename for pattern in dangerous_patterns)
```

### Permissions
- Ensure media folders have correct permissions (readable by web server)
- Don't expose full filesystem paths to users
- Validate file types before creating attachments

---

## Future Enhancements

### Phase 10+ (Optional)
1. **Thumbnail generation** for photos
2. **File metadata extraction** (EXIF, PDF metadata)
3. **Duplicate detection** (content-based hashing)
4. **File versioning** (track changes to same filename)
5. **Bulk rename utility** (rename files in folder)
6. **REST API endpoints** for file access
7. **File organization** (auto-categorize into subfolders)
8. **Search indexing** (full-text search of documents)
9. **Virus scanning** for auto-detected files
10. **Audit logging** (track who added/deleted files)

---

## File Structure Summary

```
person/
├── models.py (modified)
│   └── get_attachment_folder_path() - Returns people/Lastname_Firstname_42
├── utils.py (NEW)
│   ├── sync_person_attachments(person, recursive=True)
│   ├── sync_all_persons(verbose=False)
│   ├── detect_file_type(filename)
│   └── should_skip_file(filename)
├── apps.py (modified)
│   └── ready() - Auto-sync on server startup
├── admin.py (modified)
│   ├── sync_selected_attachments() - Admin action
│   ├── get_urls() - Custom sync endpoint
│   └── sync_attachments_view() - AJAX sync handler
├── management/commands/
│   ├── sync_attachments.py (NEW)
│   └── migrate_attachment_folders.py (NEW)
└── tests.py (modified)
    └── PersonAttachmentFolderTests

templates/admin/person/person/
└── change_form.html (modified)
    ├── Folder path display with copy button
    ├── Sync now button with AJAX
    └── Source badges (uploaded vs auto-detected)

media/
├── people/ (NEW)
│   ├── Smith_John_42/
│   │   ├── birth_certificate.pdf
│   │   ├── photos/
│   │   │   └── portrait.jpg
│   │   └── documents/
│   │       └── immigration.pdf
│   └── Doe_Jane_108/
└── person_attachments/ (OLD - to be removed after migration)
```

---

## Configuration Summary

### Settings (djtree/settings.py)
```python
# Media configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Optional: Disable startup sync
DISABLE_STARTUP_SYNC = os.environ.get('DISABLE_STARTUP_SYNC', 'false').lower() == 'true'
```

### Environment Variables
```bash
# Disable startup sync (optional, for development)
export DISABLE_STARTUP_SYNC=true
```

### Commands
```bash
# Sync all persons
python manage.py sync_attachments

# Sync specific person
python manage.py sync_attachments --person-id 42

# Migrate folders (one-time)
python manage.py migrate_attachment_folders --dry-run
python manage.py migrate_attachment_folders
python manage.py migrate_attachment_folders --delete-old
```

---

## Success Criteria

Implementation is complete when:

- ✅ All new uploads go to `media/people/Lastname_Firstname_ID/`
- ✅ Manually placed files are auto-detected on startup
- ✅ Management command syncs files on demand
- ✅ Admin action syncs selected persons
- ✅ Subfolders are supported and traversed
- ✅ File types are auto-detected from extensions
- ✅ All existing files migrated from old structure
- ✅ PersonAttachment database records updated with new paths
- ✅ Admin UI shows folder path and sync button
- ✅ No breaking changes to existing functionality
- ✅ All tests passing
- ✅ Documentation complete

---

## Questions & Decisions Log

### Decided
1. **Folder format:** `media/people/Lastname_Firstname_42/` ✅
2. **Auto-sync:** Server startup + management command ✅
3. **Subfolders:** Allowed with recursive traversal ✅
4. **Migration:** Immediate one-time migration ✅
5. **Conflicts:** Not expected (unique person IDs) ✅

### Open Questions
1. **Startup sync performance:** Monitor and optimize if needed
2. **Async processing:** Consider Celery if sync becomes slow
3. **API integration:** Add REST endpoints for file access?
4. **Thumbnail generation:** Auto-generate for photos?
5. **File validation:** Add size/type restrictions?

---

## References

### Existing Code
- Person model: `person/models.py:9-114`
- PersonAttachment model: `person/models.py:117-142`
- Current folder path: `person/models.py:78-102`
- Admin upload handling: `person/admin.py:373-438`
- Admin template: `templates/admin/person/person/change_form.html`

### Django Documentation
- File uploads: https://docs.djangoproject.com/en/5.1/topics/http/file-uploads/
- Management commands: https://docs.djangoproject.com/en/5.1/howto/custom-management-commands/
- Admin actions: https://docs.djangoproject.com/en/5.1/ref/contrib/admin/actions/

---

**Last Updated:** 2025-10-26
**Status:** Plan Complete - Ready for Implementation
