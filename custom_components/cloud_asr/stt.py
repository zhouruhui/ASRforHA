"""
通用中文云语音识别组件STT平台集成。
"""
import logging
import voluptuous as vol

from homeassistant.components import stt
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None
):
    """设置STT平台。"""
    if discovery_info is None:
        return

    name = discovery_info["name"]
    provider = hass.data[DOMAIN].get(name)

    if provider is None:
        _LOGGER.error(f"未找到名为 {name} 的ASR提供程序")
        return

    async_add_entities([CloudSpeechToText(name, provider)])


class CloudSpeechToText(stt.SpeechToTextEntity):
    """通用中文云ASR语音转文字实体。"""

    def __init__(self, name, provider):
        """初始化语音转文字实体。"""
        self.name = name
        self.provider = provider
        
    @property
    def name(self):
        """返回实体名称。"""
        return self._name

    @name.setter
    def name(self, value):
        """设置实体名称。"""
        self._name = value

    @property
    def supported_languages(self):
        """返回支持的语言列表。"""
        return ["zh-CN", "en-US"]

    @property
    def supported_formats(self):
        """返回支持的音频格式。"""
        return [stt.AudioFormats.WAV]

    async def async_process_audio_stream(self, metadata, stream):
        """处理音频流并返回识别结果。"""
        return await self.provider.async_process_audio_stream(metadata, stream) 