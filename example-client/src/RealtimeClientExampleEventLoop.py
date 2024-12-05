# Copyright (c) 2024, Oracle and/or its affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/

import asyncio
import pyaudio
import oci
from oci.config import from_file
from oci.auth.signers.security_token_signer import SecurityTokenSigner

import argparse

from oci_ai_speech_realtime import (
    RealtimeSpeechClient,
    RealtimeSpeechClientListener
)

from oci.ai_speech.models import RealtimeParameters

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Create a logger for this module
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()
# Create a FIFO queue
queue = asyncio.Queue()

# Set audio parameters
SAMPLE_RATE = 16000 #Can be 8000 as well
FORMAT = pyaudio.paInt16
CHANNELS = 1
BUFFER_DURATION_MS = 96

# Calculate the number of frames per buffer
FRAMES_PER_BUFFER = int(SAMPLE_RATE * BUFFER_DURATION_MS / 1000)

# Set realtime/customization parameters

DOMAIN = "GENERIC" #Can also be "MEDICAL"
LANGUAGE_CODE = "en-US" #Choose according to your preference

#Duration until which the session is active. To run forever, set this to -1
SESSION_DURATION = 100

#Used for authentication purposes
def authenticator():
    config = from_file("~/.oci/config", "DEFAULT")
    with open(config["security_token_file"], "r") as f:
        token = f.readline()

    private_key = oci.signer.load_private_key_from_file(config["key_file"])

    auth = SecurityTokenSigner(token=token, private_key=private_key)
    return auth


def audio_callback(in_data, frame_count, time_info, status):
    # This function will be called by PyAudio when there's new audio data
    queue.put_nowait(in_data)
    return (None, pyaudio.paContinue)


# Create a PyAudio object
p = pyaudio.PyAudio()

# Open the stream
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=SAMPLE_RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER,
    stream_callback=audio_callback,
)

stream.start_stream()
config = from_file()


async def send_audio(client):
    i = 0
    # loop = asyncio.get_running_loop()
    while not client.close_flag:
        data = await queue.get()

        # Send it over the websocket
        await client.send_data(data)
        i += 1

    if stream.is_active():
        stream.close()

def get_realtime_parameters(customizations, compartment_id):
    realtime_speech_parameters: RealtimeParameters = RealtimeParameters()
    realtime_speech_parameters.language_code = "en-US"
    realtime_speech_parameters.model_domain = (
        realtime_speech_parameters.MODEL_DOMAIN_GENERIC
    )
    realtime_speech_parameters.partial_silence_threshold_in_ms = 0
    realtime_speech_parameters.final_silence_threshold_in_ms = 2000
    
    realtime_speech_parameters.encoding=f"audio/raw;rate={SAMPLE_RATE}" #Default=16000 Hz
    realtime_speech_parameters.should_ignore_invalid_customizations = False
    realtime_speech_parameters.stabilize_partial_results = (
        realtime_speech_parameters.STABILIZE_PARTIAL_RESULTS_NONE
    )

    #Skip this if you don't want to use customizations    
    for customization_id in customizations:
        realtime_speech_parameters.customizations = [
            {
                "compartmentId": compartment_id,
                "customizationId": customization_id,
            }
        ]
    
    return realtime_speech_parameters

class MyListener(RealtimeSpeechClientListener):
    def on_result(self, result):
        if result["transcriptions"][0]["isFinal"]:
            logger.info(
                f"Received final results: {result['transcriptions'][0]['transcription']}"
            )
        else:
            logger.info(
                f"Received partial results: {result['transcriptions'][0]['transcription']}"
            )

    def on_ack_message(self, ackmessage):
        return super().on_ack_message(ackmessage)

    def on_connect(self):
        return super().on_connect()

    def on_connect_message(self, connectmessage):
        return super().on_connect_message(connectmessage)

    def on_network_event(self, ackmessage):
        return super().on_network_event(ackmessage)

    def on_error(self, error_message):
        return super().on_error(error_message)
    
    def on_close(self, error_code, error_message):
        print(f"Closed due to error code {error_code}:{error_message}")

async def start_realtime_session(customizations = [], compartment_id = None, region = None):
    def message_callback(message):
        logger.info(f"Received message: {message}")

    #See this for more info: https://docs.oracle.com/en-us/iaas/api/#/en/speech/20220101/datatypes/RealtimeParameters
    
    realtime_speech_parameters = get_realtime_parameters(customizations = customizations, compartment_id=compartment_id)

    realtime_speech_url = f"wss://realtime.aiservice.{region}.oci.oraclecloud.com"
    client = RealtimeSpeechClient(
        config=config,
        realtime_speech_parameters=realtime_speech_parameters,
        listener=MyListener(),
        service_endpoint=realtime_speech_url,
        signer=authenticator(),
        compartment_id=compartment_id,
    )

    #example close condition
    async def close_after_a_while(realtime_speech_client, session_duration_seconds):
        if session_duration_seconds >= 0:
            await asyncio.sleep(session_duration_seconds)
            realtime_speech_client.close()
    
    #asyncio.create_task(send_audio(client))
    
    #asyncio.create_task(close_after_a_while(client, SESSION_DURATION))

    loop = asyncio.get_running_loop()
    loop.create_task(send_audio(client))
    loop.create_task(close_after_a_while(client, SESSION_DURATION))
    
    await client.connect()

    """
    Optionally request the final result on demand. Do this before closure.
    The below code snippet will request a final result.
    
    await client.request_final_result()
    
    """

    logger.info("Closed now")

if __name__ == "__main__":
    # Populate with appropriate customization IDs
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '-c', '--compartment-id',
        required=True,
        help='The compartment ID (mandatory)'
    )
    parser.add_argument(
        '-r', '--region',
        default='us-ashburn-1',
        help='The region (default: us-ashburn-1)'
    )
    
    args = parser.parse_args()

    customization_ids = []

    loop.run_until_complete(start_realtime_session(customizations = customization_ids, compartment_id = args.compartment_id, region = args.region))