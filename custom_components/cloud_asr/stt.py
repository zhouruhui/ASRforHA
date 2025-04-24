"""
通用中文云语音识别组件STT平台集成。
"""
import logging
import voluptuous as vol

from homeassistant.components import stt
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_get_engine(hass, config, discovery_info=None):
    """设置STT引擎。"""
    if discovery_info is None:
        return None

    name = discovery_info["name"]
    provider = hass.data[DOMAIN].get(name)

    if provider is None:
        _LOGGER.error(f"未找到名为 {name} 的ASR提供程序")
        return None

    return CloudSpeechToTextEngine(name, provider)


class CloudSpeechToTextEngine(stt.SpeechToTextEntity):
    """通用中文云ASR语音转文字引擎。"""

    def __init__(self, name, provider):
        """初始化语音转文字引擎。"""
        self._name = name
        self.provider = provider
        
    @property
    def name(self):
        """返回实体名称。"""
        return self._name

    @property
    def supported_languages(self):
        """返回支持的语言列表。"""
        return ["zh-CN", "en-US"]

    @property
    def supported_formats(self):
        """返回支持的音频格式。"""
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self):
        """返回支持的编解码器。"""
        return [stt.AudioCodecs.PCM]

    @property 
    def supported_bit_rates(self):
        """返回支持的比特率。"""
        return [16]

    @property
    def supported_sample_rates(self):
        """返回支持的采样率。"""
        return [16000]

    @property
    def supported_channels(self):
        """返回支持的通道数。"""
        return [1]  # 单声道

    async def async_process_audio_stream(self, metadata, stream):
        """处理音频流并返回识别结果。"""
        return await self.provider.async_process_audio_stream(metadata, stream) 