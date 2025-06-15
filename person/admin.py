from django.contrib import admin
from .models import Person, Name, PersonName

class PersonNameInline(admin.TabularInline):
    model = PersonName
    extra = 1

class PersonAdmin(admin.ModelAdmin):
    inlines = [PersonNameInline]

class NameAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return a dict of all perms for this model. This dict has the keys
        add, change, delete, and view mapping to the True/False for each of those actions.
        """
        return {}

admin.site.register(Person, PersonAdmin)
admin.site.register(Name, NameAdmin)

