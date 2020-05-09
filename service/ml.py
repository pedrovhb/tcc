import time
from typing import List

import dill
from pyod.models.knn import KNN
from pyod.models.lof import LOF
from pyod.models.lscp import LSCP
from pyod.models.pca import PCA

from database import Observation, Station
from utils import log

loaded_models = {}


def make_prediction_agg(observations: List[Observation], p: float) -> int:
    log.info(f'Calculating prediction from {len(observations)} observations (p: {p})')
    if observations[0].station.name in loaded_models:
        trained_model = loaded_models[observations[0].station.name]
    else:
        trained_model = dill.loads(observations[0].station.trained_model)
        loaded_models[observations[0].station.name] = trained_model
    observation_data = [[obs.rms, obs.peak_to_peak, obs.kurtosis, obs.crest] for obs in observations]
    predictions = trained_model.predict(observation_data)
    positive_ratio = sum(predictions) / len(predictions)
    log.info(f'Prediction p: {positive_ratio}')
    if positive_ratio >= p:
        log.info('Result: anomaly')
        return 1
    else:
        log.info('Result: no anomaly')
        return 0


def train_model(station: Station) -> LSCP:
    t1 = time.time()
    log.info(f'Training model for {station}...')
    log.info('Loading training observations')
    observations_select = Observation.select(
        Observation.time,
        Observation.sample_frequency,
        Observation.sample_count,
        Observation.rms,
        Observation.crest,
        Observation.peak_to_peak,
        Observation.kurtosis,
    ).where(Observation.station == station, Observation.is_training)

    obs_data = []
    for observation in observations_select:
        obs_data.append([observation.rms, observation.peak_to_peak, observation.kurtosis, observation.crest])

    log.info('Fitting LSCP model')
    lscp = LSCP(
        [KNN()] * 5
        + [LOF()] * 5
        + [PCA()] * 5, contamination=0.03)
    lscp.fit(X=obs_data)
    log.info(f'Trained model in {time.time() - t1}')
    return lscp


def serialize_model(model: LSCP):
    log.info('Serializing model...')
    return dill.dumps(model)
