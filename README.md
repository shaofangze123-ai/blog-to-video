# Blog to Video — 博客一键生成视频

输入一篇博客 Markdown 文件，全自动生成抖音（9:16）和 YouTube（16:9）两个带 TTS 配音的科技风格介绍视频。

## 管线流程

```
博客 Markdown
    ↓ LLM 分析（GPT-4.1-mini）
分镜脚本（JSON：标题/要点/旁白）
    ↓ 并行生成
    ├→ HTML 幻灯片（两套尺寸，科技深空风格）
    └→ TTS 中文配音（edge-tts，逐页生成）
    ↓ 合并
Playwright 逐页截帧 + ffmpeg 合成
    ↓
MP4 视频（9:16 + 16:9）
```

## 功能特性

- **全自动** — 一条命令，从博客到视频
- **双尺寸输出** — 抖音竖屏（1080x1920）+ YouTube 横屏（1920x1080）
- **AI 分镜** — LLM 自动分析文章结构，生成 5-8 页幻灯片脚本
- **中文 TTS** — 微软 Edge TTS，自然流畅的中文配音
- **科技风格** — 深空背景 + 毛玻璃卡片 + 渐变色彩
- **音频驱动** — 每页停留时间由 TTS 音频实际时长决定

## 快速开始

### 依赖安装

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

需要 ffmpeg，可通过 `pip install imageio-ffmpeg` 自动获取。

### 运行

```bash
# 设置 API 密钥
export BLOG_VIDEO_API_KEY="your-api-key"

# 生成视频
python main.py your-blog-post.md

```

### 输出结构

```
output/
├── videos/                                    # 最终视频（统一存放）
│   ├── video_20260414_ai-cosmos_douyin.mp4    # 抖音版
│   └── video_20260414_ai-cosmos_youtube.mp4   # YouTube 版
└── temp/                                      # 中间文件（按任务隔离）
    └── video_20260414_ai-cosmos/
        ├── script.json
        ├── slides_vertical.html
        ├── slides_horizontal.html
        ├── audio/
        │   ├── slide_00.mp3
        │   └── ...
        └── audio_info.json
```

视频命名规则：`video_日期_标题slug_平台.mp4`

## 项目结构

```
blog-to-video/
├── main.py              # 主入口，串联全流程
├── src/
│   ├── analyze.py       # 博客分析 + 分镜脚本生成（LLM）
│   ├── slides.py        # HTML 幻灯片生成（双尺寸）
│   ├── tts.py           # TTS 音频生成（edge-tts）
│   ├── render.py        # 视频渲染（Playwright + ffmpeg）
│   ├── config.py        # 全局配置
│   └── utils.py         # 工具函数
└── requirements.txt     # Python 依赖
```

## 配置

编辑 `src/config.py` 可调整：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API_BASE_URL | LLM API 地址 | https://ai.opendoor.cn/v1 |
| CHAT_MODEL | 对话模型 | gpt-4.1-mini |
| TTS_VOICE | TTS 声音 | zh-CN-XiaoxiaoNeural |
| TTS_RATE | 语速 | +0% |
| PAGE_PADDING | 每页额外停留时间 | 1.0 秒 |

## 技术栈

- **Python 3** — 主要语言
- **OpenAI API** — 内容分析和分镜生成
- **edge-tts** — 微软 TTS 语音合成
- **Playwright** — 无头浏览器截帧
- **ffmpeg** — 视频编码合成

## 许可证

[MIT](LICENSE)
