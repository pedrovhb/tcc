import asyncio
import json
import os
import time
from datetime import datetime

import pandas as pd
from aiohttp import ClientSession, TCPConnector
from tqdm import tqdm
from tenacity import retry, stop_after_attempt

from calculations import calc_rms, calc_kurtosis, calc_crest, calc_peak_to_peak

IMS_DATASET_DIR = "/ims_dataset"
host = "http://app:8000"


def load_datasets(folder):
    file_list = os.listdir(os.path.join(IMS_DATASET_DIR, folder))
    file_list.sort()
    for filename in file_list:
        loaded_dt = datetime.strptime(filename, "%Y.%m.%d.%H.%M.%S")
        loaded_df = pd.read_csv(
            os.path.join(IMS_DATASET_DIR, folder, filename),
            sep="\t",
            names=["Ch 1", "Ch 2", "Ch 3", "Ch 4"],
        )
        yield loaded_df, loaded_dt


# Clears DB, creates stations for each channel in test 2
async def startup():
    async with ClientSession() as client:
        r = await client.post(f"{host}/clear_db")
        assert r.status == 200

        for i in range(1, 4 + 1):
            r = await client.post(
                f"{host}/create_station",
                json={
                    "name": f"test_2_ch_{i}",
                    "description": "",
                    "is_training": True,
                },
            )
            assert r.status == 200


@retry(stop=stop_after_attempt(4))
async def post_one(
    client: ClientSession, channel: str, dt: datetime, df: pd.DataFrame
):
    channel_number = channel.split()[1]
    await client.post(
        f"{host}/make_observation",
        json={
            "station_name": f"test_2_ch_{channel_number}",
            "time": dt.timestamp(),
            "sample_frequency": 20000,
            "sample_count": len(df[channel]),
            "rms": calc_rms(df[channel].values.tolist()),
            "crest": calc_crest(df[channel].values.tolist()),
            "peak_to_peak": calc_peak_to_peak(df[channel].values.tolist()),
            "kurtosis": calc_kurtosis(df[channel].values.tolist()),
        },
    )
    insertion_dts.append(time.time())


async def disable_training(client: ClientSession, channel: str):
    channel_number = channel.split()[1]
    await client.post(
        f"{host}/disable_training",
        params={"station_name": f"test_2_ch_{channel_number}",},
    )


async def do_input():
    async with ClientSession(
        connector=TCPConnector(limit_per_host=5)
    ) as client:

        disabled_training = False
        tasks = []
        for df, dt in load_datasets("2nd_test"):
            for channel in df.columns:
                tasks.append(post_one(client, channel, dt, df))
            if len(tasks) > 200:
                print(f"Sending {len(tasks)}...")
                for res in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
                    await res
                if not disabled_training:
                    await asyncio.gather(
                        *[disable_training(client, ch) for ch in df.columns]
                    )
                    disabled_training = True
                tasks = []


async def main():
    await startup()
    await do_input()


insertion_dts = []

asyncio.run(main())
print(insertion_dts)
with open(r"insertion_dts", "w") as fd:
    json.dump(insertion_dts, fd)
