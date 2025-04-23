"""
通用中文云语音识别组件常量定义。
"""

DOMAIN = "cloud_asr"

# 配置键
CONF_TYPE = "type"
CONF_APPID = "appid"
CONF_ACCESS_TOKEN = "access_token"
CONF_CLUSTER = "cluster"
CONF_OUTPUT_DIR = "output_dir"
CONF_SECRET_ID = "secret_id"
CONF_SECRET_KEY = "secret_key"
CONF_ENABLE_VAD = "enable_vad"
CONF_VAD_MODE = "vad_mode"

# 语音识别类型
TYPE_DOUBAO = "doubao"
TYPE_TENCENT = "tencent"

# VAD模式
VAD_MODE_NORMAL = "normal"
VAD_MODE_LOW = "low"
VAD_MODE_HIGH = "high"

# 默认值
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_BIT_DEPTH = 16
DEFAULT_CHANNELS = 1
DEFAULT_LANGUAGE = "zh-CN"
DEFAULT_TIMEOUT = 10
DEFAULT_ENABLE_VAD = True
DEFAULT_VAD_MODE = VAD_MODE_NORMAL 