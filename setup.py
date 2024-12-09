# coding: utf-8

# Copyright (c) 2024, Oracle and/or its affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/

import os
from setuptools import setup, find_packages

NAME = "oci-ai-speech-realtime"
__version__ = os.environ.get("PKG_VERSION", "0.0.1")
VERSION = __version__.replace("-", "+", 1).replace("-", "", 1)

requires = [
    "oci>=2.130.0",
    'websockets>=11.0.3'
]

setup(
    name=NAME,
    url="https://docs.oracle.com/en-us/iaas/tools/python/latest/index.html",
    version=VERSION,
    description="Oracle Cloud Infrastructure Python SDK for Realtime Speech Service",
    author="Oracle",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(where="ai-speech-realtime-sdk-python/src"),
    package_dir={"": "ai-speech-realtime-sdk-python/src"},
    include_package_data=True,
    install_requires=requires,
    extras_require={"dev": ["pip-tools", "build", "twine"]},
    license="Universal Permissive License 1.0",
    license_files=["LICENSE.txt", "THIRD_PARTY_LICENSES.txt"],
    
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Universal Permissive License (UPL)",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]
)
