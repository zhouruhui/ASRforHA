"""
通用中文云语音识别组件，支持火山引擎(豆包)和腾讯云ASR服务。
"""
import logging
import os
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.components import stt
# 直接导入async_setup_legacy_entry_from_platform函数
from homeassistant.components.stt import async_setup_legacy_entry_from_platform

from .const import (
    DOMAIN,
    CONF_TYPE,
    CONF_APPID,
    CONF_ACCESS_TOKEN,
    CONF_CLUSTER,
    CONF_OUTPUT_DIR,
    CONF_SECRET_ID,
    CONF_SECRET_KEY,
    CONF_ENABLE_VAD,
    CONF_VAD_MODE,
    TYPE_DOUBAO,
    TYPE_TENCENT,
    VAD_MODE_NORMAL,
    VAD_MODE_LOW,
    VAD_MODE_HIGH,
    DEFAULT_ENABLE_VAD,
    DEFAULT_VAD_MODE,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TYPE): cv.string,
        vol.Required(CONF_APPID): cv.string,
        vol.Optional(CONF_ACCESS_TOKEN): cv.string,
        vol.Optional(CONF_CLUSTER): cv.string,
        vol.Optional(CONF_SECRET_ID): cv.string,
        vol.Optional(CONF_SECRET_KEY): cv.string,
        vol.Optional(CONF_OUTPUT_DIR, default="tmp/"): cv.string,
        vol.Optional(CONF_ENABLE_VAD, default=DEFAULT_ENABLE_VAD): cv.boolean,
        vol.Optional(CONF_VAD_MODE, default=DEFAULT_VAD_MODE): vol.In(
            [VAD_MODE_NORMAL, VAD_MODE_LOW, VAD_MODE_HIGH]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.string: SERVICE_SCHEMA,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """设置通用中文云ASR组件。"""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    hass.data[DOMAIN] = {}

    for service_name, service_config in conf.items():
        service_type = service_config[CONF_TYPE]
        
        # 确保输出目录存在
        output_dir = service_config.get(CONF_OUTPUT_DIR, "tmp/")
        os.makedirs(output_dir, exist_ok=True)
        
        # VAD相关配置
        enable_vad = service_config.get(CONF_ENABLE_VAD, DEFAULT_ENABLE_VAD)
        vad_mode = service_config.get(CONF_VAD_MODE, DEFAULT_VAD_MODE)
        
        vad_processor = None
        if enable_vad:
            from .vad import VadProcessor, VadMode
            # 转换VAD模式字符串为枚举值
            mode_map = {
                VAD_MODE_NORMAL: VadMode.NORMAL,
                VAD_MODE_LOW: VadMode.LOW,
                VAD_MODE_HIGH: VadMode.HIGH,
            }
            vad_processor = VadProcessor(mode=mode_map.get(vad_mode, VadMode.NORMAL))
        
        if service_type == TYPE_DOUBAO:
            from .doubao_provider import DoubaoProvider
            provider = DoubaoProvider(
                service_name,
                service_config[CONF_APPID],
                service_config[CONF_ACCESS_TOKEN],
                service_config.get(CONF_CLUSTER, "volcengine_input_common"),
                output_dir,
                vad_processor,
            )
            
        elif service_type == TYPE_TENCENT:
            from .tencent_provider import TencentProvider
            provider = TencentProvider(
                service_name,
                service_config[CONF_APPID],
                service_config.get(CONF_SECRET_ID, ""),
                service_config.get(CONF_SECRET_KEY, ""),
                output_dir,
                vad_processor,
            )
        else:
            _LOGGER.error(f"不支持的ASR类型: {service_type}")
            continue

        hass.data[DOMAIN][service_name] = provider
        
        # 使用新API注册STT提供程序
        # 创建一个配置项，稍后会由async_get_engine函数使用
        hass.async_create_task(
            async_setup_legacy_entry_from_platform(
                hass,
                "stt",
                DOMAIN,
                {"name": service_name},
                {},
                service_name,
            )
        )
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置项。"""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项。"""
    return True 