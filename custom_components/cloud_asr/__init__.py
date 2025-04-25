"""
通用中文云语音识别组件，支持火山引擎(豆包)和腾讯云ASR服务。
"""
import logging
import os
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.components import stt
# 导入平台加载和发现函数
from homeassistant.setup import async_setup_component
from homeassistant.helpers import discovery

from .const import (
    DOMAIN,
    CONF_TYPE,
    CONF_APPID,
    CONF_ACCESS_TOKEN,
    CONF_CLUSTER,
    CONF_OUTPUT_DIR,
    CONF_SECRET_ID,
    CONF_SECRET_KEY,
    TYPE_DOUBAO,
    TYPE_TENCENT,
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
        
        if service_type == TYPE_DOUBAO:
            from .doubao_provider import DoubaoProvider
            provider = DoubaoProvider(
                service_name,
                service_config[CONF_APPID],
                service_config[CONF_ACCESS_TOKEN],
                service_config.get(CONF_CLUSTER, "volcengine_input_common"),
                output_dir,
            )
            
        elif service_type == TYPE_TENCENT:
            from .tencent_provider import TencentProvider
            provider = TencentProvider(
                service_name,
                service_config[CONF_APPID],
                service_config.get(CONF_SECRET_ID, ""),
                service_config.get(CONF_SECRET_KEY, ""),
                output_dir,
            )
        else:
            _LOGGER.error(f"不支持的ASR类型: {service_type}")
            continue

        hass.data[DOMAIN][service_name] = provider
        
        # 确保STT组件已加载，使用in操作符检查
        if "stt" not in hass.config.components:
            if not await async_setup_component(hass, "stt", config):
                _LOGGER.error("无法加载STT组件")
                return False

        # 使用标准的discovery机制来加载STT平台
        discovery_info = {"name": service_name}
        hass.async_create_task(
            discovery.async_load_platform(
                hass, 
                "stt", 
                DOMAIN, 
                discovery_info, 
                config
            )
        )
    
    # 注册测试语音识别服务
    async def handle_test_asr(call: ServiceCall):
        """处理测试ASR服务。"""
        service_name = call.data.get("service_name")
        text = call.data.get("text", "测试语音识别服务")
        
        if not service_name or service_name not in hass.data[DOMAIN]:
            _LOGGER.error(f"未找到语音识别服务: {service_name}")
            return
        
        _LOGGER.info(f"测试语音识别服务 {service_name}: {text}")
        hass.states.async_set(f"{DOMAIN}.{service_name}_test", text)
    
    hass.services.async_register(
        DOMAIN, 
        "test_asr", 
        handle_test_asr, 
        vol.Schema({
            vol.Required("service_name"): cv.string,
            vol.Optional("text"): cv.string,
        })
    )
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置项。"""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项。"""
    return True 