"""
语音活动检测(VAD)模块。
"""
import numpy as np
import logging
from enum import Enum
import wave
import io

_LOGGER = logging.getLogger(__name__)

class VadMode(Enum):
    """VAD灵敏度模式。"""
    NORMAL = 0  # 正常模式
    LOW = 1     # 低灵敏度，需要更强的语音信号
    HIGH = 2    # 高灵敏度，弱语音信号也能检测

class VadProcessor:
    """基于能量的简单VAD处理器。"""
    
    def __init__(self, mode=VadMode.NORMAL, sample_rate=16000, frame_duration_ms=30):
        """初始化VAD处理器。
        
        Args:
            mode: VAD敏感度模式
            sample_rate: 采样率
            frame_duration_ms: 帧长度(毫秒)
        """
        self.mode = mode
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        
        # 计算每帧样本数
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # 设置能量阈值，根据模式调整
        if mode == VadMode.LOW:
            self.energy_threshold = 0.025  # 较高阈值，需要更强信号
        elif mode == VadMode.HIGH:
            self.energy_threshold = 0.0035  # 较低阈值，弱信号也能检测
        else:  # NORMAL
            self.energy_threshold = 0.0075
            
        # 静音持续帧数阈值
        self.silence_frame_threshold = 15  # 大约450ms的静音判定为结束
        
        # 最短语音段持续时间(帧数)
        self.min_speech_frames = 10  # 大约300ms
        
    def process_wav(self, wav_data):
        """处理WAV音频数据，返回只包含语音的片段。
        
        Args:
            wav_data: WAV格式的音频数据(字节)
            
        Returns:
            处理后的WAV音频数据(字节)
        """
        try:
            # 解析WAV头
            with io.BytesIO(wav_data) as wav_io:
                with wave.open(wav_io, 'rb') as wav_file:
                    params = wav_file.getparams()
                    frames = wav_file.readframes(wav_file.getnframes())
                    
                    # 转换为数组进行处理
                    if params.sampwidth == 2:  # 16-bit音频
                        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    elif params.sampwidth == 1:  # 8-bit音频
                        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 255.0 - 0.5
                    else:
                        _LOGGER.error(f"不支持的音频位深: {params.sampwidth * 8}位")
                        return wav_data
            
            # 检测语音段
            speech_segments = self._detect_speech(audio)
            
            if not speech_segments:
                _LOGGER.warning("未检测到语音片段")
                return wav_data
                
            # 合并检测到的语音段
            speech_audio = self._merge_segments(audio, speech_segments)
            
            # 转换回WAV格式
            output_wav = self._audio_to_wav(speech_audio, params)
            
            return output_wav
            
        except Exception as e:
            _LOGGER.error(f"VAD处理失败: {e}")
            return wav_data  # 出错时返回原始数据
    
    def _detect_speech(self, audio):
        """检测音频中的语音片段。
        
        Args:
            audio: 音频数据(浮点数组)
            
        Returns:
            语音片段列表，每个片段为(开始帧索引, 结束帧索引)
        """
        frames = []
        for i in range(0, len(audio), self.frame_size):
            if i + self.frame_size <= len(audio):
                frames.append(audio[i:i+self.frame_size])
        
        # 计算每帧能量
        frame_energies = [np.mean(np.abs(frame)) for frame in frames]
        
        # 检测语音段
        in_speech = False
        speech_segments = []
        current_segment_start = 0
        silence_frame_count = 0
        
        for i, energy in enumerate(frame_energies):
            if energy > self.energy_threshold:
                if not in_speech:
                    in_speech = True
                    current_segment_start = i
                silence_frame_count = 0
            else:
                if in_speech:
                    silence_frame_count += 1
                    # 如果静音持续超过阈值，则认为语音结束
                    if silence_frame_count >= self.silence_frame_threshold:
                        if i - current_segment_start > self.min_speech_frames:
                            speech_segments.append((current_segment_start, i - self.silence_frame_threshold))
                        in_speech = False
        
        # 处理最后一个语音段
        if in_speech and len(frames) - current_segment_start > self.min_speech_frames:
            speech_segments.append((current_segment_start, len(frames) - 1))
            
        return speech_segments
    
    def _merge_segments(self, audio, segments):
        """合并语音片段。
        
        Args:
            audio: 原始音频数据
            segments: 语音片段列表
            
        Returns:
            合并后的音频数据
        """
        if not segments:
            return audio
            
        merged_audio = np.array([], dtype=audio.dtype)
        
        for start, end in segments:
            start_sample = start * self.frame_size
            end_sample = min((end + 1) * self.frame_size, len(audio))
            merged_audio = np.append(merged_audio, audio[start_sample:end_sample])
            
        return merged_audio
    
    def _audio_to_wav(self, audio, original_params):
        """将音频数据转换为WAV格式。
        
        Args:
            audio: 音频数据(浮点数组)
            original_params: 原始WAV参数
            
        Returns:
            WAV格式的音频数据(字节)
        """
        # 转换回整数格式
        if original_params.sampwidth == 2:
            audio_int = (audio * 32768.0).astype(np.int16)
        elif original_params.sampwidth == 1:
            audio_int = ((audio + 0.5) * 255.0).astype(np.uint8)
        else:
            audio_int = audio
            
        # 写入WAV文件
        output_buffer = io.BytesIO()
        with wave.open(output_buffer, 'wb') as wav_file:
            wav_file.setparams(original_params)
            wav_file.writeframes(audio_int.tobytes())
            
        return output_buffer.getvalue() 