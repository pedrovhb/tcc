from peewee import Model, CharField, DateTimeField, ForeignKeyField, AutoField, IntegerField, FloatField, BooleanField
from playhouse.postgres_ext import PostgresqlExtDatabase, ArrayField, BlobField

from utils import log

pg_db = PostgresqlExtDatabase('postgres', user='postgres', password='secret',
                              host='tcc_timescaledb', port=5432)


class BaseModel(Model):
    """A base model that will use our Postgresql database"""

    class Meta:
        database = pg_db


class Station(BaseModel):
    name = CharField(primary_key=True, unique=True)
    description = CharField()
    is_training = BooleanField()
    trained_model = BlobField(null=True)  # Trained model for aggregate data


class Observation(BaseModel):
    id_ = AutoField(primary_key=True)
    station = ForeignKeyField(model=Station, backref='observations')
    time = DateTimeField()
    is_training = BooleanField()

    sample_frequency = FloatField()
    sample_count = IntegerField()
    sample_data = ArrayField(FloatField)

    rms = FloatField()
    crest = FloatField()
    peak_to_peak = FloatField()
    kurtosis = FloatField()

    is_anomaly = BooleanField(null=True)


def clear_db():
    pg_db.drop_tables([Station, Observation])
    pg_db.create_tables([Station, Observation])


pg_db.create_tables([Station, Observation])
log.info('Loaded DB')
