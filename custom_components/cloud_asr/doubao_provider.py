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
import ssl
import os.path
from homeassistant.helpers import aiohttp_client
from homeassistant.util import ssl as ha_ssl

from .const import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TIMEOUT,
    DEFAULT_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)

# 在模块加载时（非事件循环中）创建SSL上下文
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

class DoubaoProvider:
    """火山引擎(豆包)语音识别提供程序。"""

    def __init__(self, name, appid, access_token, cluster, output_dir):
        """初始化火山引擎(豆包)语音识别提供程序。"""
        self.name = name
        self.appid = appid
        self.access_token = access_token
        self.cluster = cluster
        self.output_dir = output_dir
        
        # 构建基本连接参数 - 使用正确的URL
        # 根据文档："The WebSocket API for large language model speech recognition uses wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        
        # 使用模块级别的SSL上下文，避免在初始化时创建
        self.ssl_context = _SSL_CONTEXT
        
    async def async_process_audio_stream(self, metadata, stream):
        """处理音频流并返回识别结果。"""
        sample_rate = DEFAULT_SAMPLE_RATE
        language = metadata.language or DEFAULT_LANGUAGE
        
        # 保存音频流到临时文件
        audio_data = await self._stream_to_bytes(stream)
        
        # 确保音频数据是有效的WAV格式
        if not audio_data.startswith(b'RIFF'):
            _LOGGER.debug("添加WAV头部到音频数据")
            audio_data = await asyncio.to_thread(self._add_wav_header, audio_data, sample_rate)
            
        temp_file = os.path.join(self.output_dir, f"{uuid.uuid4()}.wav")
        
        # 使用异步文件操作
        await asyncio.to_thread(self._write_file, temp_file, audio_data)
        
        try:
            text = await self._recognize_audio(temp_file, sample_rate, language)
            # 使用正确的参数创建结果（根据最新错误日志，应为 text）
            return stt.SpeechResult(text=text)
        except Exception as err:
            _LOGGER.error("火山引擎(豆包)语音识别失败: %s", err)
            # 创建空结果（根据最新错误日志，应为 text）
            return stt.SpeechResult(text="")
        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_file):
                    await asyncio.to_thread(os.remove, temp_file)
            except Exception as e:
                _LOGGER.error("清理临时文件失败: %s", e)
    
    async def _stream_to_bytes(self, stream):
        """将流转换为字节。"""
        audio_data = b""
        try:
            # 处理async_generator类型的流
            async for chunk in stream:
                if not chunk:
                    break
                audio_data += chunk
        except AttributeError:
            # 兼容旧版本的接口，尝试使用read方法
            while True:
                try:
                    chunk = await stream.read(4096)
                    if not chunk:
                        break
                    audio_data += chunk
                except Exception as e:
                    _LOGGER.error("读取音频流出错: %s", e)
                    break
        return audio_data
    
    async def _recognize_audio(self, audio_file, sample_rate, language):
        """发送语音识别请求。"""
        # 根据火山引擎最新文档，使用正确的鉴权方式和URL
        import uuid
        connect_id = str(uuid.uuid4())
        
        # 根据最新文档更新鉴权信息
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            # 使用用户在 configuration.yaml 中配置的 cluster 值作为资源ID
            # !! 用户必须确保此值是火山引擎提供的有效资源ID !!
            # 例如: "volc.bigasr.sauc.duration" 或 "volc.bigasr.sauc.concurrent"
            "X-Api-Resource-Id": self.cluster,
            "X-Api-Connect-Id": connect_id,
            "Content-Type": "application/json"
        }
        
        # 添加资源ID格式检查警告
        if not self.cluster or not self.cluster.startswith("volc."):
            _LOGGER.warning(
                "配置的火山引擎资源ID '%s' 可能格式不正确，" 
                "请检查VolcEngine控制台并确保其以 'volc.' 开头。 "
                "常见的格式如 'volc.bigasr.sauc.duration' 或 'volc.bigasr.sauc.concurrent'.",
                self.cluster
            )
        
        # 准备连接参数 - 简化参数
        request_params = {
            "format": "wav",
            "sample_rate": sample_rate,
            "audio_encoding": "pcm_s16le",
        }
        
        # 添加语言参数
        if language and language.startswith("zh"):
            request_params["lang"] = "zh"
        elif language and language.startswith("en"):
            request_params["lang"] = "en"
            
        # 添加详细调试信息
        _LOGGER.debug("豆包API认证信息: App Key: %s, 资源ID: %s, Connect ID: %s",
                     self.appid, 
                     headers["X-Api-Resource-Id"],
                     connect_id)
            
        ws_url = self.ws_url
        
        try:
            # 建立WebSocket连接
            async with aiohttp.ClientSession() as session:
                _LOGGER.debug("尝试连接豆包API: %s", ws_url)
                _LOGGER.debug("请求头: %s", {k: ('***' if k == 'X-Api-Access-Key' else v) for k, v in headers.items()})
                _LOGGER.debug("请求参数: %s", request_params)
                
                # 使用预创建的SSL上下文
                async with session.ws_connect(
                    ws_url,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                    heartbeat=30,
                    ssl=self.ssl_context
                ) as ws:
                    # 发送初始请求参数
                    _LOGGER.debug("发送初始化参数")
                    await ws.send_json(request_params)
                    
                    # 读取音频文件并发送
                    audio_data = await asyncio.to_thread(self._read_file, audio_file)
                    _LOGGER.debug("读取到音频数据: %d 字节", len(audio_data))
                    
                    # 根据火山引擎WebSocket协议，分批发送音频数据
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i+chunk_size]
                        await ws.send_bytes(chunk)
                        
                    # 发送结束标志
                    _LOGGER.debug("发送结束标志")
                    await ws.send_json({"end": True})
                    
                    # 接收并解析结果
                    final_text = ""
                    _LOGGER.debug("已发送音频数据，等待豆包API响应")
                    async with async_timeout.timeout(DEFAULT_TIMEOUT):
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                _LOGGER.debug("豆包API响应: %s", data)
                                
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
    
    def _write_file(self, file_path, data):
        """写入文件（非阻塞方法，在线程池中执行）"""
        with open(file_path, "wb") as f:
            f.write(data)
            
    def _read_file(self, file_path):
        """读取文件（非阻塞方法，在线程池中执行）"""
        with open(file_path, "rb") as f:
            return f.read()
    
    def _add_wav_header(self, audio_data, sample_rate, channels=1, sample_width=2):
        """为PCM数据添加WAV头部。
        
        Args:
            audio_data: 原始PCM音频数据
            sample_rate: 采样率
            channels: 通道数
            sample_width: 样本宽度（字节）
            
        Returns:
            带WAV头部的音频数据
        """
        import wave
        import io
        
        # 创建内存缓冲区
        wav_buffer = io.BytesIO()
        
        # 创建WAV文件
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
            
        # 获取完整的WAV数据
        wav_buffer.seek(0)
        return wav_buffer.getvalue() 