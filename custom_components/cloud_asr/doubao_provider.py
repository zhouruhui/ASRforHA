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
        
        # 确保音频数据是有效的WAV格式
        if not audio_data.startswith(b'RIFF'):
            _LOGGER.debug("添加WAV头部到音频数据")
            audio_data = await asyncio.to_thread(self._add_wav_header, audio_data, sample_rate)
            
        temp_file = os.path.join(self.output_dir, f"{uuid.uuid4()}.wav")
        
        # 使用异步文件操作
        await asyncio.to_thread(self._write_file, temp_file, audio_data)
        
        try:
            # 如果启用了VAD，先进行处理
            if self.vad_processor:
                # 使用异步读取文件
                original_audio = await asyncio.to_thread(self._read_file, temp_file)
                
                _LOGGER.debug("使用VAD处理音频")
                processed_audio = await asyncio.to_thread(self.vad_processor.process_wav, original_audio)
                
                # 保存VAD处理后的音频
                vad_temp_file = os.path.join(self.output_dir, f"vad_{uuid.uuid4()}.wav")
                await asyncio.to_thread(self._write_file, vad_temp_file, processed_audio)
                
                # 替换为处理后的临时文件
                temp_file = vad_temp_file
            
            text = await self._recognize_audio(temp_file, sample_rate, language)
            # 根据新API创建结果
            return stt.SpeechResult(text=text)
        except Exception as err:
            _LOGGER.error("火山引擎(豆包)语音识别失败: %s", err)
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