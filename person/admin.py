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

class PersonNameInline(admin.TabularInline):
    model = PersonName
    extra = 1

class BirthEventInline(admin.TabularInline):
    model = BirthEvent
    form = EventForm
    extra = 0
    fields = ('date', 'location', 'comment')

class DeathEventInline(admin.TabularInline):
    model = DeathEvent
    form = EventForm
    extra = 0
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

