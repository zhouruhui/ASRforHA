"""
火山引擎(豆包)语音识别提供程序。
"""
import logging
import os
import asyncio
import json
import tempfile
import uuid
import aiohttp
import async_timeout
from homeassistant.components import stt

from .const import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TIMEOUT,
    DEFAULT_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)

class DoubaoProvider:
    """火山引擎(豆包)语音识别提供程序。"""

    def __init__(self, name, appid, access_token, cluster, output_dir, vad_processor=None):
        """初始化火山引擎(豆包)语音识别提供程序。"""
        self.name = name
        self.appid = appid
        self.access_token = access_token
        self.cluster = cluster
        self.output_dir = output_dir
        self.vad_processor = vad_processor
        
        # 构建基本连接参数
        self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        
    async def async_process_audio_stream(self, metadata, stream):
        """处理音频流并返回识别结果。"""
        sample_rate = DEFAULT_SAMPLE_RATE
        language = metadata.language or DEFAULT_LANGUAGE
        
        # 保存音频流到临时文件
        audio_data = await self._stream_to_bytes(stream)
        temp_file = os.path.join(self.output_dir, f"{uuid.uuid4()}.wav")
        
        with open(temp_file, "wb") as f:
            f.write(audio_data)
        
        try:
            # 如果启用了VAD，先进行处理
            if self.vad_processor:
                with open(temp_file, "rb") as f:
                    original_audio = f.read()
                
                _LOGGER.debug("使用VAD处理音频")
                processed_audio = self.vad_processor.process_wav(original_audio)
                
                # 保存VAD处理后的音频
                vad_temp_file = os.path.join(self.output_dir, f"vad_{uuid.uuid4()}.wav")
                with open(vad_temp_file, "wb") as f:
                    f.write(processed_audio)
                
                # 替换为处理后的临时文件
                temp_file = vad_temp_file
            
            text = await self._recognize_audio(temp_file, sample_rate, language)
            return stt.SpeechResult(text)
        except Exception as err:
            _LOGGER.error("火山引擎(豆包)语音识别失败: %s", err)
            return stt.SpeechResult("")
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    async def _stream_to_bytes(self, stream):
        """将流转换为字节。"""
        audio_data = b""
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            audio_data += chunk
        return audio_data
    
    async def _recognize_audio(self, audio_file, sample_rate, language):
        """发送语音识别请求。"""
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # 准备连接参数
        request_params = {
            "appid": self.appid,
            "resource_id": self.cluster,  # 使用cluster作为resource_id
            "format": "wav",
            "sample_rate": sample_rate,
            "audio_encoding": "pcm_s16le",
            "force_to_speech_time": 0,
            "end_window_size": 800,
        }
        
        # 添加语言参数
        if language and language.startswith("zh"):
            request_params["lang"] = "zh"
        elif language and language.startswith("en"):
            request_params["lang"] = "en"
            
        try:
            # 建立WebSocket连接，这里使用WebSocket流式API
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.ws_url, headers=headers, timeout=DEFAULT_TIMEOUT) as ws:
                    # 发送初始请求参数
                    await ws.send_json(request_params)
                    
                    # 读取音频文件并发送
                    with open(audio_file, "rb") as f:
                        audio_data = f.read()
                    
                    # 根据火山引擎WebSocket协议，分批发送音频数据
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i+chunk_size]
                        await ws.send_bytes(chunk)
                    
                    # 发送结束标志
                    await ws.send_json({"end": True})
                    
                    # 接收并解析结果
                    final_text = ""
                    async with async_timeout.timeout(DEFAULT_TIMEOUT):
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # 处理不同类型的结果
                                if "text" in data:
                                    final_text = data["text"]
                                
                                # 判断是否结束
                                if data.get("status", "") == "final" or "completed" in data:
                                    break
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                _LOGGER.error("WebSocket连接错误: %s", ws.exception())
                                break
                    
                    return final_text
                    
        except asyncio.TimeoutError:
            _LOGGER.error("火山引擎(豆包)语音识别请求超时")
            return ""
        except Exception as err:
            _LOGGER.error("火山引擎(豆包)语音识别异常: %s", err)
            return "" 