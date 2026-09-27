#!/usr/bin/env python3

"""
Lab 3 Part B
Ask the user a numerical question, record their spoken response,
and transcribe the response using Faster Whisper.
"""

import subprocess
from pathlib import Path

from faster_whisper import WhisperModel


# Save the recorded response in the same folder as this script.
OUTPUT_FILE = Path(__file__).resolve().parent / "number_response.wav"

# Question spoken by the Raspberry Pi.
QUESTION = "Jonathan, what is your ZIP code?"


def speak_question():
    """Use Piper to verbally ask the numerical-input question."""
    script_dir = Path(__file__).resolve().parent
    voices_dir = script_dir.parent / "voices"

    piper = subprocess.Popen(
        [
            "python3", "-m", "piper",
            "--model", "en_US-lessac-medium",
            "--data-dir", str(voices_dir),
            "--output-raw",
            "--", QUESTION,
        ],
        stdout=subprocess.PIPE,
    )

    # Stream Piper's generated speech directly to the USB speaker.
    subprocess.run(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
        stdin=piper.stdout,
        check=True,
    )

    piper.wait()


def record_answer():
    """Record five seconds of the user's spoken numerical response."""
    print("\nRecording your answer for 5 seconds...")

    subprocess.run(
        [
            "arecord",
            "-d", "5",
            "-f", "cd",
            "-c", "1",
            "-r", "16000",
            str(OUTPUT_FILE),
        ],
        check=True,
    )

    print(f"Recording saved to {OUTPUT_FILE.name}.")


def transcribe_answer():
    """Transcribe the recorded response using the tiny English Whisper model."""
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(OUTPUT_FILE), beam_size=1)

    text = " ".join(segment.text.strip() for segment in segments)

    print("\nThe Pi heard:")
    print(text)


def main():
    speak_question()
    record_answer()
    transcribe_answer()


if __name__ == "__main__":
    main()
