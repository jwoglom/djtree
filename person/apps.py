from django.apps import AppConfig


class PersonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'person'

    def ready(self):
        """Trigger attachment sync once Django starts up."""
        import logging
        import os
        import sys
        from django.conf import settings

        if getattr(settings, 'DISABLE_STARTUP_SYNC', False):
            return

        # Avoid running during management commands that shouldn't trigger sync
        if any(cmd in sys.argv for cmd in {'migrate', 'makemigrations'}):
            return

        # Django's autoreloader spawns a child process; only run in the reloaded process
        if os.environ.get('RUN_MAIN') != 'true':
            return

        self.sync_on_startup()

    def sync_on_startup(self):
        """Sync attachments for all persons with error handling."""
        import logging

        from .utils import sync_all_persons

        logger = logging.getLogger(__name__)
        logger.info('Starting attachment sync on server startup...')

        try:
            stats = sync_all_persons(verbose=False)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error('Error during startup sync: %s', exc)
        else:
            logger.info(
                'Attachment sync complete: %s new file(s), %s person(s) synced',
                stats['total_files_created'],
                stats['persons_synced'],
            )
