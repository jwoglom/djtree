from rest_framework import routers, serializers, viewsets
from .models import (
    Person, Name, PersonName,
    BirthEvent, DeathEvent, MarriageEvent, DivorceEvent,
    ImmigrationEvent, CitizenshipEvent, ParentChildRelationship
)

router = routers.DefaultRouter()

class NameSerializer(serializers.ModelSerializer):
    name_type = serializers.SerializerMethodField()

    def get_name_type(self, obj):
        person_name = obj.personname_set.first()
        return person_name.name_type if person_name else None

    class Meta:
        model = Name
        serializer_related_field = PersonName
        fields = ['first_name', 'middle_name', 'last_name', 'name_type']

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

class MiniPersonSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk')
    name = serializers.SerializerMethodField()
    names = NameSerializer(many=True, read_only=True)
    gender = serializers.CharField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='person-detail', lookup_field='pk')

    def get_name(self, obj):
        name = obj.name
        return NameSerializer(name).data if name else None

    class Meta:
        model = Person
        fields = ['id', 'name', 'names', 'gender', 'url']

class CoupleEventSerializer(EventSerializer):
    other_person = MiniPersonSerializer(read_only=True)
    
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
    id = serializers.IntegerField(source='pk')
    name = serializers.SerializerMethodField()
    names = NameSerializer(many=True, read_only=True)
    birth = BirthEventSerializer(read_only=True)
    death = DeathEventSerializer(read_only=True)
    marriages = MarriageEventSerializer(many=True, read_only=True, source='marriageevents')
    divorces = DivorceEventSerializer(many=True, read_only=True, source='divorceevents')
    immigrations = ImmigrationEventSerializer(many=True, read_only=True)
    citizenships = CitizenshipEventSerializer(many=True, read_only=True)
    parents = MiniPersonSerializer(many=True, read_only=True)
    children = MiniPersonSerializer(many=True, read_only=True)
    siblings = MiniPersonSerializer(many=True, read_only=True)

    def get_name(self, obj):
        name = obj.name
        return NameSerializer(name).data if name else None
    
    class Meta:
        model = Person
        fields = [
            'id', 'name', 'names', 'gender', 'is_living',
            'birth', 'death',
            'marriages', 'divorces',
            'immigrations', 'citizenships',
            'parents', 'children', 'siblings'
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