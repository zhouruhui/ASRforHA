"""Support for Volcengine ASR speech-to-text service."""
import asyncio
import logging
import json
import uuid
import struct
import aiohttp # Import aiohttp

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechToTextEntity,
)
from homeassistant.components.stt.models import (
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.aiohttp_client import async_get_clientsession # For getting HA's client session

from .const import (
    DOMAIN,
    CONF_APP_ID,
    CONF_ACCESS_TOKEN,
    CONF_RESOURCE_ID,
    CONF_SERVICE_URL,
    CONF_LANGUAGE,
    CONF_AUDIO_FORMAT,
    CONF_AUDIO_RATE,
    CONF_AUDIO_BITS,
    CONF_AUDIO_CHANNEL,
    CONF_ENABLE_ITN,
    CONF_ENABLE_PUNC,
    CONF_RESULT_TYPE,
    CONF_SHOW_UTTERANCES,
    DEFAULT_SERVICE_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_AUDIO_RATE,
    DEFAULT_AUDIO_BITS,
    DEFAULT_AUDIO_CHANNEL,
    DEFAULT_ENABLE_ITN,
    DEFAULT_ENABLE_PUNC,
    DEFAULT_RESULT_TYPE,
    DEFAULT_SHOW_UTTERANCES,
)

_LOGGER = logging.getLogger(__name__)

async def async_get_engine(hass: HomeAssistant, config: ConfigType, discovery_info: DiscoveryInfoType | None = None):
    """Set up Volcengine ASR STT component."""
    return VolcengineASRProvider(hass, hass.data[DOMAIN])

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType, # platform config
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Volcengine ASR STT platform."""
    _LOGGER.info("Setting up Volcengine ASR STT platform")
    component_config = hass.data.get(DOMAIN)
    if not component_config:
        _LOGGER.error("Volcengine ASR main component config not found in hass.data")
        return
    
    async_add_entities([VolcengineASRProvider(hass, component_config)])
    _LOGGER.info("Volcengine ASR STT platform setup complete")


class VolcengineASRProvider(SpeechToTextEntity):
    """Volcengine ASR speech-to-text provider."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the provider."""
        self.hass = hass
        self._config = config
        self._attr_name = "Volcengine ASR"
        self.name = "Volcengine ASR" 
        self._connect_id = str(uuid.uuid4())

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return [self._config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bitrates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported samplerates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]
    
    def _preprocess_payload(self, payload_bytes: bytes) -> bytes:
        """Preprocesses the payload to remove any non-JSON prefix."""
        try:
            json_start_index = payload_bytes.find(b"{")
            if json_start_index == -1:
                _LOGGER.warning(f"ASR response payload does not contain JSON start character 	{{	. Payload (hex): {payload_bytes.hex()}")
                return b""
            if json_start_index > 0:
                _LOGGER.debug(f"ASR response payload has prefix. Original (hex): {payload_bytes.hex()}, Stripped (hex): {payload_bytes[json_start_index:].hex()}")
            return payload_bytes[json_start_index:]
        except Exception as e:
            _LOGGER.error(f"Error during payload preprocessing: {e}. Original payload (hex): {payload_bytes.hex()}")
            return payload_bytes

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: asyncio.StreamReader
    ) -> SpeechResult:
        _LOGGER.debug(f"Processing audio stream with metadata: {metadata}")
        if not self.check_metadata(metadata):
            _LOGGER.error(
                f"Unsupported audio metadata: format={metadata.format}, "
                f"codec={metadata.codec}, rate={metadata.sample_rate}, "
                f"bits={metadata.bit_rate}, channels={metadata.channel}. "
                f"Supported: formats={self.supported_formats}, codecs={self.supported_codecs}, "
                f"rates={self.supported_sample_rates}, bits={self.supported_bit_rates}, "
                f"channels={self.supported_channels}"
            )
            return SpeechResult(None, SpeechResultState.ERROR)

        app_id = self._config[CONF_APP_ID]
        access_token = self._config[CONF_ACCESS_TOKEN]
        resource_id = self._config[CONF_RESOURCE_ID]
        service_url = self._config.get(CONF_SERVICE_URL, DEFAULT_SERVICE_URL)
        self._connect_id = str(uuid.uuid4())

        custom_headers = {
            "X-Api-App-Key": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Connect-Id": self._connect_id,
        }
        volc_audio_params = {
            "format": self._config.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
            "rate": self._config.get(CONF_AUDIO_RATE, DEFAULT_AUDIO_RATE),
            "bits": self._config.get(CONF_AUDIO_BITS, DEFAULT_AUDIO_BITS),
            "channel": self._config.get(CONF_AUDIO_CHANNEL, DEFAULT_AUDIO_CHANNEL),
            "codec": "raw",
        }
        request_params = {
            "model_name": "bigmodel",
            "language": self._config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            "enable_itn": self._config.get(CONF_ENABLE_ITN, DEFAULT_ENABLE_ITN),
            "enable_punc": self._config.get(CONF_ENABLE_PUNC, DEFAULT_ENABLE_PUNC),
            "result_type": self._config.get(CONF_RESULT_TYPE, DEFAULT_RESULT_TYPE),
            "show_utterances": self._config.get(CONF_SHOW_UTTERANCES, DEFAULT_SHOW_UTTERANCES),
        }
        full_client_request_payload = {
            "user": {"uid": "homeassistant_user"},
            "audio": volc_audio_params,
            "request": request_params,
        }

        session = async_get_clientsession(self.hass)
        final_text_set = set()
        server_marked_final = False
        error_occurred = False
        error_payload_for_logging = None
        result_segments = {}
        current_segment_index = 0

        try:
            async with session.ws_connect(service_url, headers=custom_headers) as websocket:
                _LOGGER.info(f"Connected to Volcengine ASR: {service_url} with connect_id: {self._connect_id}")
                payload_json_bytes = json.dumps(full_client_request_payload).encode("utf-8")
                msg_header = struct.pack(">BBBB", 0x11, 0x10, 0x10, 0x00)
                payload_size = struct.pack(">I", len(payload_json_bytes))
                await websocket.send_bytes(msg_header + payload_size + payload_json_bytes)
                _LOGGER.debug(f"Sent Full Client Request: {full_client_request_payload}")

                # Loop to send audio and receive intermediate results
                async for audio_chunk in stream:
                    if not audio_chunk or error_occurred:
                        continue
                    flags = 0b0000 # Not final chunk
                    msg_type_flags = (0b0010 << 4) | flags # Audio Frame
                    audio_header = struct.pack(">BBBB", 0x11, msg_type_flags, 0x00, 0x00)
                    audio_payload_size = struct.pack(">I", len(audio_chunk))
                    await websocket.send_bytes(audio_header + audio_payload_size + audio_chunk)
                    _LOGGER.debug(f"Sent audio chunk, size: {len(audio_chunk)}")

                    try:
                        ws_msg = await asyncio.wait_for(websocket.receive(), timeout=0.5) # Adjusted timeout
                        if ws_msg.type == aiohttp.WSMsgType.BINARY:
                            response_data = ws_msg.data
                            if not response_data or len(response_data) < 8:
                                _LOGGER.debug("ASR: Empty/incomplete binary msg (during send), skipping.")
                                continue
                            
                            resp_header_data = response_data[:4]
                            raw_payload_data = response_data[8:] # Assuming 4-byte size header after 4-byte msg header
                            processed_payload_data = self._preprocess_payload(raw_payload_data)
                            resp_msg_type = (resp_header_data[1] >> 4) & 0x0F

                            if resp_msg_type == 0b1001:  # Server ASR Result
                                if not processed_payload_data:
                                    _LOGGER.debug("ASR: Empty payload after preprocess (during send), skipping.")
                                    continue
                                try:
                                    decoded_payload = processed_payload_data.decode("utf-8")
                                    resp_json = json.loads(decoded_payload)
                                    _LOGGER.debug(f"ASR Response (during send): {resp_json}")

                                    msg_type = resp_json.get("type")
                                    msg_status = resp_json.get("header", {}).get("status", 0)

                                    if msg_type == "error" or (msg_status != 20000000 and msg_status != 0 and msg_type == "final"):
                                        _LOGGER.error(f"Volcengine ASR Error in payload (during send): {resp_json}")
                                        error_payload_for_logging = resp_json
                                        error_occurred = True; break

                                    result_data = resp_json.get("result")
                                    if isinstance(result_data, list):
                                        for res_item in result_data:
                                            if isinstance(res_item, dict):
                                                text = res_item.get("text", "").strip()
                                                if text and text not in final_text_set:
                                                    final_text_set.add(text)
                                                    result_segments[current_segment_index] = text
                                                    current_segment_index += 1
                                            elif isinstance(res_item, str) and res_item.strip() and res_item.strip() not in final_text_set:
                                                final_text_set.add(res_item.strip())
                                                result_segments[current_segment_index] = res_item.strip()
                                                current_segment_index += 1
                                    elif isinstance(result_data, dict):
                                        text = result_data.get("text", "").strip()
                                        if text and text not in final_text_set:
                                            final_text_set.add(text)
                                            result_segments[current_segment_index] = text
                                            current_segment_index += 1
                                    elif isinstance(result_data, str) and result_data.strip() and result_data.strip() not in final_text_set:
                                        final_text_set.add(result_data.strip())
                                        result_segments[current_segment_index] = result_data.strip()
                                        current_segment_index += 1
                                    
                                    if msg_type == "final":
                                        server_marked_final = True
                                        # Don't break, allow sending final empty chunk

                                except UnicodeDecodeError as ude_err:
                                    _LOGGER.warning(f"ASR: UnicodeDecodeError (during send): {ude_err}. Payload (hex): {processed_payload_data.hex()}")
                                except json.JSONDecodeError as json_err:
                                    _LOGGER.warning(f"ASR: JSONDecodeError (during send): {json_err}. Original (hex): {raw_payload_data.hex()}, Processed: {processed_payload_data.decode('utf-8', errors='ignore')}")
                                except AttributeError as attr_err:
                                    _LOGGER.error(f"ASR: AttributeError processing result (during send): {attr_err}. Response JSON: {resp_json}", exc_info=True)
                                    error_payload_for_logging = resp_json
                                    error_occurred = True; break
                            
                            elif resp_msg_type == 0b1111:  # Server Error Message
                                _LOGGER.error(f"Volcengine ASR WebSocket Error Message (during send): {processed_payload_data.decode('utf-8', errors='ignore')}")
                                error_payload_for_logging = processed_payload_data.decode('utf-8', errors='ignore')
                                error_occurred = True; break

                        elif ws_msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(f"aiohttp WS Error (during send): {websocket.exception()}")
                            error_occurred = True; break
                        elif ws_msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("aiohttp WS Closed by server (during send).")
                            error_occurred = True; break # Treat as error if closed during active send

                    except asyncio.TimeoutError:
                        _LOGGER.debug("ASR: No immediate response while sending audio, continuing.")
                    except Exception as e:
                        _LOGGER.error(f"ASR: Unexpected error processing response (during send): {e}", exc_info=True)
                        error_occurred = True; break
                
                # Send final empty audio chunk if no error occurred during streaming
                if not error_occurred:
                    _LOGGER.debug("Finished audio stream. Sending final empty chunk.")
                    flags = 0b0010  # Mark as final chunk
                    msg_type_flags = (0b0010 << 4) | flags
                    final_audio_header = struct.pack(">BBBB", 0x11, msg_type_flags, 0x00, 0x00)
                    final_audio_payload_size = struct.pack(">I", 0)
                    await websocket.send_bytes(final_audio_header + final_audio_payload_size)
                    _LOGGER.debug("Sent final empty audio chunk.")
                else:
                    _LOGGER.warning(f"Skipping final empty chunk due to earlier error. Error details: {error_payload_for_logging}")

                # Wait for final ASR responses
                while not server_marked_final and not error_occurred:
                    try:
                        ws_msg = await asyncio.wait_for(websocket.receive(), timeout=10.0) 
                        if ws_msg.type == aiohttp.WSMsgType.BINARY:
                            response_data = ws_msg.data
                            if not response_data or len(response_data) < 8:
                                _LOGGER.debug("ASR: Empty/incomplete binary msg (final wait), skipping.")
                                continue

                            resp_header_data = response_data[:4]
                            raw_payload_data = response_data[8:]
                            processed_payload_data = self._preprocess_payload(raw_payload_data)
                            resp_msg_type = (resp_header_data[1] >> 4) & 0x0F

                            if resp_msg_type == 0b1001:  # Server ASR Result
                                if not processed_payload_data:
                                    _LOGGER.debug("ASR: Empty payload after preprocess (final wait), skipping.")
                                    continue
                                try:
                                    decoded_payload = processed_payload_data.decode("utf-8")
                                    resp_json = json.loads(decoded_payload)
                                    _LOGGER.debug(f"ASR Response (final wait): {resp_json}")

                                    msg_type = resp_json.get("type")
                                    msg_status = resp_json.get("header", {}).get("status", 0)

                                    if msg_type == "error" or (msg_type == "final" and msg_status != 20000000 and msg_status != 0):
                                        _LOGGER.error(f"Volcengine ASR Error in payload (final wait): {resp_json}")
                                        error_payload_for_logging = resp_json
                                        error_occurred = True; break 
                                    
                                    result_data = resp_json.get("result")
                                    if isinstance(result_data, list):
                                        for res_item in result_data:
                                            if isinstance(res_item, dict):
                                                text = res_item.get("text", "").strip()
                                                if text and text not in final_text_set:
                                                    final_text_set.add(text)
                                                    result_segments[current_segment_index] = text
                                                    current_segment_index += 1
                                            elif isinstance(res_item, str) and res_item.strip() and res_item.strip() not in final_text_set:
                                                final_text_set.add(res_item.strip())
                                                result_segments[current_segment_index] = res_item.strip()
                                                current_segment_index += 1
                                    elif isinstance(result_data, dict):
                                        text = result_data.get("text", "").strip()
                                        if text and text not in final_text_set:
                                            final_text_set.add(text)
                                            result_segments[current_segment_index] = text
                                            current_segment_index += 1
                                    elif isinstance(result_data, str) and result_data.strip() and result_data.strip() not in final_text_set:
                                        final_text_set.add(result_data.strip())
                                        result_segments[current_segment_index] = result_data.strip()
                                        current_segment_index += 1

                                    if msg_type == "final":
                                        server_marked_final = True
                                        # If it's final and we got text, it's a success regardless of earlier minor issues
                                        if "".join(filter(None, result_segments.values())):
                                            error_occurred = False # Override minor errors if final text is present
                                        break # Got the definitive final message

                                except UnicodeDecodeError as ude_err:
                                    _LOGGER.warning(f"ASR: UnicodeDecodeError (final wait): {ude_err}. Payload (hex): {processed_payload_data.hex()}")
                                except json.JSONDecodeError as json_err:
                                    _LOGGER.warning(f"ASR: JSONDecodeError (final wait): {json_err}. Original (hex): {raw_payload_data.hex()}, Processed: {processed_payload_data.decode('utf-8', errors='ignore')}")
                                except AttributeError as attr_err:
                                    _LOGGER.error(f"ASR: AttributeError processing result (final wait): {attr_err}. Response JSON: {resp_json}", exc_info=True)
                                    error_payload_for_logging = resp_json
                                    error_occurred = True; break
                            
                            elif resp_msg_type == 0b1111:  # Server Error Message
                                _LOGGER.error(f"Volcengine ASR WebSocket Error Message (final wait): {processed_payload_data.decode('utf-8', errors='ignore')}")
                                error_payload_for_logging = processed_payload_data.decode('utf-8', errors='ignore')
                                error_occurred = True; break

                        elif ws_msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(f"aiohttp WS Error (final wait): {websocket.exception()}")
                            error_occurred = True; break
                        elif ws_msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("aiohttp WS Closed by server (final wait).")
                            break # Connection closed, proceed with what we have

                    except asyncio.TimeoutError:
                        _LOGGER.warning("ASR: Timeout waiting for final response from server.")
                        break # Assume no more messages are coming
                    except Exception as e:
                        _LOGGER.error(f"ASR: Unexpected error processing final response: {e}", exc_info=True)
                        error_occurred = True; break
                
                # 按索引顺序构建最终文本，保持识别片段的原始顺序
                final_text = ""
                if result_segments:
                    try:
                        final_text_ordered = " ".join([result_segments[i] for i in sorted(result_segments.keys())])
                        final_text = final_text_ordered.strip()
                    except Exception as e:
                        _LOGGER.error(f"Error constructing final text: {e}", exc_info=True)
                        # 回退方案：直接使用集合内容（可能顺序不正确，但总比没有结果好）
                        final_text = " ".join(final_text_set).strip()
                
                _LOGGER.info(f"Final recognized text: \"{final_text}\"")

                if final_text: # 如果我们有任何文本，则为成功
                    _LOGGER.info(f"ASR process finished with text. Error state: {error_occurred}, Server final: {server_marked_final}")
                    return SpeechResult(final_text, SpeechResultState.SUCCESS)
                elif server_marked_final and not error_occurred:
                    # 服务器标记了最终状态，但没有文本（可能是静音识别）
                    _LOGGER.info("ASR process ended: Server marked final with no text. Likely silence. Returning SUCCESS with no text.")
                    return SpeechResult("", SpeechResultState.SUCCESS)
                elif error_occurred: # 没有文本，发生了错误
                    _LOGGER.error(f"ASR process ended with an error and no recognized text. Details: {error_payload_for_logging}")
                    return SpeechResult(None, SpeechResultState.ERROR)
                else: # 没有文本，没有明确的错误（例如静音，或服务器在没有最终消息的情况下关闭）
                    _LOGGER.warning("ASR process ended with no recognized text and no explicit error. Returning ERROR state.")
                    return SpeechResult(None, SpeechResultState.ERROR)

        except aiohttp.ClientError as e:
            _LOGGER.error(f"aiohttp client connection error: {e}", exc_info=True)
            return SpeechResult(None, SpeechResultState.ERROR)
        except Exception as e:
            _LOGGER.error(f"An unexpected error occurred in Volcengine ASR processing: {e}", exc_info=True)
            return SpeechResult(None, SpeechResultState.ERROR)

