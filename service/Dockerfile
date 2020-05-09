FROM python:3.7-buster
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get install -y libopenblas-dev gfortran

WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt


