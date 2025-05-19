"""The Volcengine ASR integration."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery # Added import

from .const import (
    DOMAIN,
    CONF_APP_ID,
    CONF_ACCESS_TOKEN,
    CONF_RESOURCE_ID,
    CONF_SERVICE_URL,
    CONF_LANGUAGE,
    CONF_AUDIO_FORMAT,
    CONF_AUDIO_RATE,
    CONF_AUDIO_BITS,
    CONF_AUDIO_CHANNEL,
    CONF_ENABLE_ITN,
    CONF_ENABLE_PUNC,
    CONF_RESULT_TYPE,
    CONF_SHOW_UTTERANCES,
    CONF_PERFORMANCE_MODE,
    CONF_END_WINDOW_SIZE,
    CONF_FORCE_TO_SPEECH_TIME,
    CONF_LOG_TEXT_CHANGE_ONLY,
    DEFAULT_SERVICE_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_AUDIO_RATE,
    DEFAULT_AUDIO_BITS,
    DEFAULT_AUDIO_CHANNEL,
    DEFAULT_ENABLE_ITN,
    DEFAULT_ENABLE_PUNC,
    DEFAULT_RESULT_TYPE,
    DEFAULT_SHOW_UTTERANCES,
    DEFAULT_PERFORMANCE_MODE,
    DEFAULT_END_WINDOW_SIZE,
    DEFAULT_FORCE_TO_SPEECH_TIME,
    DEFAULT_LOG_TEXT_CHANGE_ONLY,
)

_LOGGER = logging.getLogger(__name__)

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
                vol.Optional(CONF_PERFORMANCE_MODE, default=DEFAULT_PERFORMANCE_MODE): cv.boolean,
                # VAD相关配置
                vol.Optional(CONF_END_WINDOW_SIZE, default=DEFAULT_END_WINDOW_SIZE): cv.positive_int,
                vol.Optional(CONF_FORCE_TO_SPEECH_TIME, default=DEFAULT_FORCE_TO_SPEECH_TIME): cv.positive_int,
                vol.Optional(CONF_LOG_TEXT_CHANGE_ONLY, default=DEFAULT_LOG_TEXT_CHANGE_ONLY): cv.boolean,
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
        discovery.async_load_platform(hass, "stt", DOMAIN, {}, config) # Changed call
    )
    _LOGGER.info("Volcengine ASR integration setup complete")
    return True

