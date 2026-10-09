import os
import json
import re
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
    "user_id": "账号",
    "passwd": "密码",

    # 认证参数
    "wlanacname": "SCITC-BRAS-ME60",

    # 本机 MAC 地址（支持大小写，支持 : 或 - 分隔）
    "mac": "你的MAC",

    # 校园网 WiFi 名称（可选，留空则不校验）
    "campus_ssid": "",

    # 请求超时（秒）
    "timeout": 8,

    # 失败重试
    "retry_times": 3,
    "retry_interval": 5,

    # 循环检查间隔（秒）
    "check_interval": 60,

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


def log(msg):
    """写入日志并打印"""
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"写入日志失败: {e}")


def normalize_mac(mac):
    """
    将 MAC 地址标准化为小写冒号分隔格式。
    支持输入：aa:bb:cc:dd:ee:ff、AA-BB-CC-DD-EE-FF、aabbccddeeff 等。
    返回标准化后的字符串，若格式无效则返回 None。
    """
    cleaned = re.sub(r'[^0-9a-fA-F]', '', mac)
    if len(cleaned) != 12:
        return None
    return ':'.join(cleaned[i:i+2] for i in range(0, 12, 2)).lower()


def get_local_ip():
    """获取本机默认出口 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        log(f"获取本机 IP 失败: {e}")
        return None


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
    """检测外网是否真正可达（避免被 Portal 重定向误判）"""
    host = CONFIG["internet_check_host"]
    if host.startswith("http://") or host.startswith("https://"):
        url = host
    else:
        url = f"http://{host}"

    try:
        r = requests.get(url, timeout=5, allow_redirects=False)

        if r.status_code == 204:
            return True

        if r.status_code == 200:
            text = r.text.lower()
            portal_keywords = [
                "portal", "webauth", "认证", "登录", "校园网",
                CONFIG["auth_host"].lower()
            ]
            if any(kw in text for kw in portal_keywords):
                return False
            return True

        if 300 <= r.status_code < 400:
            loc = r.headers.get("Location", "").lower()
            if any(kw in loc for kw in ["portal", "webauth", "auth", CONFIG["auth_host"].lower()]):
                return False
            return True

        return False

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

    mac_input = CONFIG.get("mac", "")
    if mac_input in ("", "你的MAC地址"):
        errors.append("请填写本机 MAC 地址（mac）")
    else:
        normalized = normalize_mac(mac_input)
        if not normalized:
            errors.append("MAC 地址格式错误，应为 12 位十六进制字符，可带 : 或 - 分隔")
        else:
            CONFIG["mac"] = normalized  # 自动标准化

    if errors:
        for e in errors:
            log(f"配置错误: {e}")
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
    except requests.RequestException as e:
        log(f"请求失败: {e}")
        return False

    try:
        result = response.json()
    except Exception:
        log(f"返回不是 JSON: {response.text[:200]}")
        return False

    if result.get("success") is True and result.get("code") == 200:
        redirect_url = result.get("result", {}).get("redirect")
        if redirect_url:
            full_url = f"http://{CONFIG['auth_host']}{redirect_url}"
            try:
                requests.get(full_url, timeout=5)
            except Exception:
                pass
        log("登录成功")
        return True
    else:
        msg = result.get("message", "未知错误")
        log(f"登录失败: {msg} | 完整返回: {result}")
        return False


def try_login():
    """尝试登录一次（带重试）"""
    local_ip = get_local_ip()
    if not local_ip:
        log("无法获取本机 IP")
        return False

    mac = CONFIG["mac"]

    for i in range(1, CONFIG["retry_times"] + 1):
        if do_login(local_ip, mac):
            return True
        if i < CONFIG["retry_times"]:
            time.sleep(CONFIG["retry_interval"])

    log(f"多次尝试后仍登录失败 | IP: {local_ip} | MAC: {mac}")
    return False


def main():
    """入口：启动时判断是否在校园网，不在则直接退出"""
    # 删除上次运行的日志
    if os.path.exists(LOG_PATH):
        try:
            os.remove(LOG_PATH)
        except Exception:
            pass

    log("=" * 50)
    log("脚本启动")

    if not validate_config():
        return

    if not is_campus_network():
        log("启动时不在校园网环境，退出")
        return

    while True:
        try:
            if not is_campus_network():
                log("检测到已离开校园网，退出")
                return

            if is_internet_ok():
                pass
            else:
                log("检测到断网，开始重新登录")
                try_login()

        except Exception as e:
            log(f"循环异常: {e}")

        time.sleep(CONFIG["check_interval"])


if __name__ == "__main__":
    main()
