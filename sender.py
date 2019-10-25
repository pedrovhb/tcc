import asyncio
import os
from datetime import datetime

import pandas as pd
from aiohttp import ClientSession, TCPConnector
from tqdm import tqdm


def load_datasets(folder):
    for filename in os.listdir(os.path.join(r'G:\BigData\IMS', folder)):
        loaded_dt = datetime.strptime(filename, '%Y.%m.%d.%H.%M.%S')
        loaded_df = pd.read_csv(os.path.join(r'G:\BigData\IMS', folder, filename), sep='\t',
                                names=['Ch 1', 'Ch 2', 'Ch 3', 'Ch 4'])
        yield loaded_df, loaded_dt


host = 'http://localhost:8000'


async def startup():
    async with ClientSession() as client:
        r = await client.post(f'{host}/clear_db')
        assert r.status == 200

        for i in range(1, 4 + 1):
            r = await client.post(f'{host}/create_station', json={
                'name': f'test_2_ch_{i}',
                'description': '',
                'is_training': True
            })
            assert r.status == 200


async def post_one(client: ClientSession, channel: str, dt: datetime, df: pd.DataFrame):
    channel_number = channel.split()[1]
    await client.post(f'{host}/make_observation', json={
        'station_name': f'test_2_ch_{channel_number}',
        'time': dt.timestamp(),
        'sample_frequency': 20000,
        'sample_data': df[channel].values.tolist()
    })


async def do_input():
    async with ClientSession(connector=TCPConnector(limit_per_host=5)) as client:

        set_training_off = False
        tasks = []
        for df, dt in load_datasets('2nd_test'):
            for channel in df.columns:
                tasks.append(post_one(client, channel, dt, df))
            if len(tasks) > 100:
                print(f'Sending {len(tasks)}...')
                for res in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
                    await res
                if not set_training_off:
                    set_training_off = True

                tasks = []


async def main():
    await startup()
    await do_input()


asyncio.run(main())
