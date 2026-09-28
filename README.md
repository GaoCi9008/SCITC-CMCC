# 校园网自动登录脚本（四川信息职业技术学院 · 中国移动）

基于 [xiaoxiaoguai-yyds](https://github.com/xiaoxiaoguai-yyds) 学长的《[SCITC-xiaoyuanwifi](https://github.com/xiaoxiaoguai-yyds/SCITC-xiaoyuanwifi)》中国电信校园网登录脚本项目为灵感编写。

一个用于自动登录校园网 Web Portal 认证的 Python 脚本。  
基于实际wireshark抓包分析编写，适用于四川信息职业技术学院（SCITC）的 **中国移动** 校园网认证系统。

---

## 功能简介

- 向校园网认证服务器提交账号、密码、MAC 等参数。
- 登录成功后弹窗提示，失败时显示服务器返回信息。
- 可修改配置后用于其他类似 Web Portal 认证的校园网。

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

打开 `校园网.py`，找到 `CONFIG` 配置区，修改以下三项：

```python
CONFIG = {
    "auth_host": "10.2.1.27",          # 认证服务器 IP（如学校更换请修改）
    "auth_path": "/api/portal/webauth", # 登录接口路径
    "user_id": "你的账号",               # 校园网账号
    "passwd": "你的密码",                # 校园网密码
    "wlanacname": "SCITC-BRAS-ME60",    # 抓包得到的值，一般不用改
    "mac": "你的MAC地址",                # 本机连接校园网网卡的 MAC
    "timeout": 8,
}
```

### 如何查看本机 MAC 地址

Windows：

1. 按 `Win + R`，输入 `cmd`，回车。
2. 运行 `ipconfig /all` 或 `getmac /v`。
3. 找到你连接校园网的那张网卡（有线或无线），复制其物理地址。
4. 格式示例：`a8:e2:91:13:c8:e4`

> 注意：如果你有多张网卡（有线、无线、虚拟机），请填写实际连接校园网的那张。

---

## 使用方法

1. 修改好 `CONFIG` 中的账号、密码、MAC。
2. 确保电脑已连接校园网 WiFi 或网线（但尚未认证）。
3. 运行脚本：

```bash
python 校园网.py
```

4. 脚本会自动提交登录请求，并弹窗提示结果。

---

## 注意事项

1. **设备数量限制**  
      学校服务器启用了 MAC 绑定，通常限制一个账号同时在线一台手机 + 一台电脑。  
      如果登录失败并提示“设备超限”，请先登录校园网自助服务页面解绑不用的设备。

2. **MAC 地址必须正确**  
      脚本中填写的 MAC 必须是你当前电脑连接校园网网卡的真实 MAC。  
      如果更换网卡或电脑，需要同步修改。

3. **认证服务器 IP 可能变化**  
      如果学校升级网络，`auth_host`、`auth_path` 或参数可能改变。  
      此时需要重新抓包，更新 `CONFIG` 和请求参数。

4. **`browserFingerprint` 参数**  
      脚本中随机生成，如果服务器严格校验，可替换为抓包中获取的固定值。

5. **`Referer` 中的 `nasip` 和 `userlocation`**  
      这两个值来自抓包，目前写死。如果换楼或换 AP 后无法登录，请重新抓包更新。

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

_Last updated: 2026-09-28_
