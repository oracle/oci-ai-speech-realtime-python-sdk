# DEVELOPMENT

The target audience for this README is developers wanting to contribute to the OCI Realtime Speech Python SDK. If you simply want to use the SDK in your programs, refer to the top-level README, along with the example in this repository.

## Getting Started and Running Tests

Once you've cloned this repository, you need to install some dependencies to be able to build/test the code. Do the following:

```bash
pip install -r dev-requirements.txt
```
Feel free to alter the pytest and pytest-asyncio versions according to your preference.

Once you've done that, you need point the PYTHONPATH to the source code location. You can do that by:

```bash
export PYTHONPATH=<repository-root>/ai-speech-realtime-sdk-python/src
```

You should be able to run tests by doing the following:

```bash
python -m pytest -v
```

## Creating Binary Distributions

You can create binary distributions by running the following command in the content root. The distribution files will appear in the `dist/` directory.

```bash
python -m build
```

You should now be able to see both the binary (wheel) and source distributions in the `dist/` directory.