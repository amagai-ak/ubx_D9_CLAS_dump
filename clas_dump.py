#!/usr/bin/env python3

"""
UBX プロトコルを解析してCLASの情報をダンプするスクリプト
u-blox D9 モジュール用
D9モジュールをUSBで接続し，シリアルポート経由でUBXメッセージを受信します．
windowsでの実行例：python clas_dump.py --port com5
linuxでの実行例：python clas_dump.py --port /dev/ttyACM2
author: amagai

メッセージ詳細は下記参照
https://content.u-blox.com/sites/default/files/u-blox-D9-QZS-1.01_InterfaceDescription_UBX-21031777.pdf

"""

import argparse
import serial
import sys
import time


def main(args):
    try:
        ser = serial.Serial(args.port, args.baudrate, timeout=1)
    except serial.SerialException as e:
        print(f"Failed to open serial port: {e}", file=sys.stderr)
        return 1
    if args.csv:
        print("date,unix_time,ch,svid,cno,biterror,err_status")

    # UBXメッセージの受信と解析ループ
    try:
        while True:
            # UBXメッセージのヘッダを読み込む
            header = ser.read(6)
            if len(header) < 6:
                continue

            # 受信時刻を記録する
            receive_time = time.time()
            log_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(receive_time))

            # UBXヘッダの解析
            if header[0:2] != b'\xb5\x62':
                continue  # UBXシグネチャでない場合はスキップ
            # print(f"ヘッダ: {header.hex()}")
            msg_class = header[2]
            msg_id = header[3]
            length = int.from_bytes(header[4:6], byteorder='little')

            # メッセージ本体とチェックサムを読み込む
            payload = ser.read(length + 2)
            if len(payload) < length + 2:
                continue

            # チェックサムを計算して検証
            ck_a = 0
            ck_b = 0
            for byte in header[2:] + payload[:-2]:
                ck_a = (ck_a + byte) & 0xFF
                ck_b = (ck_b + ck_a) & 0xFF
            if ck_a != payload[-2] or ck_b != payload[-1]:
                # print("チェックサムエラー")
                continue
            # CLASメッセージのみ処理
            if msg_class == 0x02:  # CLASクラス
                svid = payload[1]
                cno = int.from_bytes(payload[2:4], byteorder='little') * pow(2, -8)
                biterror = payload[9]
                chinfo = int.from_bytes(payload[10:12], byteorder='little')
                # ch番号は chinfoの bit9-8
                chno = (chinfo >> 8) & 0x03
                # エラーステータスは chinfoの bit13-12
                # 0: unknown, 1: error-free, 2: errorneous
                err_status = (chinfo >> 12) & 0x03
                # msgNameは chinfoのbit10. 0=L6D, 1=L6E
                msg_name = (chinfo >> 10) & 0x01
                if args.csv:
                    print(f"{log_date},{receive_time:.3f},{chno},{svid},{cno:.2f},{biterror},{err_status}")
                else:
                    print(f"受信日時: {log_date}")
                    print(f"unixtime: {receive_time:.3f}")
                    print(f"CLASメッセージ: ID={msg_id:02X}, 長さ={length}")
                    print(f"ペイロード: {payload[:-2].hex()}")
                    print(f"チェックサム: {payload[-2:].hex()}")
                    print(f"衛星ID: {svid}, C/N0: {cno:.2f}, ビットエラー: {biterror}, チャネル: {chno}, エラーステータス: {err_status}, メッセージ名: {msg_name}")
                    print("-" * 40)
    except KeyboardInterrupt:
        print("Terminating...", file=sys.stderr)
    finally:
        ser.close()
    return 0


if __name__ == "__main__":
    # 利用するシリアルポートを引数から取得
    parser = argparse.ArgumentParser(description="UBX CLAS Dump Tool")
    parser.add_argument("--port", required=True,
                        help="シリアルポートのパス (例: /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int,
                        default=38400,
                        help="シリアルポートのボーレート (デフォルト: 38400)")
    parser.add_argument("--csv", action="store_true",
                        help="CSV形式で出力")
    args = parser.parse_args()
    sys.exit(main(args))
