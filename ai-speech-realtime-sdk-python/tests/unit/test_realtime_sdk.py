# Copyright (c) 2024, Oracle and/or its affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/

import unittest
from unittest.mock import patch, AsyncMock, Mock, MagicMock
from oci.ai_speech.models import RealtimeMessageAckAudio, RealtimeParameters, RealtimeMessage
from oci_ai_speech_realtime import RealtimeSpeechClient, RealtimeSpeechClientListener
import asyncio
import pytest

from websockets.exceptions import ConnectionClosed

import json

from oci.signer import Signer, _PatchedHeaderSigner
import oci, websockets
import json

class TestRealtimeSpeechClient:
    
    @pytest.mark.asyncio
    async def test_connect(self):
        # Mock setup
        with patch("websockets.connect", new_callable=Mock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws
            mock_ws.__aenter__.return_value = mock_ws

            with patch.object(RealtimeSpeechClient, "_send_credentials", new_callable=AsyncMock) as mock_send_credentials, \
                 patch.object(RealtimeSpeechClient, "_handle_messages", new_callable=AsyncMock) as mock_handle_messages, \
                 patch('oci.util.get_signer_from_authentication_type') as mock_get_signer_from_authentication_type, \
                 patch('oci_ai_speech_realtime.ai_service_speech_realtime_client.validate_config') as mock_validate_config:
                
                # Configure test inputs and instance creation
                config = {"user": "test_user", "tenancy": "test_tenancy", "fingerprint": "test_fingerprint", "authentication_type": "test"}
                realtime_parameters = RealtimeParameters()
                mock_listener = Mock(spec=RealtimeSpeechClientListener)
                mock_listener.on_connect = Mock()
                custom_signer = Mock(spec=Signer)
                basic_signer_mock = Mock(spec=_PatchedHeaderSigner)
                custom_signer._basic_signer = basic_signer_mock

                # Configure return values
                basic_signer_mock.sign.return_value = {'Authorization': 'Bearer custom_token'}
                mock_validate_config.return_value = None
                mock_get_signer_from_authentication_type.return_value = custom_signer

                # Initialize instance and call the async method
                client = RealtimeSpeechClient(
                    config=config,
                    listener=mock_listener,
                    realtime_speech_parameters=realtime_parameters,
                    service_endpoint="wss://service-endpoint.com",
                    signer=custom_signer
                )
                
                await client.connect()

                # Assert calls
                mock_send_credentials.assert_called_once_with(mock_ws)
                mock_handle_messages.assert_called_once_with(mock_ws)
    

    @pytest.mark.asyncio
    @patch('urllib.parse.urlparse')
    @patch('oci.util.get_signer_from_authentication_type')
    @patch('oci_ai_speech_realtime.ai_service_speech_realtime_client.validate_config')
    async def test_send_credentials(self, mock_urlparse, mock_get_signer_from_authentication_type, mock_validate_config):
        # Mock the connection and the signing process
        mock_signer_instance = Mock()
        mock_basic_signer = Mock()

        mock_signer_instance._basic_signer = mock_basic_signer
        mock_basic_signer.sign.return_value = {'Authorization': 'Bearer test_token'}
        mock_get_signer_from_authentication_type.return_value = mock_signer_instance
        
        
        # Attach the _basic_signer mock to the mock_signer_instance        
        signer = oci.util.get_signer_from_authentication_type("test-auth-type")
        
        mock_ws = AsyncMock()
        
        mock_validate_config.return_value = None

        # Initialize client
        config = {"user": "test_user", "tenancy": "test_tenancy", "fingerprint": "test_fingerprint"}
        client = RealtimeSpeechClient(config={"user": "test_user"}, signer=mock_signer_instance, service_endpoint = "wss://service-endpoint.com", compartment_id = "compartmentId")
        
        
        await client._send_credentials(mock_ws)

        
        mock_ws.send.assert_called_once()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["authenticationType"] == "CREDENTIALS"
        
        assert sent_data["headers"] == {'Authorization': 'Bearer test_token', 'uri': 'wss://service-endpoint.com/ws/transcribe/stream?isAckEnabled=false&encoding=audio/raw;rate=16000&shouldIgnoreInvalidCustomizations=false&partialSilenceThresholdInMs=0&finalSilenceThresholdInMs=2000&languageCode=en-US&modelDomain=GENERIC&stabilizePartialResults=NONE'}
        assert sent_data["compartmentId"] == "compartmentId"
        
        
    @pytest.mark.asyncio
    @patch('urllib.parse.urlparse')
    @patch('oci.util.get_signer_from_authentication_type')
    @patch('oci_ai_speech_realtime.ai_service_speech_realtime_client.validate_config')
    @patch.object(RealtimeSpeechClient, "_send_credentials", new_callable=AsyncMock)
    #@patch("asyncio.wait_for", new_callable=AsyncMock)
    async def test_handle_messages_and_close(self, mock_urlparse, mock_get_signer_from_authentication_type, mock_validate_config, mock_send_credentials):
        mock_ws = Mock()
        mock_ws_coroutine = AsyncMock()
        
        mock_async_result = json.dumps({"event": RealtimeMessage.EVENT_CONNECT})

        async def delayed_return():
            await asyncio.sleep(0.05)
            return mock_async_result
        
        #mock_ws_coroutine.return_value = mock_async_result
        
        mock_ws_coroutine.side_effect = delayed_return

        mock_ws.recv = mock_ws_coroutine

        #mock_ws_coroutine.assert_called_once_with(2,3)
        #mock_asyncio_wait_for.return_value = mock_ws_coroutine

        custom_signer = Mock(spec=Signer)
        config = {"user": "test_user", "tenancy": "test_tenancy", "fingerprint": "test_fingerprint", "authentication_type": "test"}

        realtime_parameters = RealtimeParameters()
        mock_listener = Mock(spec=RealtimeSpeechClientListener)

        client = RealtimeSpeechClient(
                    config=config,
                    listener=mock_listener,
                    realtime_speech_parameters=realtime_parameters,
                    service_endpoint="wss://service-endpoint.com",
                    signer=custom_signer
                )
        
        asyncio.create_task(client._handle_messages(mock_ws))

        #Close the client after 1 second
        await asyncio.sleep(1)
        client.close()


if __name__ == "__main__":
    unittest.main()