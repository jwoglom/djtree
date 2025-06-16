from django.contrib import admin
from django import forms
from django.contrib.admin import SimpleListFilter
from .models import (
    Person, Name, PersonName,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, ParentChildRelationship
)
from django.urls import reverse
from django.utils.html import format_html

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
    ]
    list_display = ('get_first_name', 'get_middle_name', 'get_last_name', 'gender', 'is_living', 'get_birth_date', 'get_death_date')
    list_display_links = ('get_first_name', 'get_middle_name', 'get_last_name')
    list_filter = ('gender', 'is_living', LastNameFilter)
    search_fields = ('names__first_name', 'names__middle_name', 'names__last_name')
    ordering_fields = ('birthevents__date', 'deathevents__date')
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

