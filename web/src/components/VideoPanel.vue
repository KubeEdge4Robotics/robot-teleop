<template>
  <div id="widgetVueTemplate">
    <div class="header">
      {{ robotName }}
      <div class="heard_rightBox">
        <div class="stopBut" @click="refreshVideo">刷新</div>
        <div class="signal-icon">
          <div class="bar" style="height: 3px"></div>
          <div class="bar" style="height: 6px"></div>
          <div class="bar" style="height: 9px"></div>
          <div class="bar" style="height: 12px"></div>
          <div class="bar" style="height: 15px"></div>
        </div>
        <div class="robot_electricity">
          <div></div>
          <div></div>
          <div></div>
          <div></div>
          <span></span>
        </div>
        <span>100%</span>
      </div>
    </div>

    <div class="video_box">
      <div class="picture-list">
        <div>
          <div class="picture-item-title">
            <el-dropdown>
              <span class="el-dropdown-link">
                {{ videoNames.videoName1 || "选择视频流"
                }}<i class="el-icon-arrow-down el-icon--right"></i>
              </span>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item
                  v-for="(item, index) in cameras"
                  @click.native="
                    changeCamera(item, 'cameraOne', videoNames.videoName1)
                  "
                  :key="index"
                  :command="item"
                  >{{ item }}</el-dropdown-item
                >
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div class="picture-item-main" id="cameraOne"></div>
        </div>
        <div>
          <div class="picture-item-title">
            <el-dropdown>
              <span class="el-dropdown-link">
                {{ videoNames.videoName2 || "选择视频流"
                }}<i class="el-icon-arrow-down el-icon--right"></i>
              </span>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item
                  v-for="(item, index) in cameras"
                  @click.native="
                    changeCamera(item, 'cameraTwo', videoNames.videoName2)
                  "
                  :key="index"
                  :command="item"
                  >{{ item }}</el-dropdown-item
                >
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div class="picture-item-main" id="cameraTwo"></div>
        </div>
        <div>
          <div class="picture-item-title">
            <el-dropdown>
              <span class="el-dropdown-link">
                {{ videoNames.videoName3 || "选择视频流"
                }}<i class="el-icon-arrow-down el-icon--right"></i>
              </span>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item
                  v-for="(item, index) in cameras"
                  @click.native="
                    changeCamera(item, 'cameraThree', videoNames.videoName3)
                  "
                  :key="index"
                  :command="item"
                  >{{ item }}</el-dropdown-item
                >
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div class="picture-item-main" id="cameraThree"></div>
        </div>
      </div>
      <div class="picture-item-main">
        <div class="picture-item-title">
          <el-dropdown>
            <span class="el-dropdown-link">
              {{ videoNames.videoName4 || "选择视频流"
              }}<i class="el-icon-arrow-down el-icon--right"></i>
            </span>
            <el-dropdown-menu slot="dropdown">
              <el-dropdown-item
                v-for="(item, index) in cameras"
                @click.native="
                  changeCamera(item, 'cameraMain', videoNames.videoName4)
                "
                :key="index"
                :command="item"
                >{{ item }}</el-dropdown-item
              >
            </el-dropdown-menu>
          </el-dropdown>
        </div>
        <div
          id="cameraMain"
          ref="mainVideoBox"
          :class="{ robotBgcGrey: selectedCamera.length === 0 }"
        ></div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import HRTC from "../js/hrtc.js";
export default {
  data() {
    return {
      robotName: "",
      robotId: "",
      remoteId: "",
      selectedCamera: [],
      serviceList: [],
      option: {
        userId: "",
        userName: "client123",
        signature: "",
        ctime: "",
        role: 0,
      },
      client: null,
      cameras: [],
      clients: {},
      num: 1,
      videoItem: [],
      camerasList: {
        oneStream: "",
        twoStream: "",
        threeStream: "",
        mainStream: "",
      },
      mainStream: null,
      oneStream: null,
      twoStream: null,
      threeStream: null,
      videoNames: {
        videoName1: "",
        videoName2: "",
        videoName3: "",
        videoName4: "",
      },
    };
  },
  created() {
    HRTC.checkSystemRequirements().then((res) => {
      console.log(res);
    });
    this.robotId = this.$route.params.id;
    this.fetchServiceList();
    this.flowGetRobotDetail(this.robotId);
  },
  methods: {
    // 获取机器人详情
    flowGetRobotDetail(id) {
      axios.get(`/v1/robot/${id}`).then((res) => {
        this.robotName = res.data.robot_name;
      });
    },

    // 获取服务列表
    fetchServiceList() {
      var currentServiceId = "";
      axios.get(`/v1/service`).then((res) => {
        this.serviceList = res.data.services;
        this.serviceList.forEach((item) => {
          if (item.user_id === this.robotId) {
            currentServiceId = item.service_id;
            this.token = item.token;
          }
        });
        if (currentServiceId) {
          // 调用start启动遥操作桥接器
          this.fetchStartTeleoperation(this.robotId, currentServiceId);
        } else {
          // 调用创建服务桥接器
          this.fetchCreateService();
        }
      });
    },

    // 执行start遥操作
    fetchStartTeleoperation(robotId, serviceId) {
      axios.post(`/v1/robot/${robotId}/${serviceId}/start`).then((res) => {
        this.option.signature =
          res?.data?.sparkrtc?.clients?.console?.signature;
        this.option.ctime = res?.data?.sparkrtc?.clients?.console?.expire_time;
        this.option.userId = "console";
        this.initClient(res?.data?.sparkrtc.app_id);
        this.joinRoom(res?.data?.sparkrtc.room_id);
      });
    },

    // 创建遥操作服务
    fetchCreateService() {
      axios.post(`/v1/service`).then((res) => {
        this.token = res.data.token;
        this.fetchStartTeleoperation(this.robotId, res.data.service_id);
      });
    },

    initClient(appId) {
      try {
        this.client = HRTC.createClient({
          appId: appId,
          countryCode: "CN",
        });
        this.client.enableCommandMsg(true);
        this.client.on("stream-added", (event) => {
          const stream = event.stream;
          this.client.subscribe(stream, {
            video: true,
            audio: true,
          });
          this.clients[stream.userId_] = {
            id: stream.id_,
            userId: stream.userId_,
          };
        });
        this.client.on("peer-join", (event) => {
          this.remoteId = event.userId;
          this.cameras.push(event.userId);
        });

        this.client.on("peer-leave", (event) => {
          const index = this.cameras.indexOf(event.userId);
          if (index !== -1) {
            this.cameras.splice(index, 1);
          }
        });
        this.client.on("stream-subscribed", (event) => {
          const stream = event.stream;
          this.videoItem.push(stream.userId_);
          if (this.num == 1) {
            this.mainStream = stream;
            this.camerasList.mainStream = stream.userId_;
            this.videoNames.videoName4 = stream.userId_;
            this.mainStream.play("cameraMain", {
              objectFit: "cover",
              muted: true,
            });
          }
          if (this.num == 2) {
            this.oneStream = stream;
            this.camerasList.oneStream = stream.userId_;
            this.videoNames.videoName1 = stream.userId_;
            this.oneStream = stream;
            stream.play("cameraOne", {
              objectFit: "cover",
              muted: true,
            });
          }
          if (this.num == 3) {
            this.twoStream = stream;
            this.camerasList.twoStream = stream.userId_;
            this.videoNames.videoName2 = stream.userId_;
            stream.play("cameraTwo", {
              objectFit: "cover",
              muted: true,
            });
          }
          if (this.num == 4) {
            this.threeStream = stream;
            this.camerasList.threeStream = stream.userId_;
            this.videoNames.videoName3 = stream.userId_;
            stream.play("cameraThree", {
              objectFit: "cover",
              muted: true,
            });
          }
          this.num++;
        });
        this.client.on("stream-updated", (event) => {
          console.log("远端流updated", event);
        });
        this.client.on("stream-removed", (event) => {
          event.stream.close();
        });
      } catch (error) {
        console.log(error);
      }
    },
    // sparkRTC
    async joinRoom(rommId) {
      try {
        await this.client.join(rommId, this.option);
        console.log("join room success");
      } catch (error) {
        console.log("join room fail", error);
      }
    },

    refreshVideo() {
      this.videoItem.forEach((item) => {
        if (this.client) {
          this.client.sendCommandMsg(
            JSON.stringify({ event: "stop_stream" }),
            item
          );
        }
        const timer = setTimeout(() => {
          this.videoItem.forEach((item) => {
            if (this.client) {
              this.client.sendCommandMsg(
                JSON.stringify({ event: "start_stream" }),
                item
              );
            }
          });
          clearTimeout(timer);
        }, 2000);
      });
    },
    changeCamera(command, boxId, videoId) {
      var dom = document.getElementById(boxId);
      var existingInnerDiv = dom.querySelector("div");
      if (existingInnerDiv) {
        dom.removeChild(existingInnerDiv);
      }
      for (var key in this.videoNames) {
        if (this.videoNames[key] == command) {
          this.videoNames[key] = "";
        }
      }
      if (boxId == "cameraOne") {
        this.videoNames.videoName1 = command;
      } else if (boxId == "cameraTwo") {
        this.videoNames.videoName2 = command;
      } else if (boxId == "cameraThree") {
        this.videoNames.videoName3 = command;
      } else if (boxId == "cameraMain") {
        this.videoNames.videoName4 = command;
      }
      for (var key in this.camerasList) {
        if (this.camerasList[key] == videoId) {
          if (key == "oneStream") {
            this.oneStream?.stop();
          } else if (key == "twoStream") {
            this.twoStream?.stop();
          } else if (key == "threeStream") {
            this.threeStream?.stop();
          } else if (key == "mainStream") {
            this.mainStream?.stop();
          }
        }
        if (this.camerasList[key] == command) {
          if (key == "oneStream") {
            this.oneStream.stop();
            this.oneStream.play(boxId, {
              objectFit: "cover",
              muted: true,
            });
          } else if (key == "twoStream") {
            this.twoStream.stop();
            this.twoStream.play(boxId, {
              objectFit: "cover",
              muted: true,
            });
          } else if (key == "threeStream") {
            this.threeStream.stop();
            this.threeStream.play(boxId, {
              objectFit: "cover",
              muted: true,
            });
          } else if (key == "mainStream") {
            this.mainStream.stop();
            this.mainStream.play(boxId, {
              objectFit: "cover",
              muted: true,
            });
          }
        }
      }
    },
  },
};
</script>

<style>
#widgetVueTemplate {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 920px;
  min-height: 620px;
  height: 100%;
  background-color: rgba(36, 36, 36, 1);
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

.header {
  position: absolute;
  top: 0;
  width: 100%;
  font-size: 16px;
  height: 48px;
  line-height: 48px;
  text-align: center;
  background-color: rgba(40, 43, 51, 0.5);
  color: #fff;
  z-index: 1;
}

.heard_rightBox {
  display: flex;
  align-items: center;
  position: absolute;
  top: 0;
  right: 0;
  font-size: 12px;
  padding-right: 20px;
}

.stopBut {
  font-size: 12px;
  margin-right: 22px;
  width: 100px;
  height: 28px;
  line-height: 28px;
  border-radius: 2px;
  text-align: center;
  background-color: #c7000b;
  cursor: pointer;
}

.heard_rightBox > div {
  display: inline-block;
}

.signal-icon {
  line-height: 0;
  margin-right: 16px;
  font-size: 0;
}

.bar {
  display: inline-block;
  width: 2px;
  margin-right: 2px;
  background-color: #fff;
}

.robot_electricity {
  position: relative;
  width: 24px;
  height: 16px;
  font-size: 0;
  padding: 1px 1px;
  box-sizing: border-box;
  margin-right: 12px;
  border: 3px solid #fff;
  border-radius: 5px;
  line-height: 0;
  text-align: unset;
}

.robot_electricity div {
  display: inline-block;
  width: 3px;
  height: 7px;
  margin-right: 1px;
  border-radius: 4px;
  background-color: #fff;
}

.robot_electricity span {
  position: absolute;
  top: 1px;
  right: -7px;
  display: inline-block;
  width: 3px;
  height: 8px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  background-color: #fff;
}

.video_box {
  display: flex;
  flex: 1;
  position: relative;
  height: 50px;
  padding: 55px 10px 7px;
  background-color: #ccc;
}

#cameraMain {
  position: relative;
  flex: 1;
  height: 100%;
  border-radius: 4px;
  background-color: #000000;
}

.picture-list {
  display: flex;
  flex-direction: column;
  width: 400px;
  height: 100%;
  margin-right: 10px;
  flex-shrink: 0;
}

.picture-list video {
  z-index: 999;
}

.picture-list > div {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
  background-color: #979797;
}

.picture-list > div:not(:last-of-type) {
  margin-bottom: 12px;
}

.picture-item-title {
  flex-shrink: 0;
  padding-left: 10px;
  width: 100%;
  height: 30px;
  line-height: 30px;
  font-size: 12px;
  color: #fff;
  background-color: #282b33;
}

.picture-item-main {
  flex: 1;
  z-index: 999;
  border-radius: 4px;
  overflow: hidden;
}

.robotBgcGrey {
  background-color: #979797 !important;
}

.robot-video-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 160px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  font-size: 14px;
  color: #fff;
}

.select_video_popup {
  display: none;
  position: absolute;
  bottom: 77px;
  left: -60px;
  width: 196px;
  padding: 20px 20px 12px;
  font-size: 12px;
  box-sizing: border-box;
  color: #000000;
  background-color: #fff;
  box-shadow: 0px 2px 8px 0px rgba(0, 0, 0, 0.2);
}

.select_video_popup_active {
  display: block;
  opacity: 0;
  animation: fade-in 0.3s forwards;
}
</style>