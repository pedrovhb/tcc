from datetime import datetime
from typing import Union, Dict, List

import pandas as pd
from playhouse.shortcuts import model_to_dict
from sklearn.covariance import EllipticEnvelope
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from tqdm import tqdm
import matplotlib.pyplot as plt

from database import Station, Observation
from sklearn.ensemble import IsolationForest, GradientBoostingClassifier


# todo - observation count window size vs timedelta window size
def get_trained_forest(station: Station, training_set_size: int = 50) -> list:
    observations_select = Observation.select(
        Observation.time,
        Observation.sample_frequency,
        Observation.sample_count,
        Observation.rms,
        Observation.crest,
        Observation.peak_to_peak,
        Observation.kurtosis,
    ). \
        where(Observation.station == station). \
        order_by(Observation.time.asc()).limit(training_set_size)

    obs_data = []
    for observation in observations_select:
        obs_data.append([observation.rms, observation.peak_to_peak, observation.kurtosis, observation.crest])

    models = [
        IsolationForest(n_estimators=30, behaviour='new', contamination=0.05),
        EllipticEnvelope(contamination=0.05),
        LocalOutlierFactor(novelty=True, contamination=0.05),
        OneClassSVM()
    ]
    for model in models:
        model.fit(obs_data)
    return models


def make_prediction(observation: Observation) -> Dict[str, Union[datetime, int]]:
    new_observation_data = [observation.rms, observation.peak_to_peak, observation.kurtosis, observation.crest]
    predictions = {m.__class__.__name__: m.predict([new_observation_data])[0] for m in trained_models}
    predictions['Sum'] = sum(p for p in predictions.values())
    predictions_dict = dict(Time=observation.time, **predictions)
    return predictions_dict


station = Station.get()
trained_models = get_trained_forest(station)

df_predictions = pd.DataFrame(columns=['Time', *[model.__class__.__name__ for model in trained_models]])
df_data = pd.DataFrame(columns=['Time', 'rms', 'peak to peak', 'kurtosis', 'crest'])

for obs in tqdm(Observation.select(
        Observation.time,
        Observation.rms,
        Observation.crest,
        Observation.peak_to_peak,
        Observation.kurtosis).where(Observation.station == station).order_by(Observation.time)):
    prediction_d = make_prediction(obs)

    new_observation_data = model_to_dict(obs)
    new_observation_data['Time'] = new_observation_data.pop('time')
    for k, v in new_observation_data.copy().items():
        if v is None:
            new_observation_data.pop(k)

    df_predictions = df_predictions.append(prediction_d, ignore_index=True)
    df_data = df_data.append(new_observation_data, ignore_index=True)

df_data.set_index('Time', inplace=True)
df_predictions.set_index('Time', inplace=True)

ax = plt.subplot(2, 1, 1)
df_predictions['Sum'][::3].plot(ax=ax, title='ok', figsize=(16, 10), fontsize=20)
ax = plt.subplot(2, 1, 2)
df_data[::3].plot(ax=ax, title='ok', figsize=(16, 10), fontsize=20)
ax.title.set_size(24)
plt.tight_layout()
plt.savefig('Distribuicoes.png', dpi=120)
