import uvicorn
from fastapi import FastAPI, HTTPException
from playhouse.shortcuts import model_to_dict, IntegrityError

from calculations import *
from database import Station, Observation, clear_db
from ml import make_prediction_agg, serialize_model, train_model
from schemas import *
from utils import log

app = FastAPI()

AGG_OBSERVATION_SAMPLE_SIZE = 5
AGG_OBSERVATION_SAMPLE_P = 0.5


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/create_station")
async def create_station(station: StationCreationSchema):
    try:
        station = Station.create(**station.dict())
        return model_to_dict(station)
    except IntegrityError:
        raise HTTPException(409, 'station name already exists')


@app.post("/enable_training")
async def station_enable_training(station_name: str):
    return station_set_training(station_name, True)


@app.post("/disable_training")
async def station_disable_training(station_name: str):
    return station_set_training(station_name, False)


def station_set_training(station_name: str, enabled: bool):
    station = Station.get_or_none(Station.name == station_name)
    if station is None:
        raise HTTPException(404, 'station not found')
    else:
        log.info(f'Setting training enabled: {enabled} for {station}')
        station.is_training = enabled
        station.save()
        if not enabled:
            model = train_model(station)
            station.trained_model = serialize_model(model)
            station.save()
        return {'status': 'ok'}


@app.post("/make_observation")
async def make_observation(observation_data: ObservationCreationSchema):
    station = Station.get_or_none(Station.name == observation_data.station_name)
    if station is None:
        raise HTTPException(404, 'station not found')
    new_observation = Observation.create(station=station.name,
                                         is_training=station.is_training,
                                         time=observation_data.time or datetime.now(),
                                         sample_frequency=observation_data.sample_frequency,
                                         sample_count=len(observation_data.sample_data),
                                         sample_data=observation_data.sample_data,
                                         rms=calc_rms(observation_data.sample_data),
                                         crest=calc_crest(observation_data.sample_data),
                                         peak_to_peak=calc_peak_to_peak(observation_data.sample_data),
                                         kurtosis=calc_kurtosis(observation_data.sample_data))
    if not station.is_training:
        # We get a few previous datapoints in order to make N predictions instead of just 1, which
        # may be subject to noise
        observations_select = Observation.select(
            Observation.station,
            Observation.is_training,
            Observation.time,
            Observation.rms,
            Observation.crest,
            Observation.peak_to_peak,
            Observation.kurtosis,
        ).where(Observation.station == station). \
            order_by(Observation.time.desc()).limit(AGG_OBSERVATION_SAMPLE_SIZE)
        observations = list(observations_select)
        anomaly_detected = make_prediction_agg(observations, AGG_OBSERVATION_SAMPLE_P)
        new_observation.is_anomaly = anomaly_detected
        new_observation.save()
        return {'anomaly': anomaly_detected}
    else:
        log.info(f'Station {station} in training mode; no prediction made')
        return {'ok': True}


@app.post('/clear_db')
async def do_clear_db():
    log.info('Clearing DB...')
    clear_db()
    return {'status': 'ok'}


@app.get('/station')
async def get_station(station_name: str, max_observations: int = 10):
    station = Station.get_or_none(Station.name == station_name)
    if station is None:
        raise HTTPException(404, 'station not found')
    observations_select = Observation.select(
        Observation.time,
        Observation.sample_frequency,
        Observation.sample_count,
        Observation.rms,
        Observation.crest,
        Observation.peak_to_peak,
        Observation.kurtosis,
    ).where(Observation.station == station).limit(max_observations)
    observations = [model_to_dict(obs, fields_from_query=observations_select) for obs in observations_select]
    return {'station': model_to_dict(station), 'observations': observations}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
