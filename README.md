# 校园网自动登录脚本（四川信息职业技术学院 · 中国移动）

基于 [xiaoxiaoguai-yyds](https://github.com/xiaoxiaoguai-yyds) 学长的《[SCITC-xiaoyuanwifi](https://github.com/xiaoxiaoguai-yyds/SCITC-xiaoyuanwifi)》中国电信校园网登录脚本项目为灵感编写。

一个用于自动登录校园网 Web Portal 认证的 Python 脚本。  
基于实际wireshark抓包分析编写，适用于四川信息职业技术学院（SCITC）的 **中国移动** 校园网认证系统。

---

## 功能简介

- 支持有线 / 无线双网卡，自动判断当前使用的网卡并选择对应 MAC。
- 启动时判断是否在校园网，不在则直接退出，不占用资源。
- 在校园网环境下常驻后台，定期检查网络状态。
- 断网或认证过期后自动重新登录。
- 运行中检测到离开校园网时自动退出，等待下次开机重新运行。
- 可配置开机自启，静默运行。

---

## 抓包分析结果

通过对校园网登录过程抓包，得到以下关键信息：

| 项目       | 内容                                                                       |
| ---------- | -------------------------------------------------------------------------- |
| 认证方式   | Web Portal（HTTP 表单提交）                                                |
| 认证服务器 | `10.2.1.27`                                                                |
| 登录接口   | `POST http://10.2.1.27/api/portal/webauth`                                 |
| 请求格式   | `application/x-www-form-urlencoded`                                        |
| 返回格式   | JSON（包含 `success` 和 `code` 字段）                                      |
| 设备绑定   | 服务器端启用 MAC 绑定（`enableBindMac: "Y"`），通常限制一台手机 + 一台电脑 |

### 登录请求参数

```text
wlanacname=SCITC-BRAS-ME60
wlanuserip=你的本机IP
mac=你的MAC地址
userId=你的账号
passwd=你的密码
loginMode=password
recordTerminalMac=Y
browserFingerprint=随机32位十六进制字符串
```

### 成功返回示例

```json
{
  "success": true,
  "message": "",
  "code": 200,
  "result": {
    "redirect": "/portal/center?...",
    "token": "eyJ...",
    "distoken": "S1FWQl9VWg..."
  },
  "timestamp": 1790574389333
}
```

---

## 环境要求

- Python 3.6 及以上
- 依赖库：`requests`
- 图形界面：`tkinter`（Python 自带，Windows / macOS 通常可用）

安装依赖：

```bash
pip install requests
```

---

## 配置说明

打开 `校园网.py`，找到 `CONFIG` 配置区，按需修改以下项目。

- **auth_host**  
  认证服务器 IP  
  示例：`10.2.1.27`

- **auth_path**  
  登录接口路径  
  示例：`/api/portal/webauth`

- **user_id**  
  校园网账号  
  示例：`你的账号`

- **passwd**  
  校园网密码  
  示例：`你的密码`

- **wlanacname**  
  认证服务器名称  
  示例：`SCITC-BRAS-ME60`

- **mac_ethernet**  
  有线网卡 MAC 地址  
  示例：`aa:bb:cc:dd:ee:01`

- **mac_wireless**  
  无线网卡 MAC 地址  
  示例：`aa:bb:cc:dd:ee:02`

- **campus_ssid**  
  校园网 WiFi 名称，留空则不校验  
  示例：可留空

- **timeout**  
  请求超时时间（秒）  
  示例：`8`

- **retry_times**  
  登录失败重试次数  
  示例：`3`

- **retry_interval**  
  每次重试间隔（秒）  
  示例：`5`

- **check_interval**  
  循环检查网络间隔（秒）  
  示例：`900`

- **internet_check_host**  
  外网检测地址  
  示例：`www.baidu.com`

- **internet_check_port**  
  外网检测端口  
  示例：`80`

- **log_file**  
  日志文件名  
  示例：`campus_login.log`

### 如何查看本机 MAC 地址

Windows：

1. 按 `Win + R`，输入 `cmd`，回车。
2. 运行 `ipconfig /all` 或 `getmac /v`。
3. 找到你连接校园网的那张网卡（有线和无线），复制其物理地址。
4. 格式示例：`a8:e2:91:13:c8:e4`


## 双网卡 MAC 选择逻辑

脚本会自动判断当前哪张网卡在工作，并选择对应的 MAC。

- **第一步：获取本机默认出口 IP**  
  通过 `socket.connect(("8.8.8.8", 80))` 获取当前用于外网通信的 IP。

- **第二步：找到拥有该 IP 的网卡**  
  遍历所有网卡，找到 IP 匹配的那一张。

- **第三步：判断网卡类型**  
  通过网卡名称关键字或 `psutil` / PowerShell 判断是有线还是无线。

- **第四步：选择 MAC**
  - 实际 MAC 与配置匹配 → 使用配置的 MAC。
  - 不匹配 → 按网卡类型回退到有线或无线 MAC。
  - 无法判断 → 默认使用有线 MAC。


## 运行逻辑

### 启动时

1. 校验配置是否完整（账号、密码、至少一个 MAC）。
2. 尝试连接认证服务器 `10.2.1.27:80`。
3. 连接失败 → 判定不在校园网 → 记录错误日志并退出。
4. 连接成功 → 判定在校园网 → 进入常驻循环。

### 常驻循环（每 `check_interval` 秒一轮）

1. 再次判断是否在校园网，不在则退出。
2. 检测外网是否可达（连接 `www.baidu.com:80`）。
   - **可达** → 网络正常，什么都不做。
   - **不可达** → 判定断网，触发重新登录。
3. 登录时先选择 MAC，再提交表单。
4. 登录失败自动重试，最多 `retry_times` 次，每次间隔 `retry_interval` 秒。

### 退出后

- 脚本退出后不会自动重启，等下次开机时任务计划程序重新触发。
- 如果拔掉网线后又插回，需要手动重启脚本或重启电脑。


## 使用方法

### 开机自启（Windows 任务计划程序）

1. 按 `Win + R`，输入 `taskschd.msc`，回车。
2. 右侧点击 **“创建任务”**。
3. **常规**：名称填 `校园网自动登录`，勾选 **“不管用户是否登录都要运行”** 和 **“使用最高权限运行”**。
4. **触发器**：新建 → 开始任务选 **“登录时”**，延迟 `30 秒`。
5. **操作**：新建 → 启动程序：
   - **程序**：`pythonw.exe` 完整路径（在 cmd 里运行 `where pythonw` 查看）
   - **参数**：脚本完整路径，例如 `D:\scripts\校园网.py`
   - **起始于**：脚本所在目录，例如 `D:\scripts`
6. **条件**：取消 **“只有在计算机使用交流电源时才启动此任务”**。
7. **设置**：勾选 **“如果任务失败，按以下频率重新启动”**，间隔 `1 分钟`，尝试 `3` 次。
8. 确定，输入 Windows 密码。

> 使用 `pythonw.exe` 可静默运行，不弹黑色窗口。
---

## 注意事项

## 注意事项

1. **设备数量限制**  
   学校服务器启用了 MAC 绑定，通常限制一个账号同时在线一台手机 + 一台电脑。  
   如果登录失败并提示“设备超限”，请先登录校园网自助服务页面解绑不用的设备。

2. **MAC 地址必须正确**  
   脚本中填写的 MAC 必须是你当前电脑连接校园网网卡的真实 MAC。  
   如果更换网卡或电脑，需要同步修改。

3. **认证服务器 IP 可能变化**  
   如果学校升级网络，`auth_host`、`auth_path` 或参数可能改变。  
   此时需要重新抓包，更新配置和请求参数。

4. **浏览器指纹参数**  
   脚本中随机生成，如果服务器严格校验，可替换为抓包中获取的固定值。

5. **Referer 中的 nasip 和 userlocation**  
   这两个值来自抓包，目前写死。如果换楼或换 AP 后无法登录，请重新抓包更新。

6. **平台限制**  
   脚本依赖 Windows 的 `netsh` 和 PowerShell 获取网卡信息，目前仅支持 Windows。  
   如果在 Linux / macOS 上运行，需要修改 `get_active_interface()` 和 `get_wifi_ssid()`。
---

## 免责声明

本脚本仅供学习与交流使用，请遵守学校网络管理规定。  
使用本脚本造成的任何后果（包括但不限于账号被封、网络中断等）由使用者自行承担。  
请勿将本脚本用于商业用途或非法目的。

---

## 致谢

再次感谢 [xiaoxiaoguai-yyds](https://github.com/xiaoxiaoguai-yyds) 学长，以及所有参与测试的同学们。
后续可能会研究面对学校校园网多设备登录限制的方法与软路由系统的登录脚本，敬请期待。

---

_Last updated: 2026-10-05_
