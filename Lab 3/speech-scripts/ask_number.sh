#!/usr/bin/env bash
python3 -m piper --model en_US-lessac-medium --data-dir ../voices --output-file ask.wav -- "What is your zip code?"
aplay ask.wav

echo "Recording..."
arecord -D plughw:2,0 -d 5 -f S16_LE -r 16000 -c 1 answer.wav

python transcribe.py answer.wav --model base.en
