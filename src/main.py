import subprocess
import socket
import re
from pathlib import Path

def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()

    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Command Error: {error}")
        return ""

def get_Network_info():

    route = run_command([
        "ip", "route", "get", "1.1.1.1"
    ])

    interface = "Unknown"
    ip_address = "Unknown"
    gateway = "Unknown"

    interface_match = re.search(
        r"dev\s+(\S+)", route
    )

    ip_match = re.search(
        r"src\s+(\S+)", route
    )

    if interface_match:
        interface = interface_match.group(1)

    if ip_match:
        ip_address = ip_match.group(1)

    default_route = run_command([
        "ip", "route", "show", "default"
    ])

    gateway_match = re.search(
        r"default via\s+(\S+)",
        default_route
    )

    if gateway_match:
        gateway = gateway_match.group(1)

    return interface, ip_address, gateway

def get_dns_servers():
    path = Path("/etc/resolv.conf")

    if not path.exists():
        return []

    dns_servers = []

    for line in path.read_text().splitlines():

        line = line.strip()

        if line.startswith("nameserver"):
            parts = line.split()

            if len(parts) >= 2:
                dns_servers.append(parts[1])

    return dns_servers

def show_dns_servers():
    dns_servers = get_dns_servers()
    if not dns_servers:
        print("No DNS servers found")
    else:
        print(dns_servers)

def get_wifi_info(interface):
    output = run_command(["iw","dev",interface,"link"])
    if not output or "Not connected" in output:
        return None
    wifi = {}
    ssid = re.search(r"SSID:\s+(.+)",output)
    signal = re.search(r"signal:\s+(-?\d+)\s+dBm",output)
    tx_rate = re.search(r"tx bitrate:\s+(.+)",output)

    if ssid:
        wifi["SSID"] = ssid.group(1)
    if signal:
        wifi["Signal"] = signal.group(1)
    if tx_rate:
        wifi["TX Rate"] = tx_rate.group(1)

    return wifi

def show_ping_result(label, data):

    print()
    print(f"[{label}]")

    if data is None:
        print("Status      : Unknown")
        return

    if data["error"]:
        status = "ERROR"
    elif data["success"]:
        status = "OK"
    else:
        status = "FAIL"

    print(f"Status      : {status}")
    print(f"Target      : {data['host']}")

    if data["sent"] is not None:
        print(f"Sent        : {data['sent']}")
        print(f"Received    : {data['received']}")
    else:
        print("Packets     : Unknown")

    if data["packet_loss"] is not None:
        print(f"Packet Loss : {data['packet_loss']}%")
    else:
        print("Packet Loss : Unknown")

    if data["avg"] is not None:
        print(f"Minimum RTT : {data['min']} ms")
        print(f"Average RTT : {data['avg']} ms")
        print(f"Maximum RTT : {data['max']} ms")
        print(f"Mdev        : {data['mdev']} ms")
    else:
        print("RTT         : Unknown")

    if data["error"]:
        print(f"Error       : {data['error']}")


def ping_test(host):

    # 初始化结果字典
    ping_data = {
        "host": host,
        "success": False,
        "sent": None,
        "received": None,
        "packet_loss": None,
        "min": None,
        "avg": None,
        "max": None,
        "mdev": None,
        "error": None
    }

    # 执行 Ping
    try:
        result = subprocess.run(
            ["ping", "-c", "4", "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=15
        )

    except subprocess.TimeoutExpired:
        ping_data["error"] = "Ping timed out"
        return ping_data

    except OSError as error:
        ping_data["error"] = str(error)
        return ping_data

    output = result.stdout

    # 提取发送与接收的数据包数量
    packet_match = re.search(
        r"(\d+)\s+packets?\s+transmitted,\s*"
        r"(\d+)\s+(?:packets?\s+)?received",
        output
    )

    if packet_match:
        ping_data["sent"] = int(packet_match.group(1))
        ping_data["received"] = int(packet_match.group(2))

        ping_data["success"] = (
            ping_data["received"] > 0
        )

    # 提取丢包率
    loss_match = re.search(
        r"(\d+(?:\.\d+)?)%\s+packet loss",
        output
    )

    if loss_match:
        ping_data["packet_loss"] = float(
            loss_match.group(1)
        )

    # 提取 RTT 数据
    rtt_match = re.search(
        r"rtt\s+min/avg/max/mdev\s*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
        output
    )

    if rtt_match:
        ping_data["min"] = float(rtt_match.group(1))
        ping_data["avg"] = float(rtt_match.group(2))
        ping_data["max"] = float(rtt_match.group(3))
        ping_data["mdev"] = float(rtt_match.group(4))

    # 判断是否存在执行或解析错误
    if packet_match is None or loss_match is None:
        ping_data["error"] = (
            result.stderr.strip()
            or "Unable to parse Ping statistics"
        )

    elif result.returncode not in (0, 1):
        ping_data["error"] = (
            result.stderr.strip()
            or f"Ping exited with code {result.returncode}"
        )

    return ping_data


def dns_test():
    try:
        socket.gethostbyname("example.com")
        return True
    except socket.gaierror:
        return False

def get_wifi_details():
    wifi_output = run_command(["iw","dev","wlan0","link"])

    if wifi_output.startswith("Not connected."):
        return{
            "connected": False,
            "ssid": None,
            "frequency": None,
            "band": None,
            "channel": None,
            "signal": None,
            "signal_grade": None,
            "tx_bitrate": None,
            "tx_status": None,
            "rx_bitrate": None
        }

    ssid_match = re.search(r"SSID:\s*(.+)",wifi_output)
    
    freq_match = re.search(r"freq:\s*(\d+)",wifi_output)
    frequency = int(freq_match.group(1)) if freq_match else None
    band = get_wifi_band(frequency)
    channel = get_wifi_channel(frequency)

    signal_match = re.search(r"signal:\s*(-?\d+)",wifi_output)
    signal = float(signal_match.group(1)) if signal_match else None
    signal_grade = get_signal_grade(signal)

    tx_match = re.search(r"tx bitrate:\s*([\d.]+)",wifi_output)
    tx_bitrate = float(tx_match.group(1)) if tx_match else None
    tx_status = get_tx_status(tx_bitrate)

    rx_match = re.search(r"rx bitrate:\s*([\d.]+)",wifi_output)
    rx_bitrate = float(rx_match.group(1)) if rx_match else None

    return{
        "connected": bool(ssid_match),
        "ssid": str(ssid_match.group(1).strip()) if ssid_match else None,
        "frequency": frequency,
        "band": band,
        "channel": channel,
        "signal": signal,
        "signal_grade": signal_grade,
        "tx_bitrate": tx_bitrate,
        "tx_status": tx_status,
        "rx_bitrate": rx_bitrate
    }

def get_wifi_band(frequency):

    if frequency is None:
        return "Unknown"

    if 2400 <= frequency <= 2500:
        return "2.4Ghz"
    elif 5000 <= frequency <= 5925:
        return "5Ghz"
    elif 5925<= frequency <= 7125:
        return "6Ghz"

    else:
        return "Unknown"

def get_wifi_channel(frequency):

    if frequency is None:
        return None

    if 2412 <= frequency <= 2472:
        if (frequency - 2412) % 5 == 0:
            return (frequency - 2407) // 5

    elif frequency == 2484:
        return 14

    elif 5000 <= frequency < 5925:
        if (frequency - 5000) % 5 == 0:
            return (frequency - 5000) // 5

    return None

def get_signal_grade(signal):

    if signal is None:
        return "Unknown"

    if signal >= -50:
        return "极好 Excellent"

    elif signal >= -60:
        return "好 Good"

    elif signal >= -70:
        return "较好 Fair"

    elif signal >= -80:
        return "弱 Weak"

    else:
        return "差 Poor"

def get_tx_status(tx_bitrate):

    if tx_bitrate is None:
        return "Unknown"

    elif tx_bitrate <= 0:
        return "Invalid"

    else:
        return "Available"

def diagnose_wifi(wifi, gateway_ping):

    issues = []
    notes = []

    # 1. Check Wi-Fi connection
    if not wifi.get("connected", False):
        issues.append("Wi-Fi is disconnected")

        return {
            "status": "Disconnected",
            "issues": issues,
            "notes": notes
        }

    # 2. Check signal strength
    signal = wifi.get("signal")

    if signal is None:
        notes.append("Wi-Fi signal is unavailable")

    elif signal < -80:
        issues.append("Very weak Wi-Fi signal")

    elif signal < -70:
        issues.append("Weak Wi-Fi signal")

    # 3. Check TX / RX bitrate availability
    tx = wifi.get("tx_bitrate")
    rx = wifi.get("rx_bitrate")

    if tx is None:
        notes.append("TX bitrate is unavailable")
    elif tx <= 0:
        issues.append("Invalid TX bitrate")

    if rx is None:
        notes.append("RX bitrate is unavailable")
    elif rx <= 0:
        issues.append("Invalid RX bitrate")

    # 4. Check gateway Ping
    if gateway_ping is None:
        notes.append("Gateway Ping was not performed")

    elif gateway_ping.get("error"):
        notes.append("Gateway Ping test error: " + str(gateway_ping["error"]))

    else:
        loss = gateway_ping.get("packet_loss")

        if loss is None:
            notes.append("Gateway packet loss is unavailable")

        elif loss == 100:
            issues.append("Gateway did not respond")

        elif loss > 0:
            issues.append("Gateway packet loss detected")

    # 5. Determine overall status
    if issues:
        status = "Warning"
    else:
        status = "OK"

    return {
        "status": status,
        "issues": issues,
        "notes": notes
    }
    
def main():
    print("="*45)
    print("     uConsole Network Toolkit v0.3")
    print("="*45)

    # --------------------------------------------------------
    # 1. 获取网络基础信息
    # --------------------------------------------------------

    interface, ip_address, gateway=(get_Network_info())

    print()

    print(f"Hostname    :{socket.gethostname()}")
    print(f"Interface   :{interface}")
    print(f"IPv4        :{ip_address}")
    print(f"Gateway     :{gateway}")

    # --------------------------------------------------------
    # 2. DNS 服务器信息
    # --------------------------------------------------------

    dns_servers = get_dns_servers()
    
    if  dns_servers:
        print(f"DNS         :{','.join(dns_servers)}")
    else:
        print("DNS          ：Unknown")

    # --------------------------------------------------------
    # 3. Wi-Fi 信息
    # --------------------------------------------------------

    wifi = get_wifi_details()

    if wifi:
        print()
        print("[Wi-Fi Diagnostics]")

        for key, value in wifi.items():

            print(f"{key:<15}:{value}")

    # --------------------------------------------------------
    # 4. Ping 测试
    # --------------------------------------------------------


    # 测试网关
    gateway_ping = None

    if gateway_ping != "Unknown":
        gateway_ping = ping_test(gateway)

    # 互联网测试
    internet_ping = ping_test("1.1.1.1")
    
    # 测试 DNS
    dns_ok = dns_test()

    # 连通性测试
    internet_ok = internet_ping["success"]

    # 提取连通性状态
    gateway_ok = (
        gateway_ping["success"]
        if gateway_ping is not None
        else False
    )

    internet_ok = internet_ping["success"]

    print()
    print("[Connectivity]")

    if gateway_ping is None:
        print("Gateway     : Unknown")
    else:
        print(f"Gateway     : {'OK' if gateway_ok else 'FAIL'}")

    print(f"Internet    : {'OK' if internet_ok else 'FAIL'}")
    print(f"DNS         : {'OK' if dns_ok else 'FAIL'}")
   
    # --------------------------------------------------------
    # 6. 显示 Ping 统计
    # --------------------------------------------------------

    show_ping_result("Gateway Ping", gateway_ping)

    show_ping_result("Internet Ping", internet_ping)

    # --------------------------------------------------------
    # 7. 自动诊断
    # --------------------------------------------------------

    print()
    print("[Diagnosis]")

    if gateway_ping is None:
        print("Gateway information unavailable.")

    elif gateway_ping["error"]:
        print("Gateway Ping could not be completed.")

    elif not gateway_ok:
        print("Gateway did not respond to ICMP Ping.")

    elif (
        gateway_ping["packet_loss"] is not None
        and gateway_ping["packet_loss"] > 0
    ):
        print("Gateway packet loss detected.")

    # 公网 Ping 诊断
    if internet_ping["error"]:
        print("Internet Ping test encountered an error.")

    elif not internet_ok:
        print("No ICMP response from 1.1.1.1.")

    elif (
        internet_ping["packet_loss"] is not None
        and internet_ping["packet_loss"] > 0
    ):
        print("Internet packet loss detected.")

    if (
        gateway_ok
        and internet_ok
        and dns_ok
        and gateway_ping["packet_loss"] == 0
        and internet_ping["packet_loss"] == 0
    ):
        print("Basic Ping and DNS checks passed.")

    # DNS 诊断
    if not dns_ok:
        print("DNS resolution failed.")

    # 平均延迟初步提醒
    # 150ms 只是参考阈值，并不是通用故障标准

    if (
        internet_ping["avg"] is not None
        and internet_ping["avg"] >= 150
    ):
        print("High average RTT detected (>=150 ms).")

# --------------------------------------------------------
# 8. Wi-Fi 综合诊断
# --------------------------------------------------------
    wifi_diagnosis = diagnose_wifi(wifi, gateway_ping)

    print()
    print("[Wi-Fi Diagnosis]")
    print(f"Status : {wifi_diagnosis['status']}")

    for issue in wifi_diagnosis["issues"]:
        print(f"Issue  : {issue}")

    for note in wifi_diagnosis["notes"]:
        print(f"Note   : {note}")

    print()
    print("=" * 45)

   
if __name__ == "__main__": main()