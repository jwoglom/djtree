from django.db import models

# Create your models here.
class Person(models.Model):
    names = models.ManyToManyField('Name', through='PersonName')

    @property
    def name(self):
        return self.names.first()
    
    def __str__(self):
        return f"Person: {self.name}"


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
        BIRTH = "birth"
        MARRIAGE = "marriage"
        IMMIGRATION = "immigration"
    name_type = models.CharField(max_length=100, choices=Type, blank=True)

    def __str__(self):
        return f"{self.name}{f' ({self.name_type})' if self.name_type else ''}"

