"""TTS 音频生成（支持火山引擎 V3 / edge-tts），含逐字字幕"""
import os
import struct
import json
import uuid
import asyncio
import websockets
import edge_tts
from mutagen.mp3 import MP3
from config import (
    TTS_ENGINE,
    VOLCANO_APP_ID, VOLCANO_TOKEN,
    VOLCANO_ENCODING, VOLCANO_SPEED_RATIO,
    EDGE_VOICE, EDGE_RATE,
)
from utils import ensure_dir, save_json


# ===== 火山引擎 TTS V3 WebSocket =====

VOLCANO_WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
VOLCANO_RESOURCE_ID = "seed-tts-2.0"

# Event codes
E_START_CONN = 1
E_FINISH_CONN = 2
E_CONN_STARTED = 50
E_START_SESSION = 100
E_FINISH_SESSION = 102
E_SESSION_STARTED = 150
E_SESSION_FINISHED = 152
E_TASK_REQUEST = 200
E_TTS_RESPONSE = 352
E_TTS_SUBTITLE = 364


def _build_frame(event, session_id=None, payload=None):
    """构建 V3 二进制请求帧"""
    if payload is None:
        payload = {}
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    frame = bytearray([0x11, 0x14, 0x10, 0x00])
    frame += struct.pack(">i", event)
    if session_id is not None:
        sid = session_id.encode("utf-8")
        frame += struct.pack(">I", len(sid)) + sid
    frame += struct.pack(">I", len(payload_bytes)) + payload_bytes
    return bytes(frame)


def _parse_frame(data):
    """解析 V3 二进制响应帧 -> (event, audio_bytes, json_payload)"""
    if len(data) < 4:
        return None, None, None

    msg_type = (data[1] >> 4) & 0x0F
    has_event = (data[1] & 0x04) != 0
    serialization = (data[2] >> 4) & 0x0F
    compression = data[2] & 0x0F
    offset = 4

    if msg_type == 0xF:
        error_code = 0
        if offset + 4 <= len(data):
            error_code = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
        if offset + 4 <= len(data):
            plen = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            raw = data[offset:offset + plen]
            if compression == 1:
                import gzip
                raw = gzip.decompress(raw)
            try:
                return -1, None, json.loads(raw)
            except Exception:
                return -1, None, {"error_code": error_code}
        return -1, None, {"error_code": error_code}

    event = None
    if has_event and offset + 4 <= len(data):
        event = struct.unpack(">i", data[offset:offset + 4])[0]
        offset += 4

    if has_event and event is not None:
        if offset + 4 <= len(data):
            id_len = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4 + id_len

    if offset + 4 <= len(data):
        plen = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        raw = data[offset:offset + plen]
        if compression == 1:
            import gzip
            raw = gzip.decompress(raw)
        if msg_type == 0xB:
            return event, raw, None
        elif serialization == 1:
            try:
                return event, None, json.loads(raw)
            except Exception:
                return event, None, None
        else:
            return event, raw, None

    return event, None, None


async def _volcano_generate_async(text: str, output_path: str, voice: str = None) -> list[dict]:
    """V3 WebSocket TTS，返回字幕 words 列表"""
    token = os.environ.get("VOLCANO_TTS_TOKEN", VOLCANO_TOKEN)
    if not token:
        raise ValueError("请设置环境变量 VOLCANO_TTS_TOKEN")

    headers = {
        "X-Api-App-Key": VOLCANO_APP_ID,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": VOLCANO_RESOURCE_ID,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    session_id = str(uuid.uuid4())
    audio_chunks = []
    subtitle_words = []

    async with websockets.connect(VOLCANO_WS_URL, additional_headers=headers) as ws:
        # StartConnection
        await ws.send(_build_frame(E_START_CONN))
        resp = await ws.recv()
        event, _, payload = _parse_frame(resp)
        if event != E_CONN_STARTED:
            raise RuntimeError(f"连接失败: event={event}, payload={payload}")

        # StartSession (开启字幕)
        session_payload = {
            "event": E_START_SESSION,
            "req_params": {
                "speaker": voice,
                "audio_params": {
                    "format": VOLCANO_ENCODING,
                    "sample_rate": 24000,
                    "speech_rate": int((VOLCANO_SPEED_RATIO - 1) * 100),
                    "enable_subtitle": True,
                },
            },
        }
        await ws.send(_build_frame(E_START_SESSION, session_id, session_payload))
        resp = await ws.recv()
        event, _, payload = _parse_frame(resp)
        if event != E_SESSION_STARTED:
            raise RuntimeError(f"会话启动失败: event={event}, payload={payload}")

        # TaskRequest
        task_payload = {
            "event": E_TASK_REQUEST,
            "req_params": {"text": text},
        }
        await ws.send(_build_frame(E_TASK_REQUEST, session_id, task_payload))
        await ws.send(_build_frame(E_FINISH_SESSION, session_id))

        # 接收音频 + 字幕
        while True:
            resp = await ws.recv()
            event, audio, payload = _parse_frame(resp)
            if event == E_TTS_RESPONSE and audio:
                audio_chunks.append(audio)
            elif event == E_TTS_SUBTITLE and payload:
                words = payload.get("words", [])
                subtitle_words.extend(words)
            elif event == E_SESSION_FINISHED:
                break
            elif event == -1:
                raise RuntimeError(f"TTS 错误: {payload}")
            elif event == 153:
                raise RuntimeError(f"TTS 会话失败: {payload}")

        await ws.send(_build_frame(E_FINISH_CONN))

    with open(output_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    return subtitle_words


def _volcano_generate(text: str, output_path: str, voice: str = None) -> list[dict]:
    """同步包装，返回字幕 words"""
    return asyncio.run(_volcano_generate_async(text, output_path, voice))


# ===== Edge TTS =====

async def _edge_generate(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
    await communicate.save(output_path)


# ===== 通用接口 =====

def _generate_one(text: str, output_path: str, voice: str = None) -> list[dict]:
    """生成音频，返回字幕 words（仅火山引擎支持）"""
    if TTS_ENGINE == "volcano":
        return _volcano_generate(text, output_path, voice)
    else:
        asyncio.run(_edge_generate(text, output_path))
        return []


def get_duration(mp3_path: str) -> float:
    audio = MP3(mp3_path)
    return audio.info.length


def generate_tts(script: dict, output_dir: str, voice: str = None, voice_label: str = None) -> list[dict]:
    """为每页幻灯片生成 TTS 音频，返回时长信息"""
    suffix = f"_{voice_label}" if voice_label else ""
    audio_dir = os.path.join(output_dir, f"audio{suffix}")
    ensure_dir(audio_dir)

    engine_label = "火山引擎 V3" if TTS_ENGINE == "volcano" else "Edge TTS"
    voice_info = f" ({voice_label})" if voice_label else ""
    print(f"[TTS] 引擎: {engine_label}{voice_info}")

    slides = script["slides"]
    audio_info = []

    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            audio_info.append({"index": i, "path": None, "duration": 3.0, "words": []})
            continue

        filename = f"slide_{i:02d}.mp3"
        filepath = os.path.join(audio_dir, filename)

        print(f"[TTS] {i + 1}/{len(slides)}: {narration[:30]}...")

        words = _generate_one(narration, filepath, voice)

        duration = get_duration(filepath)
        audio_info.append({
            "index": i,
            "path": filepath,
            "duration": round(duration, 2),
            "words": words,
        })
        print(f"[TTS] -> {filename} ({duration:.1f}s)")

    info_path = os.path.join(output_dir, f"audio_info{suffix}.json")
    save_json(audio_info, info_path)

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
