FROM python:3.8-slim

LABEL mainterner="joeyhwong@gknow.cn"

WORKDIR /share/robosdk
COPY ./robosdk/configs /share/robosdk/configs

WORKDIR /code
COPY ./robosdk/robosdk /code/lib/robosdk
COPY ./robosdk/requirements.txt /code/requirements.txt
COPY ./server /code/lib/server
ENV PYTHONPATH "/code/lib"

RUN pip3 install --upgrade pip
RUN pip3 install -r /code/requirements.txt
RUN pip3 install -r /code/lib/server/requirements.txt

ENTRYPOINT ["python"]