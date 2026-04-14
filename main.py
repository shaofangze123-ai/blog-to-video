"""Blog to Video -- 博客一键生成视频
用法: python main.py <博客.md> [输出目录]
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
from config import SIZES, VIDEOS_DIR, TEMP_DIR
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
        print("示例:")
        print("  python main.py post.md")
        print()
        print("输出结构:")
        print("  output/videos/       最终视频")
        print("  output/temp/         中间文件")
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
    prefix = f"video_{today}_{slug}"

    # 中间文件目录（按任务隔离）
    temp_dir = os.path.join(TEMP_DIR, prefix)
    ensure_dir(temp_dir)
    ensure_dir(VIDEOS_DIR)

    start = time.time()
    print()
    print("=" * 50)
    print(f"  输入: {md_path}")
    print(f"  标题: {title}")
    print(f"  视频: output/videos/{prefix}_*.mp4")
    print("=" * 50)

    # Step 1: 内容分析
    print("\n> Step 1/4 -- 分析博客内容, 生成分镜脚本")
    script = analyze_blog(md_path, temp_dir)

    # Step 2: 生成 HTML 幻灯片
    print("\n> Step 2/4 -- 生成 HTML 幻灯片")
    html_paths = generate_slides(script, temp_dir)

    # Step 3: TTS 音频生成
    print("\n> Step 3/4 -- 生成 TTS 配音")
    audio_info = generate_tts(script, temp_dir)

    # Step 4: 视频渲染合成
    print("\n> Step 4/4 -- 渲染视频")
    video_paths = render_video(html_paths, audio_info, temp_dir)

    # 将最终视频复制到 videos/ 目录，统一命名
    final_paths = {}
    for size_key, tmp_path in video_paths.items():
        suffix = "douyin" if size_key == "vertical" else "youtube"
        final_name = f"{prefix}_{suffix}.mp4"
        final_path = os.path.join(VIDEOS_DIR, final_name)
        shutil.copy2(tmp_path, final_path)
        final_paths[size_key] = final_path

    elapsed = time.time() - start
    print()
    print("=" * 50)
    print(f"  完成! 耗时 {elapsed:.0f} 秒")
    print("=" * 50)
    for key, path in final_paths.items():
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  {SIZES[key]['label']}: {path} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    main()
