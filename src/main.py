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

def main():
    print("="*45)
    print("     uConsole Network Toolkit v0.2")
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

    wifi = get_wifi_info(interface)

    if wifi:
        print()
        print("[Wi-Fi]")

        for key, value in wifi.items():

            print(f"{key:<10}:{value}")

    # --------------------------------------------------------
    # 4. Ping 测试
    # --------------------------------------------------------


    # 测试网关
    gateway_ping = None

    if gateway_ping != "Unknow":
        gateway_ping = ping_test(gateway)

    # 互联网测试
    internet_ping = ping_test("1.1.1.1")
    
    # 测试 DNS
    dns_ok = dns_test()

    # 连通性测试
    internet_ok = ping_test("1.1.1.1")

    # 提取连通性状态
    gateway_ok = (
        gateway_ping["success"]
        if gateway_ping is not None
        else False
        )
    
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

    elif dns_ok:
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

    print()
    print("=" * 45)

   
if __name__ == "__main__": main()