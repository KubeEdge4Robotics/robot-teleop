<template>
  <div id="widgetEventTemplate">
    <div class="robotList_header">机器人列表</div>
    
    <div class="robotList_main">
      <div
        class="robotList_item"
        v-for="item in robotList"
        :key="item.robot_id"
      >
        <div class="robotList_name">
          <svg
            width="20px"
            height="20px"
            viewBox="0 0 20 20"
            version="1.1"
            xmlns="http://www.w3.org/2000/svg"
            xmlns:xlink="http://www.w3.org/1999/xlink"
          >
            <title>安全加固</title>
            <defs>
              <linearGradient
                x1="20.793418%"
                y1="13.3010507%"
                x2="66.2357302%"
                y2="99.9336394%"
                id="linearGradient-1"
              >
                <stop stop-color="#A5BAFF" offset="0%"></stop>
                <stop stop-color="#7693F5" offset="99.9234586%"></stop>
              </linearGradient>
            </defs>
            <g
              id="机器人列表"
              stroke="none"
              stroke-width="1"
              fill="none"
              fill-rule="evenodd"
            >
              <g
                id="05-02-02-07-运行平台-机器人管理-实时状态：传感器详情备份-4"
                transform="translate(-92.000000, -88.000000)"
              >
                <g id="编组-22" transform="translate(68.000000, 68.000000)">
                  <g id="安全加固" transform="translate(24.000000, 20.000000)">
                    <g id="编组-28" transform="translate(2.000000, 1.000000)">
                      <path
                        d="M11.1785577,12.3761265 C11.1785577,13.1628938 3.08861606,12.7397793 3.66257706,13.4976838 C4.22432108,14.239456 4.97318257,14.9383104 5.73734607,15.5372967 C7.21466207,16.6952845 8.74916841,17.4800217 9.09943134,17.4800217 C9.75628971,17.4800217 15.4888627,14.1957299 15.4888627,11.1503024 L15.4888627,2.90971674 L12.4000073,2.90971674 C12.400005,2.90971674 12.7908201,4.27165185 12.4000073,7.30051439 C12.2844652,8.19598398 11.8773153,9.88785467 11.1785577,12.3761265 Z"
                        id="路径"
                        fill="#D2DDFF"
                        fill-rule="nonzero"
                      ></path>
                      <path
                        d="M12.0622858,2.09000243 C12.0622858,2.09000243 11.1068558,2.09000243 9.55428284,1.49285935 C7.88228089,0.895716261 6.86714385,0.238857887 6.86714385,0.238857887 L6.38942971,0 L5.97142922,0.238857887 C5.97142922,0.238857887 4.89657036,0.895716261 3.28429024,1.49285935 C1.67200195,2.03028878 0.776287317,2.09000243 0.776287317,2.09000243 L0,2.14971674 L0,10.3903024 C0,13.4357299 5.67287074,16.7200217 6.38943134,16.7200217 C7.04628971,16.7200217 12.7788627,13.4357299 12.7788627,10.3903024 L12.7788627,2.14971674 L12.0622907,2.09000243 L12.0622858,2.09000243 Z M5.97141453,11.5845896 L2.9856991,8.83772224 L3.88141373,7.70314972 L5.79228009,9.43486369 L9.3751484,4.95628238 L10.4500073,5.97142596 L5.97142596,11.5845896 L5.97141453,11.5845896 Z"
                        id="形状"
                        fill="url(#linearGradient-1)"
                      ></path>
                    </g>
                  </g>
                </g>
              </g>
            </g>
          </svg>
          <span>{{ item.robot_name }}</span>
        </div>
        <button
          v-if="item.status === 'RUNNING'"
          class="robotList_button"
          @click="jumpPage(item.robot_id)"
        >
          查看第一视角
        </button>
        <div v-if="item.status !== 'RUNNING'" class="robotList_locked">
          <span></span>已锁定
        </div>
      </div>
    </div>
  </div>
  
</template>

<script>
import axios from "axios";
export default {
  name: "RobotList",
  props: {},
  data() {
    return {
      robotList: [],
    };
  },
  created() {
    this.fetchRobotList();
  },
  methods: {
    jumpPage(id) {
      this.$router.push({path:`/panel/${id}`});
    },
    // 获取服务列表桥接器
    fetchRobotList() {
      axios.get("/v1/robot").then((res) => {
        this.robotList = res.data.robots;
      });
    },
  },
};
</script>

<style scoped>

#widgetEventTemplate {
  position: relative;
  width: 100%;
  min-width: 830px;
  height: 100%;
  margin: 0 !important;
}

.robotList_header {
  position: absolute;
  top: 0;
  height: 48px;
  width: 100%;
  line-height: 48px;
  color: #fff;
  font-size: 16px;
  text-align: center;
  background: rgba(40, 43, 51, 0.5);
}

.robotList_main {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  height: calc(100% - 68px);
  padding: 68px 50px 0;
  background: radial-gradient(rgba(37, 43, 58, 0.5), #252b3a);
}

.robotList_main > div {
  box-sizing: border-box;
  height: 100px;
  width: calc((100% - 36px) / 4);
  margin-right: 12px;
  margin-top: 12px;
  padding: 20px 24px;
  background: #252b3a;
  box-shadow: 0px 1px 3px 0px rgba(0, 0, 0, 0.1);
}

.robotList_main div:nth-of-type(4n + 0) {
  margin-right: 0;
}

.robotList_name {
  display: flex;
}

.robotList_name span {
  display: inline-block;
  width: calc((100% - 26px));
  font-size: 14px;
  color: #adb0b8;
  margin-left: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.robotList_button {
  width: 100px;
  height: 30px;
  line-height: 28px;
  text-align: center;
  font-size: 12px;
  margin-top: 14px;
  color: #fff;
  background-color: #c7000b;
  border-radius: 2px;
  border: 1px solid #c7000b;
  cursor: pointer;
}

.robotList_locked {
  width: 100px;
  height: 30px;
  line-height: 28px;
  font-size: 12px;
  margin-top: 14px;
  color: #fff;
}

.robotList_locked span {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 8px;
  background-color: #fa9841;
  border-radius: 50%;
}

.el-dialog {
  background-color: #252b3a;
}

.el-dialog__body {
  font-size: 16px;
  color: #979797;
}

.el-dialog__title {
  color: #979797;
}

.el-button:hover {
  color: #606266;
}

.robotList_btn {
  background-color: #c7000b;
  border-radius: 2px;
  color: #fff;
  border: 1px solid #c7000b;
}
.robotList_btn:hover {
  background-color: #c7000b;
  color: #fff;
  border: 1px solid #c7000b;
}
</style>
