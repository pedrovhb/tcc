import numpy as np
from scipy.stats import kurtosis

from functools import wraps
from time import time


def timing(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time()
        result = f(*args, **kwargs)
        end = time()
        print('Elapsed time: {} for {}'.format(end - start, f.__name__))
        return result

    return wrapper


def calc_rms(df):
    return np.sqrt(np.mean(np.square(df)))


def calc_crest(df):
    return np.max(np.abs(df)) / np.sqrt(np.mean(np.square(df)))


def calc_peak_to_peak(df):
    return np.max(df) - np.min(df)


def calc_kurtosis(df):
    return kurtosis(df)
