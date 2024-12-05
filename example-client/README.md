# Python example client for AI Speech Realtime SDK

## Requirements 
1. Use OCI SDK Version - `2.130.0` or later \
   https://pypi.org/project/oci/2.130.0/
## Setup

Do the following from the current directory

1. Install Requirements →
   ```bash
   pip install -r example-requirements.txt
   ```

   If you want to install the SDK from source instead of PyPi, install it as follows:
   ```bash
   pip install ../ai-speech-realtime-sdk-python
   ```
2. Make sure you're using the right compartment, region, etc in `RealtimeClient.py`

## Usage

Run Python File →
   ```bash
   python3 src/RealtimeClient.py -c <compartment-id> -r <region>
   ```
In RealtimeClient.py,
   We have parameters like SAMPLE_RATE, FORMAT, CHANNELS, BUFFER_DURATION_MS. These define audio parameters. For now, we only support mono (single-channel) audio.  

   The **authenticator()** method is used to create the signer object used for authentication. You can choose a different method (config file, instance principals, etc) as per your use case.

   The **get_realtime_parameters(...)** method defines the realtime service parameters. See this for reference and feel free to tweak the defaults provided in this example. See this for more info: https://docs.oracle.com/en-us/iaas/api/#/en/speech/20220101/datatypes/RealtimeParameters

   Note that the example is programmed to automatically close after a certain duration, but you can choose any exit condition according to your preference.

   



