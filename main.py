"""Blog to Video — 主入口
用法: python main.py <博客.md> [输出目录]
"""
import sys
import os
import time
from analyze import analyze_blog
from slides import generate_slides
from tts import generate_tts
from render import render_video
from config import SIZES


def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("  Blog to Video — 博客一键生成视频")
        print("=" * 50)
        print()
        print("用法: python main.py <博客.md> [输出目录]")
        print()
        print("示例:")
        print("  python main.py post.md")
        print("  python main.py post.md output/my-video")
        print()
        print("环境变量:")
        print("  BLOG_VIDEO_API_KEY  LLM API 密钥")
        sys.exit(1)

    md_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join("output", os.path.splitext(os.path.basename(md_path))[0])

    if not os.path.exists(md_path):
        print(f"错误: 文件不存在 {md_path}")
        sys.exit(1)

    start = time.time()
    print()
    print("=" * 50)
    print(f"  输入: {md_path}")
    print(f"  输出: {output_dir}")
    print("=" * 50)

    # Step 1: 内容分析
    print("\n> Step 1/4 -- 分析博客内容, 生成分镜脚本")
    script = analyze_blog(md_path, output_dir)

    # Step 2: 生成 HTML 幻灯片
    print("\n> Step 2/4 -- 生成 HTML 幻灯片")
    html_paths = generate_slides(script, output_dir)

    # Step 3: TTS 音频生成
    print("\n> Step 3/4 -- 生成 TTS 配音")
    audio_info = generate_tts(script, output_dir)

    # Step 4: 视频渲染合成
    print("\n> Step 4/4 -- 渲染视频")
    video_paths = render_video(html_paths, audio_info, output_dir)

    elapsed = time.time() - start
    print()
    print("=" * 50)
    print(f"  完成！耗时 {elapsed:.0f} 秒")
    print("=" * 50)
    for key, path in video_paths.items():
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  {SIZES[key]['label']}: {path} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    main()
