#!/usr/bin/env python3
"""
Hiwonder ArmPi 中继服务 — 运行在树莓派上。

接收来自 Windows 端的 HTTP 请求，将舵机指令通过串口发送给 STM32 控制器。

用法:
    1. 将此文件复制到树莓派上
    2. pip install flask
    3. python hiwonder_server.py [--port 8080] [--serial /dev/ttyAMA0]

API:
    GET  /ping                    — 连接测试
    POST /servo/move              — 移动舵机 {"positions": {"1": 500, "2": 800}, "duration": 1000}
    POST /servo/move_single       — 单舵机 {"servo_id": 1, "position": 500, "duration": 500}
"""

import struct
import time
import argparse
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Hiwonder 总线舵机协议 ─────────────────────────────────────────────────

_HEADER = bytes([0x55, 0x55])
_CMD_SERVO_MOVE = 0x03


def _build_servo_move_cmd(servo_positions: dict, duration: int) -> bytes:
    """
    构建 Hiwonder 总线舵机移动指令。
    帧格式: 55 55 <length> 03 <num_servos> <time_low> <time_high> [<servo_id> <pos_low> <pos_high> ...]
    """
    servo_count = len(servo_positions)
    params = struct.pack('<B', servo_count)
    params += struct.pack('<H', duration)
    for sid, pos in servo_positions.items():
        params += struct.pack('<B', sid)
        params += struct.pack('<H', int(pos))

    length = 2 + len(params)
    return _HEADER + struct.pack('<B', length) + struct.pack('<B', _CMD_SERVO_MOVE) + params


# ─── 串口管理 ──────────────────────────────────────────────────────────────

class SerialBridge:
    def __init__(self, port: str, baud: int = 9600):
        import serial
        self.port = port
        self.baud = baud
        self._ser = None
        self._connect()

    def _connect(self):
        import serial
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=3)
            time.sleep(1)
            logger.info(f'串口已连接: {self.port} ({self.baud})')
        except Exception as e:
            logger.error(f'串口连接失败: {e}')
            raise

    def send(self, data: bytes):
        if self._ser and self._ser.is_open:
            self._ser.write(data)
            logger.debug(f'发送: {data.hex(" ")}')

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()


# ─── Flask 服务 ────────────────────────────────────────────────────────────

app = Flask(__name__)
bridge: SerialBridge = None  # type: ignore


@app.route('/ping')
def ping():
    ok = bridge.is_open() if bridge else False
    return jsonify({'status': 'ok' if ok else 'error', 'connected': ok})


@app.route('/servo/move', methods=['POST'])
def servo_move():
    data = request.json
    positions = data.get('positions', {})
    duration = data.get('duration', 1000)

    if not positions:
        return jsonify({'error': '缺少 positions 参数'}), 400

    try:
        servo_positions = {int(k): int(v) for k, v in positions.items()}
        cmd = _build_servo_move_cmd(servo_positions, int(duration))
        bridge.send(cmd)
        logger.info(f'move_to: {servo_positions}, duration={duration}')
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f'move 失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/servo/move_single', methods=['POST'])
def servo_move_single():
    data = request.json
    servo_id = data.get('servo_id')
    position = data.get('position')
    duration = data.get('duration', 500)

    if servo_id is None or position is None:
        return jsonify({'error': '缺少参数'}), 400

    try:
        cmd = _build_servo_move_cmd({int(servo_id): int(position)}, int(duration))
        bridge.send(cmd)
        logger.info(f'move_single: S{servo_id} -> {position}, duration={duration}')
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f'move_single 失败: {e}')
        return jsonify({'error': str(e)}), 500


# ─── 主入口 ────────────────────────────────────────────────────────────────

def main():
    global bridge

    parser = argparse.ArgumentParser(description='Hiwonder ArmPi 中继服务')
    parser.add_argument('--port', type=int, default=8080, help='HTTP 服务端口 (默认 8080)')
    parser.add_argument('--serial', type=str, default='/dev/ttyAMA0',
                        help='STM32 串口设备 (默认 /dev/ttyAMA0)')
    parser.add_argument('--baud', type=int, default=9600, help='串口波特率 (默认 9600)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认 0.0.0.0)')
    args = parser.parse_args()

    try:
        bridge = SerialBridge(args.serial, args.baud)
    except Exception:
        logger.warning('串口未连接，服务将以离线模式运行（仅响应 ping）')

    logger.info(f'Hiwonder 中继服务启动: http://{args.host}:{args.port}')
    logger.info(f'串口: {args.serial} @ {args.baud}bps')
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
