"""ASS 字幕生成 — 根据 TTS 逐字时间戳生成视频字幕"""
import os
from config import SIZES, PAGE_PADDING


# 每行字幕最大字符数
MAX_CHARS_PER_LINE = 15


def _format_ass_time(seconds: float) -> str:
    """秒 -> ASS 时间格式 H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _group_words(words: list[dict], max_chars: int = MAX_CHARS_PER_LINE) -> list[dict]:
    """将逐字时间戳按字数分组为字幕段"""
    if not words:
        return []

    groups = []
    buf_text = ""
    buf_start = None
    buf_end = None

    for w in words:
        word = w.get("word", "")
        start = w.get("startTime", 0)
        end = w.get("endTime", 0)

        if buf_start is None:
            buf_start = start

        buf_text += word
        buf_end = end

        # 遇到句号/逗号/问号等标点或达到字数上限时切分
        is_punct = word and word[-1] in "，。！？；：、,.!?;:"
        if len(buf_text) >= max_chars or is_punct:
            groups.append({
                "text": buf_text,
                "start": buf_start,
                "end": buf_end,
            })
            buf_text = ""
            buf_start = None
            buf_end = None

    if buf_text:
        groups.append({
            "text": buf_text,
            "start": buf_start,
            "end": buf_end,
        })

    return groups


def _ass_header(width: int, height: int) -> str:
    """生成 ASS 文件头，根据尺寸适配字号"""
    # 竖屏字号大一些（屏幕窄），横屏适中
    if width < height:
        font_size = 38
        margin_v = 120
    else:
        font_size = 30
        margin_v = 40

    return f"""[Script Info]
Title: Blog to Video Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2.5,1,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def generate_subtitles(audio_info: list[dict], output_dir: str, size_key: str) -> str:
    """根据音频信息中的 words 生成 ASS 字幕文件"""
    s = SIZES[size_key]
    ass_path = os.path.join(output_dir, f"subtitles_{size_key}.ass")

    lines = [_ass_header(s["width"], s["height"])]

    # 计算每页的全局起始时间
    global_offset = 0.0

    for info in audio_info:
        words = info.get("words", [])
        duration = info.get("duration", 3.0)

        if words:
            groups = _group_words(words)
            for g in groups:
                abs_start = global_offset + g["start"]
                abs_end = global_offset + g["end"]
                t1 = _format_ass_time(abs_start)
                t2 = _format_ass_time(abs_end)
                text = g["text"].replace("\n", "\\N")
                lines.append(f"Dialogue: 0,{t1},{t2},Default,,0,0,0,,{text}")
        elif info.get("path"):
            # 没有 words 数据时，用旁白文本按时长均分
            narration = info.get("narration", "")
            if narration:
                t1 = _format_ass_time(global_offset)
                t2 = _format_ass_time(global_offset + duration)
                lines.append(f"Dialogue: 0,{t1},{t2},Default,,0,0,0,,{narration}")

        global_offset += duration + PAGE_PADDING

    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    count = sum(1 for l in lines if l.startswith("Dialogue:"))
    print(f"[字幕] {SIZES[size_key]['label']}: {ass_path} ({count} 条)")
    return ass_path
