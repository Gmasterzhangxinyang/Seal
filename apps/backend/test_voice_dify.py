"""语音模块测试 — 现场录音 → Dify 工作流 → 输出结果"""

import requests
import wave
import tempfile
import os
import pyaudio

DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
BASE_URL = os.environ.get("DIFY_BASE_URL", "https://api.dify.ai/v1")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5


def record_audio() -> bytes:
    """录制音频，返回 WAV 字节，按 Ctrl+C 停止"""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print(f"录音中... (按 Ctrl+C 停止)")
    frames = []
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
    except KeyboardInterrupt:
        pass

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        raise Exception("没有录到任何音频")

    buffer_path = tempfile.mktemp(suffix='.wav')
    with wave.open(buffer_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    # 转换成 MP3
    mp3_path = tempfile.mktemp(suffix='.mp3')
    import subprocess
    subprocess.run([
        'ffmpeg', '-y', '-f', 'wav', '-i', buffer_path,
        '-f', 'mp3', mp3_path
    ], capture_output=True, timeout=30)

    with open(mp3_path, 'rb') as f:
        audio_bytes = f.read()
    os.unlink(buffer_path)
    os.unlink(mp3_path)
    return audio_bytes


def call_dify_workflow(audio_bytes: bytes) -> dict:
    """上传音频 → 调用 Dify 工作流 → 返回 tool_id + comment"""
    # Step 1: 上传
    url_upload = f"{BASE_URL}/files/upload"
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}
    resp = requests.post(
        url_upload,
        headers=headers,
        files={"file": ("voice.mp3", audio_bytes, "audio/mpeg")},
        data={"user": "mec202_voice", "type": "audio"},
        timeout=60
    )
    if resp.status_code not in (200, 201):
        raise Exception(f"上传失败: {resp.status_code} - {resp.text}")
    file_id = resp.json().get("id")
    print(f"上传成功, file_id: {file_id}")

    # Step 2: 调用工作流
    url_run = f"{BASE_URL}/workflows/run"
    payload = {
        "inputs": {
            "voice": {
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "audio"
            }
        },
        "response_mode": "blocking",
        "user": "mec202_voice",
    }
    resp2 = requests.post(
        url_run,
        json=payload,
        headers={"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"},
        timeout=120
    )
    if resp2.status_code != 200:
        raise Exception(f"工作流失败: {resp2.status_code} - {resp2.text}")

    result = resp2.json()
    status = result.get("data", {}).get("status")
    if status == "failed":
        raise Exception(f"工作流执行失败: {result.get('data', {}).get('error')}")

    return {
        "status": status,
        "tool_id": result.get("data", {}).get("outputs", {}).get("tool_id"),
        "comment": result.get("data", {}).get("outputs", {}).get("comment"),
    }


if __name__ == "__main__":
    print("=" * 50)
    print("开始现场录音测试")
    print("=" * 50)

    audio = record_audio()
    print(f"录音完成，音频大小: {len(audio)} bytes")

    result = call_dify_workflow(audio)
    print()
    print("=" * 50)
    print(f"状态: {result['status']}")
    print(f"tool_id: {result['tool_id']}")
    print(f"comment: {result['comment']}")
    print("=" * 50)