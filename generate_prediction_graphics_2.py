import pandas as pd
from playhouse.shortcuts import model_to_dict
import matplotlib.pyplot as plt
import pylab as plot

from database import Station, Observation
from utils import log

plt.clf()

observation_fields = Observation._meta.fields
observation_fields.pop('sample_data')
observation_fields.pop('station')

station_name = 'test_2_ch_1'
station = Station.get(Station.name == station_name)

log.info('Getting observations...')
observation_query = Observation.select(*observation_fields.values()).where(Observation.station == station)
station_observations = list(map(model_to_dict, observation_query))

for obs in station_observations:
    obs.pop('sample_data')
    obs.pop('station')
    obs.pop('sample_frequency')
    obs.pop('sample_count')
    obs.pop('id_')

df = pd.DataFrame(station_observations)
log.info('Created dataframe.')

df.rename(columns={
    'rms': 'RMS',
    'peak_to_peak': 'Pico a Pico',
    'kurtosis': 'Curtose',
    'crest': 'Fator de Crista',
    'time': 'Tempo'
}, inplace=True)

df.set_index('Tempo', inplace=True)
df.sort_index(inplace=True)
df = (df - df.min()) / (df.max() - df.min())

df = df[::2]

plot.rcParams.update({'legend.fontsize': 18, 'legend.handlelength': 2})

ax = df[['RMS', 'Fator de Crista', 'Pico a Pico', 'Curtose']].plot(linewidth=0.8, figsize=(14, 8), fontsize=14)
fill_where_anomaly = [True if df.loc[x].is_anomaly == 1 else False for x in df.index]
fill_where_training = [True if df.loc[x].is_training == 1 else False for x in df.index]
ax.fill_between(df.index, 0, 1, where=fill_where_anomaly, facecolor='orange', alpha=0.2)
ax.fill_between(df.index, 0, 1, where=fill_where_training, facecolor='green', alpha=0.2)
ax.set_xlabel('Tempo', fontsize=18)

plt.tight_layout()
plt.savefig('Predicoes.png', dpi=160)
