"""根据分镜脚本生成 HTML 幻灯片（双尺寸）"""
import os
from config import SIZES
from utils import ensure_dir


def _css_vars(size_key: str) -> str:
    """根据尺寸生成 CSS 变量"""
    s = SIZES[size_key]
    is_v = size_key == "vertical"
    return f"""
    :root {{
      --w: {s['width']}px;
      --h: {s['height']}px;
      --title-size: {'clamp(1.8rem, 6vw, 3rem)' if is_v else 'clamp(1.8rem, 4vw, 3.5rem)'};
      --subtitle-size: {'clamp(1rem, 3.5vw, 1.6rem)' if is_v else 'clamp(1rem, 2vw, 1.5rem)'};
      --body-size: {'clamp(0.9rem, 3vw, 1.3rem)' if is_v else 'clamp(0.85rem, 1.5vw, 1.15rem)'};
      --point-size: {'clamp(1rem, 3.2vw, 1.4rem)' if is_v else 'clamp(0.9rem, 1.6vw, 1.2rem)'};
      --pad-x: {'clamp(2rem, 8vw, 4rem)' if is_v else 'clamp(3rem, 6vw, 8rem)'};
      --pad-y: {'clamp(2rem, 6vh, 4rem)' if is_v else 'clamp(2rem, 4vh, 3rem)'};
    }}"""


def _base_css() -> str:
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 100%; height: 100%; overflow: hidden; }
    body {
      font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
      background: #0a0e1a;
      color: #e8eaed;
    }
    .slide {
      width: 100vw; height: 100vh;
      display: none;
      flex-direction: column;
      justify-content: center;
      padding: var(--pad-y) var(--pad-x);
      position: relative;
      overflow: hidden;
    }
    .slide.active { display: flex; }

    /* 背景装饰 */
    .slide::before {
      content: '';
      position: absolute; inset: 0;
      background:
        radial-gradient(ellipse 80% 60% at 20% 20%, rgba(77,124,255,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at 80% 80%, rgba(168,85,247,0.06) 0%, transparent 60%);
      pointer-events: none;
    }

    /* 封面 */
    .cover-slide { text-align: center; align-items: center; }
    .cover-slide .tag {
      display: inline-block;
      padding: 6px 20px;
      border-radius: 20px;
      border: 1px solid rgba(77,124,255,0.4);
      color: #4d7cff;
      font-size: var(--body-size);
      margin-bottom: 2rem;
      background: rgba(77,124,255,0.08);
    }
    .cover-slide h1 {
      font-size: var(--title-size);
      font-weight: 700;
      line-height: 1.3;
      margin-bottom: 1.2rem;
      background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.7) 50%, #22d3ee 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .cover-slide .subtitle {
      font-size: var(--subtitle-size);
      color: rgba(255,255,255,0.55);
      line-height: 1.6;
      max-width: 80%;
    }

    /* 内容页 */
    .content-slide h2 {
      font-size: var(--title-size);
      font-weight: 700;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid rgba(77,124,255,0.3);
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }
    .content-slide h2::before {
      content: '';
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #4d7cff;
      box-shadow: 0 0 12px #4d7cff;
      flex-shrink: 0;
    }
    .points { list-style: none; display: flex; flex-direction: column; gap: 1.2rem; }
    .points li {
      font-size: var(--point-size);
      line-height: 1.6;
      padding: 1rem 1.4rem;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 12px;
      border-left: 3px solid #4d7cff;
      color: rgba(255,255,255,0.85);
    }
    .points li:nth-child(2) { border-left-color: #a855f7; }
    .points li:nth-child(3) { border-left-color: #22d3ee; }
    .points li:nth-child(4) { border-left-color: #f472b6; }

    /* 结尾页 */
    .ending-slide { text-align: center; align-items: center; }
    .ending-slide h2 {
      font-size: var(--title-size);
      font-weight: 700;
      margin-bottom: 2rem;
      border: none;
      justify-content: center;
    }
    .ending-slide .points {
      align-items: center;
      margin-bottom: 2.5rem;
    }
    .ending-slide .points li {
      text-align: center;
      border-left: none;
      border: 1px solid rgba(77,124,255,0.2);
      background: rgba(77,124,255,0.06);
    }
    .ending-slide .cta {
      font-size: var(--subtitle-size);
      color: #4d7cff;
      font-weight: 600;
    }

    /* 页码 */
    .page-num {
      position: absolute;
      bottom: 1.5rem;
      right: 2rem;
      font-size: 0.8rem;
      color: rgba(255,255,255,0.2);
    }
    """


def _slide_html(slide: dict, index: int, total: int) -> str:
    """生成单页 HTML"""
    stype = slide.get("type", "content")

    if stype == "cover":
        return f"""
    <section class="slide cover-slide" data-index="{index}">
      <div class="tag">项目推荐</div>
      <h1>{slide['title']}</h1>
      <div class="subtitle">{slide.get('subtitle', '')}</div>
      <div class="page-num">{index + 1} / {total}</div>
    </section>"""

    elif stype == "ending":
        points_html = "\n".join(f'        <li>{p}</li>' for p in slide.get("points", []))
        return f"""
    <section class="slide ending-slide" data-index="{index}">
      <h2>{slide['title']}</h2>
      <ul class="points">
{points_html}
      </ul>
      <div class="cta">关注获取更多 AI 工具推荐</div>
      <div class="page-num">{index + 1} / {total}</div>
    </section>"""

    else:
        points_html = "\n".join(f'        <li>{p}</li>' for p in slide.get("points", []))
        return f"""
    <section class="slide content-slide" data-index="{index}">
      <h2>{slide['title']}</h2>
      <ul class="points">
{points_html}
      </ul>
      <div class="page-num">{index + 1} / {total}</div>
    </section>"""


def _full_html(script: dict, size_key: str) -> str:
    """生成完整 HTML"""
    slides = script["slides"]
    total = len(slides)
    slides_html = "\n".join(_slide_html(s, i, total) for i, s in enumerate(slides))
    css_vars = _css_vars(size_key)
    base_css = _base_css()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{script['title']}</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet" />
  <style>
    {css_vars}
    {base_css}
  </style>
</head>
<body>
{slides_html}

  <script>
    // 自动播放控制（供 Playwright 调用）
    const slides = document.querySelectorAll('.slide');
    let current = 0;
    slides[0].classList.add('active');

    window.totalSlides = slides.length;
    window.goToSlide = function(n) {{
      slides[current].classList.remove('active');
      current = n;
      slides[current].classList.add('active');
    }};
    window.getCurrentSlide = function() {{ return current; }};
  </script>
</body>
</html>"""


def generate_slides(script: dict, output_dir: str) -> dict:
    """生成双尺寸 HTML，返回文件路径"""
    ensure_dir(output_dir)
    paths = {}

    for size_key in SIZES:
        html = _full_html(script, size_key)
        filename = f"slides_{size_key}.html"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        paths[size_key] = filepath
        print(f"[幻灯片] {SIZES[size_key]['label']} → {filepath}")

    return paths


if __name__ == "__main__":
    import sys
    from utils import load_json
    if len(sys.argv) < 2:
        print("用法: python slides.py <script.json> [输出目录]")
        sys.exit(1)
    script = load_json(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    generate_slides(script, output_dir)
