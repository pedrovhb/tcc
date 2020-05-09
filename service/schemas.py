from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class StationCreationSchema(BaseModel):
    name: str = ...
    description: str = ...
    is_training: bool = True


class ObservationCreationSchema(BaseModel):
    station_name: str = ...
    time: Optional[datetime]
    sample_frequency: float = ...
    sample_data: List[float] = ...
