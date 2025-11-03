from django.shortcuts import render
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage
from pathlib import Path
import mimetypes
import re
import os
from .models import Person, PersonAttachment

# Create your views here.

def person_media_view(request, path=''):
    """
    Serve person media files or show directory listing.
    If the path points to a file, serve it.
    If the path points to a directory, show a directory listing.
    """
    # Construct the full path
    media_root = Path(settings.MEDIA_ROOT)
    full_path = media_root / 'people' / path

    # Security: ensure the path is within the media root
    try:
        full_path = full_path.resolve()
        if not str(full_path).startswith(str(media_root.resolve())):
            raise Http404("Invalid path")
    except (ValueError, RuntimeError):
        raise Http404("Invalid path")

    # Check if path exists
    if not full_path.exists():
        raise Http404("Path does not exist")

    # If it's a file, serve it
    if full_path.is_file():
        content_type, _ = mimetypes.guess_type(str(full_path))
        response = FileResponse(open(full_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{full_path.name}"'
        return response

    # If it's a directory, show directory listing
    if full_path.is_dir():
        items = []

        # Add parent directory link if not at root
        if path:
            parent_path = str(Path(path).parent)
            if parent_path == '.':
                parent_path = ''
            items.append({
                'name': '..',
                'path': f'/media/people/{parent_path}',
                'is_dir': True,
                'size': None,
            })

        # List directory contents
        for item in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            relative_path = item.relative_to(media_root / 'people')
            items.append({
                'name': item.name,
                'path': f'/media/people/{relative_path}',
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if item.is_file() else None,
            })

        # Get person name from path
        person_folder = path.split('/')[0] if path else 'Root'

        # Try to extract person ID from folder name and fetch person data
        person = None
        person_id = None
        if person_folder and person_folder != 'Root':
            # Extract ID from folder name (format: Lastname_Firstname_ID)
            match = re.search(r'_(\d+)$', person_folder)
            if match:
                person_id = int(match.group(1))
                try:
                    person = Person.objects.get(pk=person_id)
                except Person.DoesNotExist:
                    pass

        # Build breadcrumb parts
        breadcrumb_parts = []
        if path:
            parts = path.split('/')
            for i, part in enumerate(parts):
                breadcrumb_parts.append({
                    'name': part,
                    'path': '/media/people/' + '/'.join(parts[:i+1])
                })

        context = {
            'items': items,
            'current_path': path,
            'person_folder': person_folder,
            'breadcrumb_parts': breadcrumb_parts,
            'person': person,
            'person_id': person_id,
        }
        return render(request, 'person_media_index.html', context)

    raise Http404("Invalid path type")


@require_http_methods(["POST"])
def upload_person_media(request, person_id):
    """
    Handle file uploads for a person's media folder.
    Requires staff authentication.
    """
    # Check if user is authenticated and is staff
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Authentication required'}, status=403)

    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        return JsonResponse({'error': 'Person not found'}, status=404)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['file']

    # Create the PersonAttachment
    attachment = PersonAttachment(
        person=person,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        description=request.POST.get('description', ''),
    )
    attachment.save()

    return JsonResponse({
        'success': True,
        'filename': uploaded_file.name,
        'url': attachment.file.url,
    })
