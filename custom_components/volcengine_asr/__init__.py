"""The Volcengine ASR integration."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "volcengine_asr"
_LOGGER = logging.getLogger(__name__)

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

DEFAULT_SERVICE_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
DEFAULT_LANGUAGE = "zh-CN"
DEFAULT_AUDIO_FORMAT = "pcm"
DEFAULT_AUDIO_RATE = 16000
DEFAULT_AUDIO_BITS = 16
DEFAULT_AUDIO_CHANNEL = 1
DEFAULT_ENABLE_ITN = True
DEFAULT_ENABLE_PUNC = True
DEFAULT_RESULT_TYPE = "single"
DEFAULT_SHOW_UTTERANCES = False

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_APP_ID): cv.string,
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Required(CONF_RESOURCE_ID): cv.string,
                vol.Optional(CONF_SERVICE_URL, default=DEFAULT_SERVICE_URL): cv.string,
                vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): cv.string,
                vol.Optional(CONF_AUDIO_FORMAT, default=DEFAULT_AUDIO_FORMAT): cv.string,
                vol.Optional(CONF_AUDIO_RATE, default=DEFAULT_AUDIO_RATE): cv.positive_int,
                vol.Optional(CONF_AUDIO_BITS, default=DEFAULT_AUDIO_BITS): cv.positive_int,
                vol.Optional(CONF_AUDIO_CHANNEL, default=DEFAULT_AUDIO_CHANNEL): cv.positive_int,
                vol.Optional(CONF_ENABLE_ITN, default=DEFAULT_ENABLE_ITN): cv.boolean,
                vol.Optional(CONF_ENABLE_PUNC, default=DEFAULT_ENABLE_PUNC): cv.boolean,
                vol.Optional(CONF_RESULT_TYPE, default=DEFAULT_RESULT_TYPE): cv.string,
                vol.Optional(CONF_SHOW_UTTERANCES, default=DEFAULT_SHOW_UTTERANCES): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Volcengine ASR component."""
    _LOGGER.info("Setting up Volcengine ASR integration")
    conf = config.get(DOMAIN)
    if not conf:
        _LOGGER.error("Volcengine ASR configuration not found in configuration.yaml")
        return False

    hass.data[DOMAIN] = conf

    # Forward the setup to the stt platform.
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform("stt", DOMAIN, {}, config)
    )
    _LOGGER.info("Volcengine ASR integration setup complete")
    return True

