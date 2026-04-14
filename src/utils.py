"""工具函数"""
import os
import json
import re


def read_markdown(path: str) -> str:
    """读取 Markdown 文件，去掉 frontmatter"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 去掉 YAML frontmatter
    content = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)
    return content.strip()


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_json(data, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    """生成文件名安全的 slug"""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:50]
