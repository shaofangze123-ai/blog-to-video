"""Blog to Video -- 博客一键生成视频
用法: python main.py <博客.md>

每篇博客生成 4 个视频：男一/女一 x 竖版/横版
"""
import sys
import os
import time
import shutil
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from analyze import analyze_blog
from slides import generate_slides
from tts import generate_tts
from render import render_video
from config import SIZES, VOLCANO_VOICES, VIDEOS_DIR, TEMP_DIR
from utils import ensure_dir, slugify, read_markdown


def _extract_title(md_path: str) -> str:
    """从 Markdown 提取标题（第一个 # 标题或文件名）"""
    content = read_markdown(md_path)
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return os.path.splitext(os.path.basename(md_path))[0]


def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("  Blog to Video -- 博客一键生成视频")
        print("=" * 50)
        print()
        print("用法: python main.py <博客.md>")
        print()
        print("每篇博客生成 4 个视频:")
        print("  男一/女一 x 竖版/横版")
        print()
        print("输出结构:")
        print("  output/videos/<项目名>_<日期>/")
        print("    vertical/   竖版视频")
        print("    horizontal/ 横版视频")
        print()
        print("环境变量:")
        print("  BLOG_VIDEO_API_KEY   LLM API 密钥")
        sys.exit(1)

    md_path = sys.argv[1]

    if not os.path.exists(md_path):
        print(f"错误: 文件不存在 {md_path}")
        sys.exit(1)

    # 生成日期和标题 slug
    today = date.today().strftime("%Y%m%d")
    title = _extract_title(md_path)
    slug = slugify(title)
    project_dir_name = f"{slug}_{today}"

    # 中间文件目录
    temp_dir = os.path.join(TEMP_DIR, project_dir_name)
    ensure_dir(temp_dir)

    # 最终视频目录
    video_base = os.path.join(VIDEOS_DIR, project_dir_name)
    vertical_dir = os.path.join(video_base, "vertical")
    horizontal_dir = os.path.join(video_base, "horizontal")
    ensure_dir(vertical_dir)
    ensure_dir(horizontal_dir)

    start = time.time()
    print()
    print("=" * 50)
    print(f"  输入: {md_path}")
    print(f"  标题: {title}")
    voices_str = ", ".join(v["label"] for v in VOLCANO_VOICES)
    print(f"  音色: {voices_str}")
    print(f"  输出: output/videos/{project_dir_name}/")
    print("=" * 50)

    # Step 1: 内容分析（只需一次）
    print("\n> Step 1/4 -- 分析博客内容, 生成分镜脚本")
    script = analyze_blog(md_path, temp_dir)

    # Step 2: 生成 HTML 幻灯片（只需一次）
    print("\n> Step 2/4 -- 生成 HTML 幻灯片")
    html_paths = generate_slides(script, temp_dir)

    # Step 3 & 4: 为每个音色生成 TTS + 渲染视频
    all_final = []

    for vi, voice_cfg in enumerate(VOLCANO_VOICES):
        voice_id = voice_cfg["id"]
        voice_label = voice_cfg["label"]

        print(f"\n{'='*50}")
        print(f"  音色 {vi+1}/{len(VOLCANO_VOICES)}: {voice_label}")
        print(f"{'='*50}")

        # Step 3: TTS
        print(f"\n> Step 3/4 -- 生成 TTS 配音 ({voice_label})")
        audio_info = generate_tts(script, temp_dir, voice=voice_id, voice_label=voice_label)

        # Step 4: 渲染视频
        print(f"\n> Step 4/4 -- 渲染视频 ({voice_label})")
        video_paths = render_video(html_paths, audio_info, temp_dir)

        # 复制到最终目录
        for size_key, tmp_path in video_paths.items():
            orient = "vertical" if size_key == "vertical" else "horizontal"
            final_name = f"{slug}_{orient}_{voice_label}.mp4"
            final_dir = vertical_dir if size_key == "vertical" else horizontal_dir
            final_path = os.path.join(final_dir, final_name)
            shutil.copy2(tmp_path, final_path)
            all_final.append((voice_label, SIZES[size_key]["label"], final_path))

    elapsed = time.time() - start
    print()
    print("=" * 50)
    print(f"  完成! 耗时 {elapsed:.0f} 秒, 共 {len(all_final)} 个视频")
    print("=" * 50)
    for voice_label, size_label, path in all_final:
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  [{voice_label}] {size_label}: {path} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    main()
