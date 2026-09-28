from datetime import datetime
import socket
import uuid
import hashlib
import tkinter as tk
from tkinter import messagebox

import requests


# ==================== 配置区（请修改这里） ====================
CONFIG = {
    # 认证服务器地址
    "auth_host": "10.2.1.27",
    # 登录接口路径
    "auth_path": "/api/portal/webauth",

    # 校园网账号和密码
    "user_id": "你的账号",
    "passwd": "你的密码",

    # 认证服务器参数
    "wlanacname": "SCITC-BRAS-ME60",

    # 你的 MAC 地址，格式：aa:bb:cc:dd:ee:ff
    "mac": "你的MAC地址",

    # 请求超时（秒）
    "timeout": 8,
}
# =============================================================


def get_local_ip():
    """获取本机 IP（用于和外网通信的网卡 IP）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"[错误] 获取本机 IP 失败: {e}")
        return None


def make_browser_fingerprint():
    """生成一个随机的浏览器指纹（32 位十六进制字符串）"""
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()


def show_popup(title, text, is_error=False):
    """弹窗提示"""
    root = tk.Tk()
    root.withdraw()
    if is_error:
        messagebox.showerror(title, text)
    else:
        messagebox.showinfo(title, text)
    root.destroy()


def validate_config():
    """校验配置是否填写完整"""
    errors = []
    if CONFIG["user_id"] == "你的账号" or not CONFIG["user_id"]:
        errors.append("请在 CONFIG 中填写校园网账号（user_id）")
    if CONFIG["passwd"] == "你的密码" or not CONFIG["passwd"]:
        errors.append("请在 CONFIG 中填写校园网密码（passwd）")
    if CONFIG["mac"] == "你的MAC地址" or not CONFIG["mac"]:
        errors.append("请在 CONFIG 中填写你的 MAC 地址（mac）")
    elif ":" not in CONFIG["mac"]:
        errors.append("MAC 地址格式错误，应为 aa:bb:cc:dd:ee:ff")

    if errors:
        msg = "\n".join(errors)
        show_popup("配置错误", f"请先修改代码中的配置：\n\n{msg}", is_error=True)
        return False
    return True


def main():
    # 1. 校验配置
    if not validate_config():
        return

    # 2. 获取本机 IP
    local_ip = get_local_ip()
    if not local_ip:
        show_popup("错误", "无法获取本机 IP 地址。", is_error=True)
        return

    mac = CONFIG["mac"]
    print(f"[信息] 本机 IP : {local_ip}")
    print(f"[信息] 本机 MAC: {mac}")

    # 3. 构造请求
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

    # 4. 发送请求
    try:
        response = requests.post(
            url,
            data=data,
            headers=headers,
            timeout=CONFIG["timeout"],
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[错误] 请求失败: {e}")
        show_popup("登录失败", f"请求异常：\n{e}", is_error=True)
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5. 解析返回结果
    try:
        result = response.json()
    except Exception:
        print("[错误] 返回不是 JSON")
        print("返回内容片段：", response.text[:300])
        show_popup(
            "登录结果未知",
            f"返回内容不是 JSON，无法判断。\n\n片段：\n{response.text[:300]}",
            is_error=True,
        )
        return

    if result.get("success") is True and result.get("code") == 200:
        print("[成功] 登录成功")
        show_popup(
            "登录成功",
            f"登录成功！\n\n当前 IP：{local_ip}\n当前 MAC：{mac}\n当前时间：{now_str}",
        )
    else:
        msg = result.get("message", "未知错误")
        print(f"[失败] {msg}")
        print("完整返回：", result)
        show_popup(
            "登录失败",
            f"服务器返回失败：\n{msg}\n\n完整返回：\n{result}",
            is_error=True,
        )


if __name__ == "__main__":
    main()