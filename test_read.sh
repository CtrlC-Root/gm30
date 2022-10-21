#!/bin/bash

set -e

export PYTHONUNBUFFERED="1"

#gm30 mr -f data.bin | tee output.txt
gm30 read -c config.bin | tee output.txt
sha256sum output.txt *.bin | tee hashes.txt
