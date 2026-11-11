"""
手动逐步测试 /mask 接口，用来替代容易在PowerShell里出问题的一行命令
（命令行里URL带 & 符号，PowerShell对这类特殊字符的处理和bash不一样，
容易悄无声息地什么都没发出去）。这是一个正经的脚本文件，直接跑就行，
不用自己拼命令。

Usage:
    python test_mask_manual.py --ip 172.20.10.2
"""
import argparse
import urllib.request
import urllib.error


def call(url):
    print(f"GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode()
            print(f"  HTTP {resp.status}: {body}")
    except urllib.error.URLError as e:
        print(f"  失败: {e}")
    except Exception as e:
        print(f"  出错: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="ESP32CAM的IP地址")
    parser.add_argument("--x", type=int, default=0, help="遮挡区域左上角x坐标，默认0")
    parser.add_argument("--y", type=int, default=40, help="遮挡区域左上角y坐标，默认40（屏幕下半部分，避开开机就有的WiFi连接信息文字，避免视觉上重叠混淆）")
    parser.add_argument("--w", type=int, default=128, help="遮挡区域宽度，默认128（整行宽）")
    parser.add_argument("--h", type=int, default=20, help="遮挡区域高度，默认20")
    args = parser.parse_args()
    base = f"http://{args.ip}"
    x, y, w, h = args.x, args.y, args.w, args.h

    print("=== 第一步：画遮挡块 ===")
    call(f"{base}/mask?x={x}&y={y}&w={w}&h={h}&on=1")
    input(f"\n>>> 现在看OLED屏幕 (x={x},y={y},w={w},h={h}) 这块区域，应该出现一片'/'密集填充的图案。\n"
          ">>> 看清楚之后，回到这里按一下回车，继续清除...\n")

    print("=== 第二步：清除遮挡块 ===")
    call(f"{base}/mask?x=0&y=0&w=128&h=64&on=0")
    print("\n完成。")


if __name__ == "__main__":
    main()
