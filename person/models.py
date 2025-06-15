from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
class Person(models.Model):
    names = models.ManyToManyField('Name', through='PersonName')

    @property
    def name(self):
        return self.names.first()
    
    def __str__(self):
        return f"Person: {self.name}"

# Names
class Name(models.Model):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.middle_name} {self.last_name}"

class PersonName(models.Model):
    person = models.ForeignKey('Person', on_delete=models.CASCADE)
    name = models.ForeignKey('Name', on_delete=models.CASCADE)
    class Type(models.TextChoices):
        BIRTH = "born as"
        MARRIAGE = "married as"
        IMMIGRATION = "immigrated as"
    name_type = models.CharField(max_length=100, choices=Type, blank=True)

    def __str__(self):
        return f"{self.name}{f' ({self.name_type})' if self.name_type else ''}"

# Events

class Event(models.Model):
    date = models.DateField()
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='%(class)s')
    comment = models.TextField(blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__.replace('Event', '')} event for {self.person} on {self.date}"

class CoupleEvent(Event):
    other_person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='%(class)s_as_partner')
    location = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

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

class ImmigrationEvent(Event):
    from_country = models.CharField(max_length=100)
    to_country = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)

class CitizenshipEvent(Event):
    country = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)

