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
    
    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: asyncio.StreamReader # stream is actually an async_generator
    ) -> SpeechResult:
        """Process an audio stream to STT service."""
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
        final_text_parts = []
        server_marked_final = False 

        try:
            async with session.ws_connect(service_url, headers=custom_headers) as websocket:
                _LOGGER.info(f"Connected to Volcengine ASR via aiohttp: {service_url} with connect_id: {self._connect_id}")
                
                payload_json = json.dumps(full_client_request_payload).encode("utf-8")
                msg_header = struct.pack(">BBBB", 0x11, 0x10, 0x10, 0x00)
                payload_size = struct.pack(">I", len(payload_json))
                await websocket.send_bytes(msg_header + payload_size + payload_json)
                _LOGGER.debug(f"Sent Full Client Request: {full_client_request_payload}")

                async for audio_chunk in stream:
                    if not audio_chunk: 
                        continue
                    
                    flags = 0b0000 
                    msg_type_flags = (0b0010 << 4) | flags
                    audio_header = struct.pack(">BBBB", 0x11, msg_type_flags, 0x00, 0x00)
                    audio_payload_size = struct.pack(">I", len(audio_chunk))
                    
                    await websocket.send_bytes(audio_header + audio_payload_size + audio_chunk)
                    _LOGGER.debug(f"Sent audio chunk, size: {len(audio_chunk)}")

                    try:
                        ws_msg = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                        if ws_msg.type == aiohttp.WSMsgType.BINARY:
                            response_data = ws_msg.data
                            if not response_data or len(response_data) < 8:
                                _LOGGER.debug("Received empty or incomplete binary message from ASR, skipping.")
                                continue
                            resp_header_data = response_data[:4]
                            resp_payload_data = response_data[8:]
                            resp_msg_type = (resp_header_data[1] >> 4) & 0x0F
                            if resp_msg_type == 0b1001:
                                if not resp_payload_data:
                                    _LOGGER.debug("Received ASR message with empty payload, skipping JSON parse.")
                                    continue
                                try:
                                    decoded_payload = resp_payload_data.decode("utf-8")
                                    resp_payload_json = json.loads(decoded_payload)
                                    _LOGGER.debug(f"Received ASR response: {resp_payload_json}")
                                    if resp_payload_json.get("type") == "final" or resp_payload_json.get("type") == "utterance_end":
                                        for res_item in resp_payload_json.get("result", []):
                                            final_text_parts.append(res_item.get("text", ""))
                                        if resp_payload_json.get("type") == "final":
                                            server_marked_final = True
                                except UnicodeDecodeError as ude_err:
                                    _LOGGER.warning(f"UnicodeDecodeError during ASR response decoding (audio send): {ude_err}. Payload (hex): {resp_payload_data.hex()}")
                                except json.JSONDecodeError as json_err:
                                    _LOGGER.warning(f"JSONDecodeError during ASR response processing (audio send): {json_err}. Payload: {resp_payload_data.decode("utf-8", errors="ignore")}")
                            elif resp_msg_type == 0b1111:
                                _LOGGER.error(f"Volcengine ASR WebSocket Error Message: {resp_payload_data.decode("utf-8", errors="ignore")}")
                                return SpeechResult(None, SpeechResultState.ERROR)
                        elif ws_msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(f"aiohttp WebSocket connection error during receive: {websocket.exception()}")
                            return SpeechResult(None, SpeechResultState.ERROR)
                        elif ws_msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("aiohttp WebSocket connection closed by server during audio send.")
                            return SpeechResult(" ".join(filter(None, final_text_parts)) or None, SpeechResultState.ERROR if not server_marked_final else SpeechResultState.SUCCESS)
                    except asyncio.TimeoutError:
                        _LOGGER.debug("No immediate response from ASR, continuing to send audio.")
                    except Exception as e:
                        _LOGGER.error(f"Error processing ASR response during audio send: {e}", exc_info=True)
                
                _LOGGER.debug("Finished sending all audio chunks from stream. Sending final empty chunk.")
                flags = 0b0010 
                msg_type_flags = (0b0010 << 4) | flags
                final_audio_header = struct.pack(">BBBB", 0x11, msg_type_flags, 0x00, 0x00)
                final_audio_payload_size = struct.pack(">I", 0) 
                await websocket.send_bytes(final_audio_header + final_audio_payload_size)
                _LOGGER.debug("Sent final empty audio chunk.")

                while not server_marked_final:
                    try:
                        ws_msg = await asyncio.wait_for(websocket.receive(), timeout=10.0)
                        if ws_msg.type == aiohttp.WSMsgType.BINARY:
                            response_data = ws_msg.data
                            if not response_data or len(response_data) < 8:
                                _LOGGER.debug("Received empty or incomplete binary message from ASR (final wait), skipping.")
                                continue
                            resp_header_data = response_data[:4]
                            resp_payload_data = response_data[8:]
                            resp_msg_type = (resp_header_data[1] >> 4) & 0x0F
                            if resp_msg_type == 0b1001:
                                if not resp_payload_data:
                                    _LOGGER.debug("Received ASR message with empty payload (final wait), skipping JSON parse.")
                                    continue
                                try:
                                    decoded_payload = resp_payload_data.decode("utf-8")
                                    resp_payload_json = json.loads(decoded_payload)
                                    _LOGGER.debug(f"Received ASR response (final wait): {resp_payload_json}")
                                    if resp_payload_json.get("type") == "final" or resp_payload_json.get("type") == "utterance_end":
                                        for res_item in resp_payload_json.get("result", []):
                                            final_text_parts.append(res_item.get("text", ""))
                                        if resp_payload_json.get("type") == "final":
                                            server_marked_final = True
                                            break 
                                    elif resp_payload_json.get("header", {}).get("status") != 20000000:
                                        _LOGGER.error(f"Volcengine ASR Error in payload (final wait): {resp_payload_json}")
                                        return SpeechResult(None, SpeechResultState.ERROR)
                                except UnicodeDecodeError as ude_err:
                                    _LOGGER.warning(f"UnicodeDecodeError during ASR response decoding (final wait): {ude_err}. Payload (hex): {resp_payload_data.hex()}")
                                except json.JSONDecodeError as json_err:
                                    _LOGGER.warning(f"JSONDecodeError during ASR response processing (final wait): {json_err}. Payload: {resp_payload_data.decode("utf-8", errors="ignore")}")
                            elif resp_msg_type == 0b1111:
                                _LOGGER.error(f"Volcengine ASR WebSocket Error Message (final wait): {resp_payload_data.decode("utf-8", errors="ignore")}")
                                return SpeechResult(None, SpeechResultState.ERROR)
                        elif ws_msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(f"aiohttp WebSocket connection error (final wait): {websocket.exception()}")
                            return SpeechResult(None, SpeechResultState.ERROR)
                        elif ws_msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.info("aiohttp WebSocket connection closed by server (final wait).")
                            break 
                    except asyncio.TimeoutError:
                        _LOGGER.error("Timeout waiting for final ASR response after sending all audio.")
                        break 
                    except Exception as e:
                        _LOGGER.error(f"Error processing final ASR response: {e}", exc_info=True)
                        return SpeechResult(None, SpeechResultState.ERROR)
                
                final_text = " ".join(filter(None, final_text_parts))
                _LOGGER.info(f"Final recognized text: {final_text}")
                if final_text or server_marked_final: 
                    return SpeechResult(final_text if final_text else None, SpeechResultState.SUCCESS)
                else:
                    _LOGGER.warning("ASR result is empty and not marked as final by server.")
                    return SpeechResult(None, SpeechResultState.ERROR) 
        
        except aiohttp.ClientError as e:
            _LOGGER.error(f"aiohttp client connection error: {e}", exc_info=True)
            return SpeechResult(None, SpeechResultState.ERROR)
        except Exception as e:
            _LOGGER.error(f"An unexpected error occurred in Volcengine ASR (aiohttp): {e}", exc_info=True)
            return SpeechResult(None, SpeechResultState.ERROR)

