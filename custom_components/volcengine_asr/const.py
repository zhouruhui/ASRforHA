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

