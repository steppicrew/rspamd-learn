#!/bin/bash

cwd=$(realpath "$(dirname "$0")")

cd "$cwd"

python3 -m venv .venv
source .venv/bin/activate

pip3 install -r requirements.txt

python3 -u rspamd_learn.py

