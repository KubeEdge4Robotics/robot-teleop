FROM arm64v8/ros:noetic-ros-base

LABEL mainterner="joeyhwong@gknow.cn"

WORKDIR /share/robosdk
COPY ./robosdk/configs /share/robosdk/configs

WORKDIR /code
COPY ./robosdk/robosdk /code/lib/robosdk
COPY ./robosdk/requirements.txt /code/requirements.txt
COPY ./robot /code/main

ENV PYTHONPATH /code/lib

RUN apt-get clean && apt-get update \
    && apt-get install -q -y cmake python3-pip \
    python3-opencv ros-noetic-cv-bridge \
    ros-noetic-move-base-msgs ros-noetic-audio-common-msgs ros-noetic-tf \
    libgl1-mesa-glx wireless-tools iproute2

RUN pip3 install --upgrade pip
RUN pip3 uninstall -y setuptools
RUN pip3 install -r /code/requirements.txt
RUN pip3 install aiortc~=1.4.0


RUN echo ' \n \
    echo "Sourcing ROS1 packages ..." \n \
    export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1:$LD_PRELOAD \n \
    source /opt/ros/noetic/setup.bash \n' >> ~/.bashrc

# cleanup

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["bash"]
