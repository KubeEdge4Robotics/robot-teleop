FROM python:3.8-slim

LABEL mainterner="joeyhwong@gknow.cn"

WORKDIR /code
ENV PYTHONPATH "/code/lib"

COPY ./robosdk /code/lib/robosdk
COPY ./requirements.txt /code/requirements.txt
COPY ./examples/scout-arm/teleoperation/server/main.py /code/main.py

RUN pip3 install --upgrade pip
RUN pip3 install -r /code/requirements.txt

COPY ./configs /code/lib/configs

ENTRYPOINT ["python", "/code/main.py"]