"""
腾讯云语音识别提供程序。
"""
import logging
import os
import json
import uuid
import base64
import hmac
import hashlib
import time
from datetime import datetime
import aiohttp
import asyncio
from urllib.parse import urlencode
from homeassistant.components import stt

from .const import (
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TIMEOUT,
    DEFAULT_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)

class TencentProvider:
    """腾讯云语音识别提供程序。"""

    def __init__(self, name, appid, secret_id, secret_key, output_dir):
        """初始化腾讯云语音识别提供程序。"""
        self.name = name
        self.appid = appid
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.output_dir = output_dir
        self.service = "asr"
        self.host = "asr.tencentcloudapi.com"
        self.region = "ap-guangzhou"  # 默认区域
        self.version = "2019-06-14"
        self.algorithm = "TC3-HMAC-SHA256"
        self.url = "https://" + self.host
        
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
            # 读取文件转为base64
            with open(temp_file, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode("utf-8")
                
            # 调用腾讯云API进行识别
            text = await self._call_tencent_asr(audio_base64, sample_rate, language)
            return stt.SpeechResult(text)
        except Exception as err:
            _LOGGER.error("腾讯云语音识别失败: %s", err)
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
        
    async def _call_tencent_asr(self, audio_base64, sample_rate, language):
        """调用腾讯云ASR API。使用一句话识别接口"""
        # 设置请求参数
        req_param = {
            "ProjectId": int(self.appid),
            "SubServiceType": 2,  # 一句话识别
            "EngSerViceType": "16k_zh",  # 引擎类型
            "SourceType": 1,  # 音频数据来源 0:语音URL 1:语音数据
            "VoiceFormat": "wav",  # 音频格式
            "Data": audio_base64,  # Base64编码的音频数据
            "DataLen": len(audio_base64),  # 数据长度
            "FilterDirty": 0,  # 是否过滤脏话
            "FilterModal": 0,  # 是否过滤语气词
            "FilterPunc": 0,  # 是否过滤标点符号
            "ConvertNumMode": 1,  # 是否进行数字转换
        }
        
        # 设置语言参数
        if language and language.startswith("zh"):
            req_param["EngSerViceType"] = "16k_zh"
        elif language and language.startswith("en"):
            req_param["EngSerViceType"] = "16k_en"
            
        timestamp = int(time.time())
        
        # 生成签名
        signature = await self._generate_signature(req_param, timestamp)
        
        # 准备请求头
        headers = {
            "Content-Type": "application/json",
            "Host": self.host,
            "X-TC-Action": "SentenceRecognition",
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
            "Authorization": signature
        }
        
        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=req_param, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status == 200:
                        result = await response.json()
                        _LOGGER.debug("腾讯云ASR响应: %s", result)
                        
                        if "Response" in result and "Result" in result["Response"]:
                            return result["Response"]["Result"]
                        elif "Response" in result and "Error" in result["Response"]:
                            error_msg = result["Response"]["Error"].get("Message", "未知错误")
                            _LOGGER.error("腾讯云ASR错误: %s", error_msg)
                    else:
                        _LOGGER.error("腾讯云ASR请求失败，状态码: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("腾讯云ASR请求超时")
        except Exception as err:
            _LOGGER.error("腾讯云ASR请求异常: %s", err)
            
        return ""
        
    async def _generate_signature(self, params, timestamp):
        """生成腾讯云API签名。"""
        # 1. 组装规范请求字符串
        request_timestamp = timestamp
        request_date = datetime.utcfromtimestamp(request_timestamp).strftime("%Y-%m-%d")
        
        # 规范请求体
        canonical_request = "POST\n"
        canonical_request += "/\n"
        canonical_request += "\n"
        canonical_request += "content-type:application/json\n"
        canonical_request += "host:" + self.host + "\n"
        canonical_request += "\n"
        canonical_request += "content-type;host\n"
        
        # 计算请求体哈希
        request_body = json.dumps(params)
        payload_hash = hashlib.sha256(request_body.encode("utf-8")).hexdigest()
        canonical_request += payload_hash
        
        # 2. 组装签名字符串
        credential_scope = f"{request_date}/{self.service}/tc3_request"
        canonical_request_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{self.algorithm}\n{timestamp}\n{credential_scope}\n{canonical_request_hash}"
        
        # 3. 计算签名
        # 计算派生签名密钥
        secret_date = self._sign(("TC3" + self.secret_key).encode("utf-8"), request_date)
        secret_service = self._sign(secret_date, self.service)
        secret_signing = self._sign(secret_service, "tc3_request")
        
        # 计算签名
        signature = hmac.new(
            secret_signing,
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # 4. 组装授权头
        auth_str = (
            f"{self.algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders=content-type;host, "
            f"Signature={signature}"
        )
        
        return auth_str
        
    def _sign(self, key, msg):
        """计算签名。"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest() 