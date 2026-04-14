"""视频渲染：Playwright 截帧 + ffmpeg 合成"""
import os
import subprocess
import shutil
import asyncio

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"
from playwright.async_api import async_playwright
from config import SIZES, MIN_PAGE_DURATION, PAGE_PADDING
from utils import ensure_dir


async def _capture_frames(html_path: str, audio_info: list, size_key: str, output_dir: str) -> str:
    """用 Playwright 逐页截图，按音频时长生成帧序列"""
    s = SIZES[size_key]
    frames_dir = os.path.join(output_dir, f"frames_{size_key}")
    ensure_dir(frames_dir)

    # 清理旧帧
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))

    abs_html = os.path.abspath(html_path).replace("\\", "/")
    url = f"file:///{abs_html}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": s["width"], "height": s["height"]})
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1000)  # 等待字体加载

        total_slides = await page.evaluate("window.totalSlides")
        fps = 30
        frame_idx = 0

        for slide_idx in range(total_slides):
            await page.evaluate(f"window.goToSlide({slide_idx})")
            await page.wait_for_timeout(300)  # 等待过渡

            # 获取该页时长
            info = audio_info[slide_idx] if slide_idx < len(audio_info) else {}
            duration = max(info.get("duration", MIN_PAGE_DURATION) + PAGE_PADDING, MIN_PAGE_DURATION)

            # 按帧率截图
            num_frames = int(duration * fps)
            print(f"[渲染] 第 {slide_idx + 1}/{total_slides} 页: {duration:.1f}s → {num_frames} 帧")

            # 截一张图，复制为多帧（静态页面无需每帧都截）
            screenshot_path = os.path.join(frames_dir, f"frame_{frame_idx:06d}.png")
            await page.screenshot(path=screenshot_path)

            # 后续帧复制同一张图
            for f_offset in range(1, num_frames):
                src = screenshot_path
                dst = os.path.join(frames_dir, f"frame_{frame_idx + f_offset:06d}.png")
                shutil.copy2(src, dst)

            frame_idx += num_frames

        await browser.close()

    print(f"[渲染] 共 {frame_idx} 帧")
    return frames_dir


def _merge_audio(audio_info: list, output_dir: str, size_key: str) -> str:
    """将所有音频片段合并为一个完整音频，中间插入静音"""
    concat_path = os.path.join(output_dir, f"audio_concat_{size_key}.txt")
    merged_path = os.path.join(output_dir, f"audio_merged_{size_key}.mp3")
    silence_path = os.path.join(output_dir, "silence_1s.mp3")

    # 生成 1 秒静音
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi", "-i",
        "anullsrc=r=24000:cl=mono", "-t", str(PAGE_PADDING),
        "-q:a", "9", silence_path,
    ], capture_output=True)

    # 写 concat 列表
    with open(concat_path, "w", encoding="utf-8") as f:
        for info in audio_info:
            if info.get("path") and os.path.exists(info["path"]):
                f.write(f"file '{os.path.abspath(info['path'])}'\n")
            # 每页后加静音间隔
            f.write(f"file '{os.path.abspath(silence_path)}'\n")

    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_path, "-c", "copy", merged_path,
    ], capture_output=True)

    return merged_path


def _compose_video(frames_dir: str, audio_path: str, output_path: str):
    """ffmpeg 合成最终视频"""
    print(f"[合成] 正在合成视频...")
    cmd = [
        FFMPEG, "-y",
        "-framerate", "30",
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[合成] ffmpeg 错误: {result.stderr[-500:]}")
        raise RuntimeError("视频合成失败")

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"[合成] 完成: {output_path} ({size_mb:.1f} MB)")


def render_video(html_paths: dict, audio_info: list, output_dir: str) -> dict:
    """渲染双尺寸视频"""
    ensure_dir(output_dir)
    video_paths = {}

    for size_key, html_path in html_paths.items():
        label = SIZES[size_key]["label"]
        print(f"\n{'='*40}")
        print(f"[渲染] 开始渲染 {label}")
        print(f"{'='*40}")

        # 1. 截帧
        frames_dir = asyncio.run(_capture_frames(html_path, audio_info, size_key, output_dir))

        # 2. 合并音频
        audio_path = _merge_audio(audio_info, output_dir, size_key)

        # 3. 合成视频
        video_filename = f"video_{size_key}.mp4"
        video_path = os.path.join(output_dir, video_filename)
        _compose_video(frames_dir, audio_path, video_path)

        video_paths[size_key] = video_path

        # 清理帧文件
        shutil.rmtree(frames_dir, ignore_errors=True)

    return video_paths


if __name__ == "__main__":
    import sys
    from utils import load_json
    if len(sys.argv) < 3:
        print("用法: python render.py <slides_vertical.html> <audio_info.json> [输出目录]")
        sys.exit(1)
    html_path = sys.argv[1]
    audio_info = load_json(sys.argv[2])
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    # 单尺寸测试
    asyncio.run(_capture_frames(html_path, audio_info, "vertical", output_dir))
