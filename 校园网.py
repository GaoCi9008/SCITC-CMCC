import os
import json
import socket
import subprocess
import hashlib
import uuid
from datetime import datetime
import time

import requests


# ==================== 配置区（请修改这里） ====================
CONFIG = {
    # 认证服务器
    "auth_host": "10.2.1.27",
    "auth_path": "/api/portal/webauth",

    # 校园网账号密码
    "user_id": "18383912694",
    "passwd": "912694",

    # 认证参数
    "wlanacname": "SCITC-BRAS-ME60",

    # 有线网卡 MAC
    "mac_ethernet": "b0:25:aa:7e:b4:ae",

    # 无线网卡 MAC
    "mac_wireless": "a8:e2:91:13:c8:e4",

    # 校园网 WiFi 名称（可选，留空则不校验）
    "campus_ssid": "",

    # 请求超时（秒）
    "timeout": 8,

    # 失败重试
    "retry_times": 3,
    "retry_interval": 5,

    # 循环检查间隔（秒）
    "check_interval": 900,

    # 外网检测地址
    "internet_check_host": "www.baidu.com",
    "internet_check_port": 80,

    # 日志文件
    "log_file": "campus_login.log",
}
# =============================================================


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(SCRIPT_DIR, CONFIG["log_file"])

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def log_error(msg):
    """只记录错误"""
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [ERROR] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"写入日志失败: {e}")


def get_local_ip():
    """获取本机默认出口 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        log_error(f"获取本机 IP 失败: {e}")
        return None


def get_active_interface():
    """获取当前活动网卡信息"""
    local_ip = get_local_ip()
    if not local_ip:
        return None

    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for name, addr_list in addrs.items():
            has_ip = False
            mac = None
            for a in addr_list:
                if a.family == socket.AF_INET and a.address == local_ip:
                    has_ip = True
                if a.family == psutil.AF_LINK and a.address:
                    mac = a.address.replace("-", ":").lower()
            if has_ip and mac:
                is_wireless = any(
                    kw in name.lower()
                    for kw in ["wi-fi", "wlan", "wireless", "无线", "802.11"]
                )
                return {
                    "name": name,
                    "desc": name,
                    "mac": mac,
                    "wireless": is_wireless,
                }
    except ImportError:
        pass
    except Exception as e:
        log_error(f"psutil 获取网卡信息失败: {e}")

    try:
        cmd = (
            f"Get-NetIPAddress -IPAddress {local_ip} -ErrorAction SilentlyContinue | "
            f"Get-NetAdapter | "
            f"Select-Object Name,InterfaceDescription,MacAddress | ConvertTo-Json -Compress"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd],
            encoding="utf-8",
            errors="ignore",
            creationflags=CREATE_NO_WINDOW,
        ).strip()

        if output:
            info = json.loads(output)
            if isinstance(info, list):
                info = info[0]
            name = info.get("Name", "") or ""
            desc = info.get("InterfaceDescription", "") or ""
            mac = (info.get("MacAddress", "") or "").replace("-", ":").lower()
            text = (name + " " + desc).lower()
            is_wireless = any(
                kw in text
                for kw in ["wi-fi", "wlan", "wireless", "无线", "802.11"]
            )
            return {
                "name": name,
                "desc": desc,
                "mac": mac,
                "wireless": is_wireless,
            }
    except Exception as e:
        log_error(f"PowerShell 获取网卡信息失败: {e}")

    return None


def choose_mac():
    """根据当前活动网卡选择 MAC"""
    info = get_active_interface()

    if info:
        actual = info["mac"]
        eth = CONFIG["mac_ethernet"].lower()
        wl = CONFIG["mac_wireless"].lower()

        if actual == eth:
            return CONFIG["mac_ethernet"]
        if actual == wl:
            return CONFIG["mac_wireless"]

        if info["wireless"]:
            return CONFIG["mac_wireless"]
        else:
            return CONFIG["mac_ethernet"]

    return CONFIG["mac_ethernet"]


def get_wifi_ssid():
    """获取当前 WiFi 名称"""
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            encoding="utf-8",
            errors="ignore",
            creationflags=CREATE_NO_WINDOW,
        )
        for line in output.splitlines():
            if "SSID" in line and "BSSID" not in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def is_campus_network():
    """判断是否在校园网"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((CONFIG["auth_host"], 80))
        s.close()
        reachable = True
    except Exception:
        reachable = False

    if not reachable:
        return False

    if CONFIG["campus_ssid"]:
        ssid = get_wifi_ssid()
        if ssid != CONFIG["campus_ssid"]:
            return False

    return True


def is_internet_ok():
    """检测外网是否可达"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((CONFIG["internet_check_host"], CONFIG["internet_check_port"]))
        s.close()
        return True
    except Exception:
        return False


def make_browser_fingerprint():
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()


def validate_config():
    errors = []
    if CONFIG["user_id"] in ("", "你的账号"):
        errors.append("请填写校园网账号（user_id）")
    if CONFIG["passwd"] in ("", "你的密码"):
        errors.append("请填写校园网密码（passwd）")
    if CONFIG["mac_ethernet"] in ("", "aa:bb:cc:dd:ee:01") and \
       CONFIG["mac_wireless"] in ("", "aa:bb:cc:dd:ee:02"):
        errors.append("请至少填写一个网卡 MAC")

    if errors:
        for e in errors:
            log_error(f"配置错误: {e}")
        return False
    return True


def do_login(local_ip, mac):
    """执行一次登录"""
    url = f"http://{CONFIG['auth_host']}{CONFIG['auth_path']}"

    data = {
        "wlanacname": CONFIG["wlanacname"],
        "wlanuserip": local_ip,
        "mac": mac,
        "userId": CONFIG["user_id"],
        "passwd": CONFIG["passwd"],
        "loginMode": "password",
        "recordTerminalMac": "Y",
        "browserFingerprint": make_browser_fingerprint(),
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0"
        ),
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": f"http://{CONFIG['auth_host']}",
        "Referer": (
            f"http://{CONFIG['auth_host']}/portal/webauth"
            f"?wlanuserip={local_ip}"
            f"&wlanacname={CONFIG['wlanacname']}"
            f"&nasip=10.2.1.13"
            f"&mac={mac}"
            f"&userlocation=ethtrunk/30:1003.1035"
        ),
    }

    try:
        response = requests.post(
            url,
            data=data,
            headers=headers,
            timeout=CONFIG["timeout"],
        )
        response.raise_for_status()
    except requests.RequestException:
        log_error("服务器未响应")
        return False

    try:
        result = response.json()
    except Exception:
        log_error(f"返回不是 JSON: {response.text[:200]}")
        return False

    if result.get("success") is True and result.get("code") == 200:
        return True
    else:
        msg = result.get("message", "未知错误")
        log_error(f"登录失败: {msg} | 完整返回: {result}")
        return False


def try_login():
    """尝试登录一次（带重试）"""
    local_ip = get_local_ip()
    if not local_ip:
        log_error("无法获取本机 IP")
        return False

    mac = choose_mac()

    for i in range(1, CONFIG["retry_times"] + 1):
        if do_login(local_ip, mac):
            return True
        if i < CONFIG["retry_times"]:
            time.sleep(CONFIG["retry_interval"])

    log_error(f"多次尝试后仍登录失败 | IP: {local_ip} | MAC: {mac}")
    return False


def main():
    """入口：启动时判断是否在校园网，不在则直接退出"""
    if not validate_config():
        return

    # 1. 启动时判断是否在校园网，不在则退出
    if not is_campus_network():
        log_error("启动时不在校园网环境，退出")
        return

    # 2. 进入常驻循环
    while True:
        try:
            # 每轮循环也检查是否还在校园网
            if not is_campus_network():
                log_error("检测到已离开校园网，退出")
                return

            # 外网正常，什么都不做
            if is_internet_ok():
                pass
            else:
                # 断网，尝试重新登录
                try_login()

        except Exception as e:
            log_error(f"循环异常: {e}")

        time.sleep(CONFIG["check_interval"])


if __name__ == "__main__":
    main()
