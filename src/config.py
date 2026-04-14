"""全局配置"""

# LLM API
API_BASE_URL = "https://ai.opendoor.cn/v1"
API_KEY = ""  # 从环境变量 BLOG_VIDEO_API_KEY 读取
CHAT_MODEL = "gpt-4.1-mini"

# TTS
TTS_VOICE = "zh-CN-XiaoxiaoNeural"
TTS_RATE = "+0%"

# 视频尺寸
SIZES = {
    "vertical": {"width": 1080, "height": 1920, "label": "抖音 9:16"},
    "horizontal": {"width": 1920, "height": 1080, "label": "YouTube 16:9"},
}

# 每页停留基础时间（秒），实际由 TTS 音频时长决定
MIN_PAGE_DURATION = 3.0
PAGE_PADDING = 1.0  # TTS 结束后额外停留

# 输出目录
OUTPUT_DIR = "output"
VIDEOS_DIR = "output/videos"   # 最终视频统一存放
TEMP_DIR = "output/temp"       # 中间文件（脚本、音频、幻灯片、帧）
