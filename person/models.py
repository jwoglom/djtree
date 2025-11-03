from django.db import models
from django.core.exceptions import ValidationError
import os
import posixpath

# Create your models here.
class Person(models.Model):
    class Gender(models.TextChoices):
        UNKNOWN = 'U', 'Unknown'
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    names = models.ManyToManyField('Name', through='PersonName')
    children = models.ManyToManyField('self', through='ParentChildRelationship',
                                   symmetrical=False,
                                   related_name='parents')
    gender = models.CharField(max_length=1, choices=Gender, default=Gender.UNKNOWN)
    is_living = models.BooleanField(default=True)

    @property
    def name(self):
        return self.names.first()
    
    @property
    def birth(self):
        return self.birthevents.first()
    
    @property
    def death(self):
        return self.deathevents.first()

    @property
    def siblings(self):
        """Get all siblings (people who share at least one parent)"""
        # Get all parent IDs for this person using the many-to-many relationship
        parent_ids = self.parents.values_list('id', flat=True)
        
        # Find all people who have any of these parents (excluding self)
        siblings = Person.objects.filter(
            parents__id__in=parent_ids
        ).exclude(id=self.id).distinct()
        
        return siblings

    @property
    def spouses(self):
        """Get current and former spouses"""
        return Person.objects.filter(
            models.Q(marriageevents__person=self) |
            models.Q(marriageevents__other_person=self)
        ).distinct()

    @property
    def spouse(self):
        """Get the current spouse of this person (returns the other person, not self)"""
        marriage = self.marriageevents.filter(ended=False).first()
        if marriage:
            return marriage.other_person
        marriage = self.marriageevents_as_partner.filter(ended=False).first()
        if marriage:
            return marriage.person
        return None
    
    @property
    def events(self):
        """Get all events for this person"""
        return [
            *self.birthevents.all(),
            *self.deathevents.all(),
            *self.marriageevents.all(),
            *self.divorceevents.all(),
            *self.immigrationevents.all(),
            *self.citizenshipevents.all()
        ]

    def get_attachment_folder_path(self):
        """Generate folder path in the format people/Lastname_Firstname_ID."""
        if not self.pk:
            return "people/Unknown_Person_unsaved"

        name = self.name
        if name:
            parts = []
            if name.last_name:
                parts.append(name.last_name.capitalize())
            if name.first_name:
                parts.append(name.first_name.capitalize())

            if parts:
                folder_name = "_".join(parts) + f"_{self.pk}"
            else:
                folder_name = f"Unknown_Person_{self.pk}"
        else:
            folder_name = f"Unknown_Person_{self.pk}"

        return f"people/{folder_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.death and self.is_living:
            self.is_living = False
            self.save(update_fields=['is_living'])

    def __str__(self):
        birth_to_death = f" ({self.birth.date} - {f'{self.death.date}' if self.death else 'present'})" if self.birth else ""
        return f"{self.name}{birth_to_death}"


# File Attachments
class PersonAttachment(models.Model):
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='person_attachments/')
    original_filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=50, blank=True)  # e.g., 'document', 'photo', 'certificate'
    
    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "name"):
            filename = os.path.basename(self.file.name)
            if not self.original_filename:
                self.original_filename = filename

            if self.person:
                folder_path = self.person.get_attachment_folder_path()
                normalized_name = self.file.name.replace('\\', '/')
                prefix = f"{folder_path}/"
                if normalized_name.startswith(prefix):
                    relative_path = normalized_name
                else:
                    relative_path = posixpath.join(folder_path, filename)

                if self.file.name != relative_path:
                    self.file.name = relative_path

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.original_filename} - {self.person}"
    
    class Meta:
        ordering = ['-uploaded_at']


# Names
class Name(models.Model):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name}{f' {self.middle_name}' if self.middle_name else ''} {self.last_name}"

class PersonName(models.Model):
    person = models.ForeignKey('Person', on_delete=models.CASCADE)
    name = models.ForeignKey('Name', on_delete=models.CASCADE)
    class Type(models.TextChoices):
        BIRTH = "born as"
        MARRIAGE = "married as"
        IMMIGRATION = "immigrated as"
        OTHER = "other"
    name_type = models.CharField(max_length=100, choices=Type, default=Type.BIRTH, blank=True)

    def __str__(self):
        return f"{self.name}{f' ({self.name_type})' if self.name_type else ''}"

# Relationships
class ParentChildRelationship(models.Model):
    parent = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='parent_relationships')
    child = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='child_relationships')
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'child'],
                name='unique_parent_child'
            )
        ]

    def clean(self):
        # Prevent self-relationships
        if self.parent == self.child:
            raise ValidationError("A person cannot be their own parent")
        
        # Only perform these checks if both parent and child are saved
        if self.parent.pk and self.child.pk:
            # Prevent duplicate parent relationships
            if ParentChildRelationship.objects.filter(
                parent=self.parent,
                child=self.child
            ).exclude(id=self.id).exists():
                raise ValidationError("This parent-child relationship already exists")
            
            # Prevent impossible relationships
            if self.parent in self.child.siblings:
                raise ValidationError("A person cannot be both a parent and a sibling")
            
            # Prevent marrying your own child
            if self.parent in self.child.spouses:
                raise ValidationError("A person cannot be both a parent and a spouse")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Ensure the many-to-many relationships are consistent
        if is_new:
            # Add to many-to-many relationships if they don't exist
            if self.child not in self.parent.children.all():
                self.parent.children.add(self.child)
            if self.parent not in self.child.parents.all():
                self.child.parents.add(self.parent)

    def __str__(self):
        return f"{self.parent} is parent of {self.child}"

# Events
class Event(models.Model):
    date = models.DateField(blank=True, null=True)
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='%(class)ss')
    comment = models.TextField(blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__.replace('Event', '')} event for {self.person} on {self.date}"

class CoupleEvent(Event):
    other_person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='%(class)ss_as_partner')
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        # Prevent self-relationships
        if self.person == self.other_person:
            raise ValidationError("A person cannot have a relationship with themselves")
        
        # Only perform these checks if both persons are saved
        if self.person.pk and self.other_person.pk:
            # Prevent marrying your own child
            if self.other_person in self.person.children.all():
                raise ValidationError("A person cannot marry their own child")
            
            # Prevent marrying your own parent
            if self.other_person in self.person.parents.all():
                raise ValidationError("A person cannot marry their own parent")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        # Block recursion
        skip_symmetric = kwargs.pop('skip_symmetric', False)
        
        super().save(*args, **kwargs)
        
        if not skip_symmetric:
            # Find or create the symmetric event
            symmetric_event, created = self.__class__.objects.get_or_create(
                person=self.other_person,
                other_person=self.person,
                date=self.date,
                defaults={
                    'location': self.location,
                    'comment': self.comment
                }
            )

            # If this is an update (not new) and the symmetric event exists,
            # update its fields to match this one
            if not is_new and not created:
                symmetric_event.location = self.location
                symmetric_event.comment = self.comment
                symmetric_event.date = self.date
                symmetric_event.save(update_fields=['location', 'comment', 'date'], skip_symmetric=True)

class MarriageEvent(CoupleEvent):
    ended = models.BooleanField(default=False)  # Track if this marriage ended in divorce

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['person', 'other_person', 'date'],
                name='unique_marriage_per_couple_date'
            )
        ]

class DivorceEvent(CoupleEvent):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['person', 'other_person', 'date'],
                name='unique_divorce_per_couple_date'
            )
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        MarriageEvent.objects.filter(
            person=self.person,
            other_person=self.other_person,
            ended=False
        ).update(ended=True)

        MarriageEvent.objects.filter(
            person=self.other_person,
            other_person=self.person,
            ended=False
        ).update(ended=True)

class BirthEvent(Event):
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['person'],
                name='unique_birth_per_person'
            )
        ]

class DeathEvent(Event):
    location = models.CharField(max_length=200, blank=True)
    cause = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['person'],
                name='unique_death_per_person'
            )
        ]
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.person.is_living:
            self.person.is_living = False
            self.person.save(update_fields=['is_living'])

class ImmigrationEvent(Event):
    from_country = models.CharField(max_length=100)
    to_country = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)

class CitizenshipEvent(Event):
    country = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)

