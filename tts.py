"""TTS 音频生成（edge-tts）"""
import os
import asyncio
import json
import edge_tts
from mutagen.mp3 import MP3
from config import TTS_VOICE, TTS_RATE
from utils import ensure_dir, save_json


async def _generate_one(text: str, output_path: str, voice: str, rate: str):
    """生成单个音频文件"""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def get_duration(mp3_path: str) -> float:
    """获取 MP3 时长（秒）"""
    audio = MP3(mp3_path)
    return audio.info.length


def generate_tts(script: dict, output_dir: str) -> list[dict]:
    """为每页幻灯片生成 TTS 音频，返回时长信息"""
    audio_dir = os.path.join(output_dir, "audio")
    ensure_dir(audio_dir)

    slides = script["slides"]
    audio_info = []

    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            audio_info.append({"index": i, "path": None, "duration": 3.0})
            continue

        filename = f"slide_{i:02d}.mp3"
        filepath = os.path.join(audio_dir, filename)

        print(f"[TTS] 第 {i + 1}/{len(slides)} 页: {narration[:30]}...")

        asyncio.run(_generate_one(narration, filepath, TTS_VOICE, TTS_RATE))

        duration = get_duration(filepath)
        audio_info.append({
            "index": i,
            "path": filepath,
            "duration": round(duration, 2),
        })
        print(f"[TTS] → {filename} ({duration:.1f}s)")

    # 保存时长元数据
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
