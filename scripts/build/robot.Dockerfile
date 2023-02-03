FROM arm64v8/ros:noetic-ros-base

LABEL mainterner="joeyhwong@gknow.cn"

WORKDIR /home
COPY ./configs /home/configs
COPY ./robosdk /home/lib/robosdk
COPY ./examples/scout-arm/teleoperation/robot/main.py /home/main.py
COPY ./requirements.txt /home/requirements.txt

RUN apt-get clean && apt-get update \
    && apt-get install -q -y cmake python3-pip \
    python3-opencv ros-noetic-cv-bridge \
    ros-noetic-move-base-msgs ros-noetic-audio-common-msgs ros-noetic-tf \
    libgl1-mesa-glx wireless-tools iproute2

RUN pip3 install --upgrade pip
RUN pip3 uninstall -y setuptools
RUN pip3 install -r /home/requirements.txt

ENV SERVER_URL ""
ENV CFG_PATH /home/configs
ENV PYTHONPATH /home/lib

RUN echo ' \n \
    echo "Sourcing ROS1 packages ..." \n \
    export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1:$LD_PRELOAD \n \
    source /opt/ros/noetic/setup.bash \n' >> ~/.bashrc

# cleanup

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["bash"]
