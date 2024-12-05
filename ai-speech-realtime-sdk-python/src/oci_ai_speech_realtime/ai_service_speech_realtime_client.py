# Copyright (c) 2024, Oracle and/or its affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/

import websockets
from oci.config import get_config_value_or_default, validate_config
from oci.signer import Signer
from oci.util import (
    get_signer_from_authentication_type,
    AUTHENTICATION_TYPE_FIELD_NAME,
)
from oci.ai_speech.models import (
    RealtimeParameters,
    CustomizationInference,
    RealtimeMessageAckAudio,
    RealtimeMessageResult,
    RealtimeMessageConnect,
    RealtimeMessageSendFinalResult,
    RealtimeMessageError,
    RealtimeMessage,
)

from urllib.parse import urlparse, quote
from email.utils import formatdate
import json
import asyncio
import abc

import logging
logger = logging.getLogger(__name__)

class RealtimeSpeechClientListener(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "on_result")
            and callable(subclass.on_result)
            and hasattr(subclass, "on_error")
            and callable(subclass.on_error)
            and hasattr(subclass, "on_connect_message")
            and callable(subclass.on_connect_message)
            and hasattr(subclass, "on_ack_message")
            and callable(subclass.on_ack_message)
            and hasattr(subclass, "on_connect")
            and callable(subclass.on_connect)
            and hasattr(subclass, "on_network_event")
            and callable(subclass.on_network_event)
        )

    @abc.abstractmethod
    def on_network_event(self, message):
        pass

    @abc.abstractmethod
    def on_ack_message(self, ackmessage: RealtimeMessageAckAudio):
        pass

    @abc.abstractmethod
    def on_connect_message(self, connectmessage: RealtimeMessageConnect):
        pass

    @abc.abstractmethod
    def on_connect(self):
        pass

    @abc.abstractmethod
    def on_error(self, error: RealtimeMessageError):
        pass

    @abc.abstractmethod
    def on_result(self, result: RealtimeMessageResult):
        pass

    def on_close(self, error_code: int, error_message: str):
        #This is intended as a callback for you to do custom logging/resource cleanups, etc
        pass


class RealtimeSpeechClient:
    def __init__(
        self,
        config,
        realtime_speech_parameters: RealtimeParameters = None,
        listener: RealtimeSpeechClientListener = None,
        service_endpoint=None,
        signer=None,
        compartment_id=None,
    ):
        self._validate_signer_and_endpoints(
            config=config, signer=signer, service_endpoint=service_endpoint
        )

        if realtime_speech_parameters is None:
            realtime_speech_parameters = RealtimeParameters()
            realtime_speech_parameters.customizations: CustomizationInference = []
            realtime_speech_parameters.encoding = "audio/raw;rate=16000"
            realtime_speech_parameters.final_silence_threshold_in_ms = 2000
            realtime_speech_parameters.partial_silence_threshold_in_ms = 0
            realtime_speech_parameters.is_ack_enabled = False
            realtime_speech_parameters.stabilize_partial_results = (
                realtime_speech_parameters.STABILIZE_PARTIAL_RESULTS_NONE
            )
            realtime_speech_parameters.language_code = "en-US"
            realtime_speech_parameters.model_domain = (
                RealtimeParameters.MODEL_DOMAIN_GENERIC
            )
            realtime_speech_parameters.should_ignore_invalid_customizations = False

        self.realtime_speech_parameters = realtime_speech_parameters

        # Function to handle incoming messages, implemented by the user the way they want
        self.listener = listener

        # This object will be used by the user in the send_data method
        self.connection = None

        # full uri with path/query params
        self.uri = (
            self.service_endpoint
            + f"{ self._parse_parameters(realtime_speech_parameters)}"
        )

        # compartmentId used for authentication
        self.compartment_id = compartment_id

        # Set this flag to close the websocket connection
        self.close_flag = False

    async def connect(self):
        logger.info(f"Connecting to: {self.uri}")
        async with websockets.connect(self.uri, ping_interval = None) as ws:
            self.connection = ws
            logger.info("Opened")
            self.listener.on_connect()
            await self._send_credentials(ws)
            await self._handle_messages(ws)

    async def _send_credentials(self, ws):
        parsed_url = urlparse(self.uri)
        headers = {"date": formatdate(usegmt=True), "host": parsed_url.hostname}

        headers = self.signer._basic_signer.sign(
            headers=headers,
            host=parsed_url.hostname,
            path=f"{parsed_url.path}?{parsed_url.query}",
            method="GET",
        )
        headers["uri"] = self.uri
        authentication_message_dict = {
            "authenticationType": "CREDENTIALS",
            "headers": headers,
            "compartmentId": self.compartment_id,
        }

        await ws.send(json.dumps(authentication_message_dict))

    async def send_data(self, data):
        if not self.connection is None:
            await self.connection.send(data)

    async def request_final_result(self):
        if not self.connection is None:
            request_message = {"event": RealtimeMessageSendFinalResult.EVENT_SEND_FINAL_RESULT}
            await self.connection.send(json.dumps(request_message))

    def on_close(self, error_code, error_message):
        logger.error(f"Connection with server closed, error code: {error_code} and reason: {error_message}")
        #Allow the clients to implement their own closing logic (logging, resource cleanup, etc)
        self.listener.on_close(error_code, error_message)
        self.close_flag = True
        self.connection = None
    
    async def _handle_messages(self, ws):
        while not self.close_flag:
            try:
                message = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.1))
                if self.listener:
                    if message["event"] == RealtimeMessage.EVENT_RESULT:
                        self.listener.on_result(message)
                    if message["event"] == RealtimeMessage.EVENT_ACKAUDIO:
                        self.listener.on_ack_message(message)
                    if message["event"] == RealtimeMessage.EVENT_CONNECT:
                        self.listener.on_connect_message(message)
                    if message["event"] == RealtimeMessage.EVENT_ERROR:
                        self.listener.on_error(message)

            except asyncio.TimeoutError:
                pass
            except websockets.exceptions.ConnectionClosed as e:
                self.on_close(e.code, e.reason)

    def close(self):
        logger.info("Client has initiated closure")
        self.listener.on_close(1000, "Closure Initiated by Client")
        self.close_flag = True
        self.connection = None

    def _parse_parameters(self, params: RealtimeParameters):
        parameterString = "/ws/transcribe/stream?"
        if params.is_ack_enabled is not None:
            parameterString += (
                "isAckEnabled="
                + ("true" if params.is_ack_enabled is True else "false")
                + "&"
            )
        
        if params.encoding is not None:
            parameterString += (
                "encoding="
                + params.encoding
                + "&"
            )

        if params.should_ignore_invalid_customizations is not None:
            parameterString += (
                "shouldIgnoreInvalidCustomizations="
                + (
                    "true"
                    if params.should_ignore_invalid_customizations is True
                    else "false"
                )
                + "&"
            )
        if params.partial_silence_threshold_in_ms is not None:
            parameterString += (
                "partialSilenceThresholdInMs="
                + str(params.partial_silence_threshold_in_ms)
                + "&"
            )
        if params.final_silence_threshold_in_ms is not None:
            parameterString += (
                "finalSilenceThresholdInMs="
                + str(params.final_silence_threshold_in_ms)
                + "&"
            )
        if params.language_code is not None:
            parameterString += "languageCode=" + params.language_code + "&"
        if params.model_domain is not None:
            parameterString += "modelDomain=" + params.model_domain + "&"
        if params.stabilize_partial_results is not None:
            parameterString += (
                "stabilizePartialResults=" + params.stabilize_partial_results + "&"
            )
        if params.customizations is not None and len(params.customizations) > 0:
            parameterString += "customizations=" + quote(
                json.dumps(params.customizations)
            )
        # if params.freeform_tags is not None and len(params.freeform_tags) > 0:
        #     parameterString += "freeFormTags=" + quote(json.dumps(params.freeform_tags))
        if parameterString[-1] == "&":
            parameterString = parameterString[:-1]
        return parameterString

    def _get_service_endpoint(self, config):
        # TBD
        pass

    def _validate_signer_and_endpoints(self, config, signer, service_endpoint):
        validate_config(config, signer=signer)
        if not signer is None:
            self.signer = signer

        elif AUTHENTICATION_TYPE_FIELD_NAME in config:
            self.signer = get_signer_from_authentication_type(config)

        else:
            self.signer = Signer(
                tenancy=config["tenancy"],
                user=config["user"],
                fingerprint=config["fingerprint"],
                private_key_file_location=config.get("key_file"),
                pass_phrase=get_config_value_or_default(config, "pass_phrase"),
                private_key_content=config.get("key_content"),
            )

        if not service_endpoint is None:
            self.service_endpoint = service_endpoint
        else:
            self.service_endpoint = self._get_service_endpoint(config)