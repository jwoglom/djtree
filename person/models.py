from django.db import models
from django.db.models import QuerySet
from django.core.exceptions import ValidationError

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
        parent_ids = self.parent_relationships.values_list('parent_id', flat=True)
        return Person.objects.filter(
            parent_relationships__parent_id__in=parent_ids
        ).exclude(id=self.id).distinct()

    @property
    def spouses(self):
        """Get current and former spouses"""
        return Person.objects.filter(
            models.Q(marriageevents__person=self) |
            models.Q(marriageevents__other_person=self)
        ).distinct()

    @property
    def spouse(self):
        """Get the current spouse of this person"""
        return self.spouses.filter(marriageevents__ended=False).first()
    
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


    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.death and self.is_living:
            self.is_living = False
            self.save(update_fields=['is_living'])

    def __str__(self):
        birth_to_death = f" ({self.birth.date} - {f'{self.death.date}' if self.death else 'present'})" if self.birth else ""
        return f"{self.name}{birth_to_death}"


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
        super().save(*args, **kwargs)
        
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
            symmetric_event.save(update_fields=['location', 'comment', 'date'])

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

