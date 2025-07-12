from django.contrib import admin
from django import forms
from django.contrib.admin import SimpleListFilter
from .models import (
    Person, Name, PersonName,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, ParentChildRelationship, PersonAttachment
)
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.forms import BaseInlineFormSet

class EventForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}),
        required=False
    )

class MultipleFileInput(forms.ClearableFileInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'multiple': 'multiple',
            'class': 'vLargeTextField',
            'style': 'min-height: 120px; border: 2px dashed #007cba; padding: 20px; text-align: center; background-color: #f9f9f9; cursor: pointer;',
        }
        if attrs:
            default_attrs.update(attrs)
        # Call the parent __init__ without the multiple validation
        super(forms.FileInput, self).__init__(default_attrs)
    
    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

class PersonAttachmentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Remove any validation errors from the files field
        for form in self.forms:
            if 'files' in form.errors:
                del form.errors['files']

class PersonAttachmentForm(forms.ModelForm):
    files = forms.FileField(
        widget=MultipleFileInput(),
        required=False,
        help_text="Drag and drop multiple files here or click to select files"
    )

    class Meta:
        model = PersonAttachment
        fields = ['description', 'file_type']
    
    def clean(self):
        cleaned_data = super().clean()
        print(f"DEBUG: Form clean called, files: {self.files}")
        if self.files:
            print(f"DEBUG: Available files: {list(self.files.keys())}")
        return cleaned_data

class PersonAttachmentInline(admin.TabularInline):
    model = PersonAttachment
    form = PersonAttachmentForm
    formset = PersonAttachmentFormSet
    extra = 0  # Don't show empty forms in the table
    max_num = 10  # Allow up to 10 attachments
    fields = ('file_link', 'original_filename', 'description', 'file_type', 'uploaded_at')
    readonly_fields = ('file_link', 'original_filename', 'uploaded_at')
    verbose_name = "Attachment"
    verbose_name_plural = "Attachments"
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, obj.original_filename or obj.file.name)
        return "No file"
    file_link.short_description = "File"
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra forms in the table"""
        return 0

class PersonNameForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100)
    name_type = forms.ChoiceField(choices=PersonName.Type.choices, required=False)

    class Meta:
        model = PersonName
        fields = ('first_name', 'middle_name', 'last_name', 'name_type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.name:
            self.fields['first_name'].initial = self.instance.name.first_name
            self.fields['middle_name'].initial = self.instance.name.middle_name
            self.fields['last_name'].initial = self.instance.name.last_name

    def save(self, commit=True):
        if self.instance.pk and self.instance.name:
            # Update existing name
            name = self.instance.name
            name.first_name = self.cleaned_data['first_name']
            name.middle_name = self.cleaned_data['middle_name']
            name.last_name = self.cleaned_data['last_name']
            name.save()
        else:
            # Create new name
            name = Name.objects.create(
                first_name=self.cleaned_data['first_name'],
                middle_name=self.cleaned_data['middle_name'],
                last_name=self.cleaned_data['last_name']
            )
        
        # Update the PersonName relationship
        instance = super().save(commit=False)
        instance.name = name
        if commit:
            instance.save()
        return instance

class PersonNameInline(admin.TabularInline):
    model = PersonName
    form = PersonNameForm
    extra = 0
    fields = ('first_name', 'middle_name', 'last_name', 'name_type')
    verbose_name = "Name"
    verbose_name_plural = "Names"

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['name_type'].initial = PersonName.Type.BIRTH
        return formset

class ParentChildRelationshipInline(admin.TabularInline):
    model = ParentChildRelationship
    fk_name = 'child'
    extra = 0
    fields = ('parent',)
    verbose_name = "Parent"
    verbose_name_plural = "Parents"

class ChildRelationshipInline(admin.TabularInline):
    model = ParentChildRelationship
    fk_name = 'parent'
    extra = 0
    fields = ('child',)
    verbose_name = "Child"
    verbose_name_plural = "Children"

class BirthEventInline(admin.TabularInline):
    model = BirthEvent
    form = EventForm
    extra = 0
    max_num = 1
    fields = ('date', 'location', 'comment')

class DeathEventInline(admin.TabularInline):
    model = DeathEvent
    form = EventForm
    extra = 0
    max_num = 1
    fields = ('date', 'location', 'cause', 'comment')

class MarriageEventInline(admin.TabularInline):
    model = MarriageEvent
    form = EventForm
    extra = 0
    fields = ('date', 'other_person', 'location', 'comment', 'ended')
    fk_name = 'person'

class DivorceEventInline(admin.TabularInline):
    model = DivorceEvent
    form = EventForm
    extra = 0
    fields = ('date', 'other_person', 'location', 'comment')
    fk_name = 'person'

class ImmigrationEventInline(admin.TabularInline):
    model = ImmigrationEvent
    form = EventForm
    extra = 0
    fields = ('date', 'from_country', 'to_country', 'location', 'comment')

class CitizenshipEventInline(admin.TabularInline):
    model = CitizenshipEvent
    form = EventForm
    extra = 0
    fields = ('date', 'country', 'location', 'comment')

class LastNameFilter(SimpleListFilter):
    title = 'Last Name'
    parameter_name = 'last_name'

    def lookups(self, request, model_admin):
        last_names = Name.objects.values_list('last_name', flat=True).distinct().order_by('last_name')
        return [(name, name) for name in last_names]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(names__last_name=self.value())
        return queryset

class PersonAdmin(admin.ModelAdmin):
    inlines = [
        PersonNameInline,
        ParentChildRelationshipInline,
        ChildRelationshipInline,
        BirthEventInline,
        DeathEventInline,
        MarriageEventInline,
        DivorceEventInline,
        ImmigrationEventInline,
        CitizenshipEventInline,
        # PersonAttachmentInline,  # Hidden - using custom template instead
    ]
    list_display = ('get_first_name', 'get_middle_name', 'get_last_name', 'gender', 'is_living', 'get_birth_date', 'get_death_date')
    list_display_links = ('get_first_name', 'get_middle_name', 'get_last_name')
    list_filter = ('gender', 'is_living', LastNameFilter)
    search_fields = ('names__first_name', 'names__middle_name', 'names__last_name')
    ordering_fields = ('birthevents__date', 'deathevents__date')
    ordering = ['-birthevents__date']  # Sort by birth date, newest to oldest
    fields = ('gender',)

    def get_first_name(self, obj):
        return obj.name.first_name
    get_first_name.short_description = "First Name"

    def get_middle_name(self, obj):
        return obj.name.middle_name
    get_middle_name.short_description = "Middle Name"

    def get_last_name(self, obj):
        return obj.name.last_name
    get_last_name.short_description = "Last Name"

    def get_birth_date(self, obj):
        birth = obj.birth
        return birth.date if birth else None
    get_birth_date.short_description = "Birth Date"
    get_birth_date.admin_order_field = 'birthevents__date'

    def get_death_date(self, obj):
        death = obj.death
        return death.date if death else None
    get_death_date.short_description = "Death Date"
    get_death_date.admin_order_field = 'deathevents__date'

    def save_formset(self, request, form, formset, change):
        print(f"DEBUG: PersonAdmin save_formset called for {formset.model}")
        if formset.model == PersonAttachment:
            print(f"DEBUG: Processing PersonAttachment formset")
            print(f"DEBUG: request.FILES: {request.FILES}")
            print(f"DEBUG: formset.forms: {len(formset.forms)} forms")
            
            # Handle files from the custom upload section
            new_files = request.FILES.getlist('new_attachments_files') if request.FILES else []
            new_description = request.POST.get('new_attachments_description', '')
            new_file_type = request.POST.get('new_attachments_file_type', '')
            
            if new_files:
                print(f"DEBUG: Found {len(new_files)} new files from custom upload")
                for uploaded_file in new_files:
                    print(f"DEBUG: Creating attachment for {uploaded_file.name}")
                    attachment = PersonAttachment(
                        person=form.instance,
                        file=uploaded_file,
                        original_filename=uploaded_file.name,
                        description=new_description,
                        file_type=new_file_type
                    )
                    attachment.save()
                    print(f"DEBUG: Saved attachment {attachment.id}")
            
            # Handle files from the inline formsets (existing functionality)
            for form_instance in formset.forms:
                print(f"DEBUG: Form instance: {form_instance}")
                print(f"DEBUG: Form is_valid: {form_instance.is_valid()}")
                print(f"DEBUG: Form has_changed: {form_instance.has_changed()}")
                print(f"DEBUG: Form files object: {form_instance.files}")
                if form_instance.files:
                    print(f"DEBUG: Form files: {list(form_instance.files.keys())}")
                    # Look for any field that ends with '-files' to handle multiple forms
                    files_field = None
                    for key in form_instance.files.keys():
                        if key.endswith('-files'):
                            files_field = key
                            break
                    
                    if files_field:
                        files = form_instance.files.getlist(files_field)
                        print(f"DEBUG: Found {len(files)} files in {files_field}")
                        for f in files:
                            print(f"DEBUG: File: {f.name}")
                        
                        # Create attachments for each file
                        print(f"DEBUG: About to create {len(files)} attachments")
                        for uploaded_file in files:
                            print(f"DEBUG: Creating attachment for {uploaded_file.name}")
                            attachment = PersonAttachment(
                                person=form.instance,
                                file=uploaded_file,
                                original_filename=uploaded_file.name,
                                description=form_instance.cleaned_data.get('description', ''),
                                file_type=form_instance.cleaned_data.get('file_type', '')
                            )
                            attachment.save()
                            print(f"DEBUG: Saved attachment {attachment.id}")
                    else:
                        print(f"DEBUG: No files field found in form_instance.files")
                else:
                    print(f"DEBUG: Form has no files object")
        
        super().save_formset(request, form, formset, change)

class NameAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return a dict of all perms for this model. This dict has the keys
        add, change, delete, and view mapping to the True/False for each of those actions.
        """
        return {}

# Register models
admin.site.register(Person, PersonAdmin)
admin.site.register(Name, NameAdmin)

class HiddenPersonAttachmentAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict to hide the model from admin
        """
        return {}

# Register PersonAttachment with hidden admin for URL generation
admin.site.register(PersonAttachment, HiddenPersonAttachmentAdmin)

