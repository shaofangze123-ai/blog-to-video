"""TTS 音频生成（支持火山引擎 / edge-tts）"""
import os
import asyncio
import json
import uuid
import base64
import requests
import edge_tts
from mutagen.mp3 import MP3
from config import (
    TTS_ENGINE,
    VOLCANO_APP_ID, VOLCANO_TOKEN, VOLCANO_CLUSTER,
    VOLCANO_VOICE, VOLCANO_ENCODING, VOLCANO_SPEED_RATIO,
    EDGE_VOICE, EDGE_RATE,
)
from utils import ensure_dir, save_json


# ===== 火山引擎 TTS =====

VOLCANO_API_URL = "https://openspeech.bytedance.com/api/v1/tts"


def _volcano_generate(text: str, output_path: str):
    """调用火山引擎 TTS HTTP 接口"""
    token = os.environ.get("VOLCANO_TTS_TOKEN", VOLCANO_TOKEN)
    if not token:
        raise ValueError("请设置环境变量 VOLCANO_TTS_TOKEN")

    payload = {
        "app": {
            "appid": VOLCANO_APP_ID,
            "token": token,
            "cluster": VOLCANO_CLUSTER,
        },
        "user": {
            "uid": "blog-to-video",
        },
        "audio": {
            "voice_type": VOLCANO_VOICE,
            "encoding": VOLCANO_ENCODING,
            "speed_ratio": VOLCANO_SPEED_RATIO,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{token}",
    }

    resp = requests.post(VOLCANO_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 3000:
        msg = result.get("message", "unknown error")
        raise RuntimeError(f"火山引擎 TTS 错误 (code={result.get('code')}): {msg}")

    audio_b64 = result.get("data", "")
    if not audio_b64:
        raise RuntimeError("火山引擎 TTS 返回空音频数据")

    audio_bytes = base64.b64decode(audio_b64)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)


# ===== Edge TTS =====

async def _edge_generate(text: str, output_path: str):
    """调用 edge-tts"""
    communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
    await communicate.save(output_path)


# ===== 通用接口 =====

def _generate_one(text: str, output_path: str):
    """根据配置选择 TTS 引擎"""
    if TTS_ENGINE == "volcano":
        _volcano_generate(text, output_path)
    else:
        asyncio.run(_edge_generate(text, output_path))


def get_duration(mp3_path: str) -> float:
    """获取 MP3 时长（秒）"""
    audio = MP3(mp3_path)
    return audio.info.length


def generate_tts(script: dict, output_dir: str) -> list[dict]:
    """为每页幻灯片生成 TTS 音频，返回时长信息"""
    audio_dir = os.path.join(output_dir, "audio")
    ensure_dir(audio_dir)

    engine_label = "火山引擎" if TTS_ENGINE == "volcano" else "Edge TTS"
    print(f"[TTS] 引擎: {engine_label}")

    slides = script["slides"]
    audio_info = []

    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            audio_info.append({"index": i, "path": None, "duration": 3.0})
            continue

        filename = f"slide_{i:02d}.mp3"
        filepath = os.path.join(audio_dir, filename)

        print(f"[TTS] {i + 1}/{len(slides)}: {narration[:30]}...")

        _generate_one(narration, filepath)

        duration = get_duration(filepath)
        audio_info.append({
            "index": i,
            "path": filepath,
            "duration": round(duration, 2),
        })
        print(f"[TTS] -> {filename} ({duration:.1f}s)")

    info_path = os.path.join(output_dir, "audio_info.json")
    save_json(audio_info, info_path)
    print(f"[TTS] 音频信息已保存: {info_path}")

    return audio_info


if __name__ == "__main__":
    import sys
    from utils import load_json
    if len(sys.argv) < 2:
        print("用法: python tts.py <script.json> [输出目录]")
        sys.exit(1)
    script = load_json(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    generate_tts(script, output_dir)
