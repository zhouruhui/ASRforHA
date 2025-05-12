"""Support for Volcengine ASR speech-to-text service."""
import asyncio
import logging
import json
import uuid
import websockets
import struct

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechToTextEntity,
)
# Import SpeechMetadata, SpeechResult, SpeechResultState from the new location
from homeassistant.components.stt.models import (
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

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
        self._name = "Volcengine ASR"
        self._connect_id = str(uuid.uuid4())

    @property
    def name(self) -> str:
        """Return the name of the STT engine."""
        return self._name

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return [self._config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported formats."""
        return [AudioFormats.PCM]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bitrates."""
        return [AudioBitRates.BITRATE_16KHZ_16BIT_MONO]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported samplerates."""
        return [AudioSampleRates.SR_16KHZ]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.MONO]
    
    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: asyncio.StreamReader
    ) -> SpeechResult:
        """Process an audio stream to STT service."""
        _LOGGER.debug(f"Processing audio stream with metadata: {metadata}")
        
        app_id = self._config[CONF_APP_ID]
        access_token = self._config[CONF_ACCESS_TOKEN]
        resource_id = self._config[CONF_RESOURCE_ID]
        service_url = self._config.get(CONF_SERVICE_URL, DEFAULT_SERVICE_URL)
        self._connect_id = str(uuid.uuid4()) 

        headers = {
            "X-Api-App-Key": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Connect-Id": self._connect_id,
        }

        audio_params = {
            "format": self._config.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
            "rate": self._config.get(CONF_AUDIO_RATE, DEFAULT_AUDIO_RATE),
            "bits": self._config.get(CONF_AUDIO_BITS, DEFAULT_AUDIO_BITS),
            "channel": self._config.get(CONF_AUDIO_CHANNEL, DEFAULT_AUDIO_CHANNEL),
            "codec": "raw", 
        }
        if metadata.format != AudioFormats.PCM or metadata.codec != AudioCodecs.PCM:
            _LOGGER.error(f"Unsupported audio format/codec: {metadata.format}/{metadata.codec}")
            return SpeechResult(None, SpeechResultState.ERROR)
        
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
            "audio": audio_params,
            "request": request_params,
        }

        try:
            async with websockets.connect(service_url, extra_headers=headers) as websocket:
                _LOGGER.info(f"Connected to Volcengine ASR: {service_url} with connect_id: {self._connect_id}")
                
                payload_json = json.dumps(full_client_request_payload).encode("utf-8")
                msg_header = struct.pack(">BBBB", 0x11, 0x10, 0x10, 0x00)
                payload_size = struct.pack(">I", len(payload_json))
                await websocket.send(msg_header + payload_size + payload_json)
                _LOGGER.debug(f"Sent Full Client Request: {full_client_request_payload}")

                chunk_size = audio_params["rate"] * audio_params["bits"] // 8 * audio_params["channel"] * 200 // 1000
                is_final_chunk = False
                final_text_parts = []

                while not is_final_chunk:
                    audio_chunk = await stream.read(chunk_size)
                    if not audio_chunk:
                        is_final_chunk = True
                    
                    flags = 0b0010 if is_final_chunk else 0b0000
                    msg_type_flags = (0b0010 << 4) | flags
                    audio_header = struct.pack(">BBBB", 0x11, msg_type_flags, 0x00, 0x00)
                    audio_payload_size = struct.pack(">I", len(audio_chunk))
                    
                    await websocket.send(audio_header + audio_payload_size + audio_chunk)
                    _LOGGER.debug(f"Sent audio chunk, size: {len(audio_chunk)}, final: {is_final_chunk}")

                    try:
                        response_data = await asyncio.wait_for(websocket.recv(), timeout=10.0) 
                        resp_header_data = response_data[:4]
                        resp_payload_data = response_data[8:]
                        resp_msg_type = (resp_header_data[1] >> 4) & 0x0F

                        if resp_msg_type == 0b1001: 
                            resp_payload_json = json.loads(resp_payload_data.decode("utf-8"))
                            _LOGGER.debug(f"Received ASR response: {resp_payload_json}")
                            if resp_payload_json.get("type") == "final" or resp_payload_json.get("type") == "utterance_end":
                                for res_item in resp_payload_json.get("result", []):
                                    final_text_parts.append(res_item.get("text", ""))
                                if resp_payload_json.get("type") == "final":
                                    is_final_chunk = True 
                                    break 
                            elif resp_payload_json.get("header", {}).get("status") != 20000000:
                                _LOGGER.error(f"Volcengine ASR Error in payload: {resp_payload_json}")
                                return SpeechResult(None, SpeechResultState.ERROR)
                        elif resp_msg_type == 0b1111: 
                            _LOGGER.error(f"Volcengine ASR WebSocket Error Message: {resp_payload_data.decode("utf-8", errors="ignore")}")
                            return SpeechResult(None, SpeechResultState.ERROR)
                        else:
                            _LOGGER.warning(f"Received unexpected message type: {resp_msg_type}")

                    except asyncio.TimeoutError:
                        _LOGGER.warning("Timeout waiting for ASR response. Continuing to send audio if not final.")
                        if is_final_chunk:
                            _LOGGER.error("Timeout waiting for final ASR response after sending last audio chunk.")
                            return SpeechResult(None, SpeechResultState.ERROR)
                    except websockets.exceptions.ConnectionClosed:
                        _LOGGER.error("WebSocket connection closed unexpectedly by server.")
                        return SpeechResult(None, SpeechResultState.ERROR)
                    except Exception as e:
                        _LOGGER.error(f"Error processing ASR response: {e}")
                        return SpeechResult(None, SpeechResultState.ERROR)
                
                final_text = " ".join(filter(None, final_text_parts))
                _LOGGER.info(f"Final recognized text: {final_text}")
                if final_text:
                    return SpeechResult(final_text, SpeechResultState.SUCCESS)
                else:
                    # If final_text is empty but no specific error occurred before, 
                    # it might be a valid empty transcription or an unhandled server response.
                    _LOGGER.warning("ASR result is empty.")
                    return SpeechResult(None, SpeechResultState.SUCCESS) # Or .ERROR depending on desired behavior for empty result

        except websockets.exceptions.InvalidURI:
            _LOGGER.error(f"Invalid WebSocket URI: {service_url}")
            return SpeechResult(None, SpeechResultState.ERROR)
        except websockets.exceptions.WebSocketException as e:
            _LOGGER.error(f"WebSocket connection error: {e}")
            return SpeechResult(None, SpeechResultState.ERROR)
        except Exception as e:
            _LOGGER.error(f"An unexpected error occurred in Volcengine ASR: {e}", exc_info=True)
            return SpeechResult(None, SpeechResultState.ERROR)

