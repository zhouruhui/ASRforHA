"""Constants for the Volcengine ASR integration."""

DOMAIN = "volcengine_asr"

# Configuration Keys
CONF_APP_ID = "app_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_RESOURCE_ID = "resource_id"
CONF_SERVICE_URL = "service_url"
CONF_LANGUAGE = "language"
CONF_AUDIO_FORMAT = "audio_format"
CONF_AUDIO_RATE = "audio_rate"
CONF_AUDIO_BITS = "audio_bits"
CONF_AUDIO_CHANNEL = "audio_channel"
CONF_ENABLE_ITN = "enable_itn"
CONF_ENABLE_PUNC = "enable_punc"
CONF_RESULT_TYPE = "result_type"
CONF_SHOW_UTTERANCES = "show_utterances"
CONF_PERFORMANCE_MODE = "performance_mode"
CONF_DEBUG_MODE = "debug_mode"
CONF_BATCH_SIZE = "batch_size"
CONF_TIMEOUT_SEND = "timeout_send"
CONF_TIMEOUT_FINAL = "timeout_final"
# VAD配置项
CONF_END_WINDOW_SIZE = "end_window_size"
CONF_FORCE_TO_SPEECH_TIME = "force_to_speech_time"
CONF_LOG_TEXT_CHANGE_ONLY = "log_text_change_only"
# 调试日志配置
CONF_ENABLE_PERF_LOG = "enable_perf_log"
CONF_LOG_LEVEL = "log_level"

# Default values
DEFAULT_SERVICE_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
DEFAULT_LANGUAGE = "zh-CN"
DEFAULT_AUDIO_FORMAT = "pcm"  # Corresponds to AudioFormats.PCM
DEFAULT_AUDIO_RATE = 16000    # Corresponds to AudioSampleRates.SR_16KHZ
DEFAULT_AUDIO_BITS = 16
DEFAULT_AUDIO_CHANNEL = 1     # Corresponds to AudioChannels.MONO
DEFAULT_ENABLE_ITN = True
DEFAULT_ENABLE_PUNC = True
DEFAULT_RESULT_TYPE = "single"
DEFAULT_SHOW_UTTERANCES = False
DEFAULT_PERFORMANCE_MODE = True
DEFAULT_DEBUG_MODE = False
DEFAULT_BATCH_SIZE = 5
DEFAULT_TIMEOUT_SEND = 0.1
DEFAULT_TIMEOUT_FINAL = 3.0
# VAD默认值
DEFAULT_END_WINDOW_SIZE = 2000      # 修改为2000毫秒，大幅增大窗口减少语音被截断的问题
DEFAULT_FORCE_TO_SPEECH_TIME = 100  # 修改为100毫秒，增强语音检测灵敏度
DEFAULT_LOG_TEXT_CHANGE_ONLY = True # 只在文本变化时记录日志
# 调试日志默认值
DEFAULT_ENABLE_PERF_LOG = False     # 是否启用性能日志
DEFAULT_LOG_LEVEL = "info"          # 日志级别 (debug, info, warning, error)

# Performance optimization values
PERF_AUDIO_BATCH_SIZE = 10  # 从5增加到10，减少发送次数
PERF_RESPONSE_TIMEOUT_SEND = 0.05  # 从0.1减少到0.05，减少等待时间
PERF_RESPONSE_TIMEOUT_FINAL = 2.0  # 从1.0增加到2.0，增加最终等待时间，确保完整识别

# 日志标签
LOG_TAG_AUDIO_SEND = "AUDIO_SEND"           # 音频发送
LOG_TAG_RESPONSE_RECEIVE = "RESP_RECEIVE"   # 响应接收
LOG_TAG_TEXT_EXTRACT = "TEXT_EXTRACT"       # 文本提取
LOG_TAG_WEBSOCKET = "WEBSOCKET"             # WebSocket连接
LOG_TAG_VAD = "VAD"                         # VAD处理

