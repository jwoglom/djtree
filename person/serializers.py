from rest_framework import routers, serializers, viewsets
from .models import (
    Person, Name, PersonName,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, ParentChildRelationship
)

router = routers.DefaultRouter()

class NameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Name
        fields = ['id', 'first_name', 'middle_name', 'last_name']

class PersonNameSerializer(serializers.ModelSerializer):
    name__first_name = serializers.CharField(source='name.first_name')
    name__middle_name = serializers.CharField(source='name.middle_name')
    name__last_name = serializers.CharField(source='name.last_name')
    
    class Meta:
        model = PersonName
        fields = ['id', 'name__first_name', 'name__middle_name', 'name__last_name', 'name_type']

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        fields = ['id', 'date', 'comment']

class BirthEventSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        model = BirthEvent
        fields = EventSerializer.Meta.fields + ['location']

class DeathEventSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        model = DeathEvent
        fields = EventSerializer.Meta.fields + ['location', 'cause']

class CoupleEventSerializer(EventSerializer):
    other_person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())
    
    class Meta(EventSerializer.Meta):
        abstract = True
        fields = EventSerializer.Meta.fields + ['other_person', 'location']

class MarriageEventSerializer(CoupleEventSerializer):
    class Meta(CoupleEventSerializer.Meta):
        model = MarriageEvent
        fields = CoupleEventSerializer.Meta.fields + ['ended']

class DivorceEventSerializer(CoupleEventSerializer):
    class Meta(CoupleEventSerializer.Meta):
        model = DivorceEvent

class ImmigrationEventSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        model = ImmigrationEvent
        fields = EventSerializer.Meta.fields + ['from_country', 'to_country', 'location']

class CitizenshipEventSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        model = CitizenshipEvent
        fields = EventSerializer.Meta.fields + ['country', 'location']

class ParentChildRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentChildRelationship
        fields = ['id', 'parent', 'child']

class PersonSerializer(serializers.ModelSerializer):
    names = PersonNameSerializer(many=True, read_only=True)
    birth = BirthEventSerializer(read_only=True)
    death = DeathEventSerializer(read_only=True)
    marriages = MarriageEventSerializer(many=True, read_only=True)
    divorces = DivorceEventSerializer(many=True, read_only=True)
    immigrations = ImmigrationEventSerializer(many=True, read_only=True)
    citizenships = CitizenshipEventSerializer(many=True, read_only=True)
    parents = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    children = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Person
        fields = [
            'id', 'names', 'gender', 'is_living',
            'birth', 'death',
            'marriages', 'divorces',
            'immigrations', 'citizenships',
            'parents', 'children'
        ]

class PersonViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows people to be viewed or edited.
    """
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    search_fields = ['names__first_name', 'names__last_name']
    filterset_fields = ['gender', 'is_living']
    ordering_fields = ['names__last_name', 'names__first_name']
    ordering = ['names__last_name', 'names__first_name']

router.register(r'people', PersonViewSet)