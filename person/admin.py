from django.contrib import admin
from django import forms
from .models import (
    Person, Name, PersonName,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, ParentChildRelationship
)

class EventForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}),
        required=False
    )

class PersonNameForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100)
    name_type = forms.ChoiceField(choices=PersonName.Type.choices, required=False)

    class Meta:
        model = PersonName
        fields = ('first_name', 'middle_name', 'last_name', 'name_type')

    def save(self, commit=True):
        # Create the Name object first
        name = Name.objects.create(
            first_name=self.cleaned_data['first_name'],
            middle_name=self.cleaned_data['middle_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Then create the PersonName relationship
        instance = super().save(commit=False)
        instance.name = name
        if commit:
            instance.save()
        return instance

class PersonNameInline(admin.TabularInline):
    model = PersonName
    form = PersonNameForm
    extra = 1
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
    ]
    list_display = ('__str__',)
    search_fields = ('names__first_name', 'names__last_name')
    fields = ('gender',)

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

