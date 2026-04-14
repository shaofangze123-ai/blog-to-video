"""博客内容分析 → 分镜脚本生成"""
import os
import json
from openai import OpenAI
from config import API_BASE_URL, API_KEY, CHAT_MODEL
from utils import read_markdown, save_json, ensure_dir

SYSTEM_PROMPT = """你是一个专业的科技视频编导。根据博客文章内容，生成一个视频分镜脚本。

要求：
1. 将文章拆分为 5-8 页幻灯片（含封面和结尾）
2. 每页包含：标题、2-4 个要点（简短有力）、旁白文案（口语化，30-60 字）
3. 封面页：项目名称 + 一句话介绍 + 开场旁白
4. 结尾页：总结 + 引导关注
5. 旁白要自然、口语化，像在跟朋友介绍一个好用的工具
6. 要点用精炼的短句，不要长段落

严格按以下 JSON 格式输出，不要输出其他内容：
{
  "title": "视频标题",
  "slides": [
    {
      "type": "cover",
      "title": "项目名称",
      "subtitle": "一句话介绍",
      "narration": "开场旁白文案"
    },
    {
      "type": "content",
      "title": "这页的标题",
      "points": ["要点1", "要点2", "要点3"],
      "narration": "这页的旁白文案"
    },
    {
      "type": "ending",
      "title": "总结标题",
      "points": ["总结要点1", "总结要点2"],
      "narration": "结尾旁白，引导关注"
    }
  ]
}"""


def analyze_blog(md_path: str, output_dir: str) -> dict:
    """分析博客内容，生成分镜脚本"""
    content = read_markdown(md_path)

    api_key = os.environ.get("BLOG_VIDEO_API_KEY", API_KEY)
    if not api_key:
        raise ValueError("请设置环境变量 BLOG_VIDEO_API_KEY 或在 config.py 中配置 API_KEY")

    client = OpenAI(base_url=API_BASE_URL, api_key=api_key)

    print(f"[分析] 正在分析博客内容（{len(content)} 字）...")

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请根据以下博客文章生成视频分镜脚本：\n\n{content}"},
        ],
        temperature=0.7,
    )

    raw = response.choices[0].message.content.strip()
    # 提取 JSON（可能被 ```json 包裹）
    if "```" in raw:
        raw = raw.split("```json")[-1].split("```")[0] if "```json" in raw else raw.split("```")[1].split("```")[0]

    script = json.loads(raw)

    ensure_dir(output_dir)
    script_path = os.path.join(output_dir, "script.json")
    save_json(script, script_path)
    print(f"[分析] 分镜脚本已保存: {script_path}")
    print(f"[分析] 共 {len(script['slides'])} 页幻灯片")

    return script


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python analyze.py <博客.md> [输出目录]")
        sys.exit(1)
    md_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    analyze_blog(md_path, output_dir)
