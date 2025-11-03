"""Test suite for person media folder synchronisation."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from person.models import Name, Person, PersonAttachment
from person.utils import detect_file_type, sync_person_attachments


class PersonAttachmentFolderTests(TestCase):
    def setUp(self):
        self.temp_media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.temp_media_dir)
        self.override.enable()

        name = Name.objects.create(first_name='John', last_name='Smith')
        self.person = Person.objects.create(gender='M')
        self.person.names.add(name)

        self.addCleanup(self.override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media_dir, ignore_errors=True))

    def _person_folder(self) -> Path:
        return Path(settings.MEDIA_ROOT) / self.person.get_attachment_folder_path()

    def test_folder_path_format(self):
        expected = f'people/Smith_John_{self.person.pk}'
        self.assertEqual(self.person.get_attachment_folder_path(), expected)

    def test_folder_path_no_name(self):
        person = Person.objects.create(gender='U')
        expected = f'people/Unknown_Person_{person.pk}'
        self.assertEqual(person.get_attachment_folder_path(), expected)

    def test_file_type_detection(self):
        self.assertEqual(detect_file_type('photo.jpg'), 'photo')
        self.assertEqual(detect_file_type('document.pdf'), 'document')
        self.assertEqual(detect_file_type('video.mp4'), 'video')
        self.assertEqual(detect_file_type('unknown.xyz'), 'document')

    def test_sync_creates_missing_attachments(self):
        folder_path = self._person_folder()
        folder_path.mkdir(parents=True, exist_ok=True)

        test_file = folder_path / 'test.pdf'
        test_file.write_text('test content')

        stats = sync_person_attachments(self.person)

        self.assertEqual(stats['files_created'], 1)
        self.assertTrue(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='test.pdf',
            ).exists()
        )

    def test_sync_ignores_existing_attachments(self):
        folder_path = self._person_folder()
        folder_path.mkdir(parents=True, exist_ok=True)

        existing_path = folder_path / 'existing.pdf'
        existing_path.write_text('existing content')

        PersonAttachment.objects.create(
            person=self.person,
            file=f'people/Smith_John_{self.person.pk}/existing.pdf',
            original_filename='existing.pdf',
        )

        stats = sync_person_attachments(self.person)

        self.assertEqual(stats['files_created'], 0)
        self.assertEqual(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='existing.pdf',
            ).count(),
            1,
        )

    def test_sync_with_subfolders(self):
        folder_path = self._person_folder()
        photos_folder = folder_path / 'photos'
        photos_folder.mkdir(parents=True, exist_ok=True)

        photo_path = photos_folder / 'portrait.jpg'
        photo_path.write_text('photo data')

        stats = sync_person_attachments(self.person, recursive=True)

        self.assertEqual(stats['files_created'], 1)
        self.assertTrue(
            PersonAttachment.objects.filter(
                person=self.person,
                original_filename='portrait.jpg',
                file_type='photo',
            ).exists()
        )
