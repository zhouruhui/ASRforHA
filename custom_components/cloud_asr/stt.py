"""
通用中文云语音识别组件STT平台集成。
"""
import logging
import voluptuous as vol

from homeassistant.components import stt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_get_engine(hass, config, discovery_info=None):
    """返回STT引擎。
    
    这是新版Home Assistant STT API需要的入口点方法。
    """
    if discovery_info is None:
        _LOGGER.error("未提供discovery_info，无法创建STT引擎")
        return None

    name = discovery_info["name"]
    provider = hass.data[DOMAIN].get(name)

    if provider is None:
        _LOGGER.error("未找到名为 %s 的ASR提供程序", name)
        return None

    _LOGGER.info("创建STT引擎: %s", name)
    return CloudSpeechToTextEntity(name, provider)


class CloudSpeechToTextEntity(stt.SpeechToTextEntity):
    """通用中文云ASR语音转文字实体。"""

    def __init__(self, name, provider):
        """初始化语音转文字实体。"""
        self._name = name
        self.provider = provider
        _LOGGER.debug("初始化语音转文字实体: %s", self._name)
        
    @property
    def name(self):
        """返回实体名称。"""
        return self._name

    @name.setter
    def name(self, value):
        """设置实体名称。

        这是为了兼容Home Assistant的legacy STT API。
        在legacy.py中会尝试设置name属性。
        """
        self._name = value
        _LOGGER.debug("设置实体名称为: %s", value)

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
        try:
            _LOGGER.debug(
                "开始处理音频流，语言: %s, 格式: %s, 编解码器: %s, 采样率: %s", 
                metadata.language,
                metadata.format,
                metadata.codec,
                metadata.sample_rate
            )
            result = await self.provider.async_process_audio_stream(metadata, stream)
            return result
        except Exception as err:
            _LOGGER.exception("处理音频流失败: %s", err)
            # 使用result参数创建SpeechResult
            _LOGGER.debug("创建备用SpeechResult(result)")
            return stt.SpeechResult(result="") 