#!/usr/bin/env python3
"""
VoiceFit Wizard-of-Oz prototype.

Interaction loop:
1. Participant presses the rotary encoder button.
2. VoiceFit listens until the participant finishes speaking.
3. Whisper transcribes the participant.
4. The Wizard selects VoiceFit's response.
5. The microphone closes before Piper speaks.
6. VoiceFit waits for the next encoder press.
"""

import argparse
import sys
import time
from pathlib import Path

import board
import numpy as np
import sherpa_onnx
import sounddevice as sd
from adafruit_seesaw import seesaw
from faster_whisper import WhisperModel
from piper import PiperVoice


# ---------------------------------------------------------------------------
# Paths and audio settings
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16000

LAB_DIR = Path(__file__).resolve().parent.parent
DEFAULT_VAD = LAB_DIR / "models" / "silero_vad.onnx"
DEFAULT_VOICE = LAB_DIR / "voices" / "en_US-lessac-medium.onnx"


# ---------------------------------------------------------------------------
# Rotary encoder button
# ---------------------------------------------------------------------------

i2c = board.I2C()
ss = seesaw.Seesaw(i2c, addr=0x36)

BUTTON_PIN = 24
ss.pin_mode(BUTTON_PIN, ss.INPUT_PULLUP)


def wait_for_button():
    """Wait until the participant presses and releases the encoder button."""
    print("\nPress the encoder when you're ready to speak.")

    # Wait for button press
    while ss.digital_read(BUTTON_PIN):
        time.sleep(0.01)

    # Wait for button release
    while not ss.digital_read(BUTTON_PIN):
        time.sleep(0.01)

    print("Listening...")


# ---------------------------------------------------------------------------
# Wizard-of-Oz dialogue
# ---------------------------------------------------------------------------

def respond(heard: str) -> str:
    """Let the Wizard choose VoiceFit's response."""

    print("\nVOICEFIT WIZARD")
    print(f'Participant said: "{heard}"\n')

    print("1 - Ask what they want to train")
    print("2 - Ask how the set felt")
    print("3 - Keep the same weight")
    print("4 - Increase the weight")
    print("5 - Decrease the weight")
    print("6 - Start rest period")
    print("7 - Start next set")
    print("8 - Custom response")

    responses = {
        "1": "What would you like to train today?",
        "2": "How did that set feel? Easy, good, or hard?",
        "3": "Sounds good. Let's keep the same weight for your next set.",
        "4": "That sounded comfortable. Let's increase the weight slightly for your next set.",
        "5": "Let's lower the weight for your next set and focus on good form.",
        "6": "Great. Take a 90 second rest before your next set.",
        "7": "Ready when you are. Let's start your next set.",
    }

    while True:
        choice = input("\nWizard choice: ").strip()

        if choice in responses:
            return responses[choice]

        if choice == "8":
            custom = input("Custom response: ").strip()
            if custom:
                return custom

        print("Please choose 1 through 8.")


# ---------------------------------------------------------------------------
# Piper speech output
# ---------------------------------------------------------------------------

class Speaker:
    """Synthesizes speech with Piper and plays it through the default output."""

    def __init__(self, voice_path: Path) -> None:
        self.voice = PiperVoice.load(str(voice_path))

    def say(self, text: str) -> float:
        """Speak text and return time until the first audio is ready."""

        t0 = time.perf_counter()
        first_audio_at = None

        for chunk in self.voice.synthesize(text):
            audio = np.frombuffer(
                chunk.audio_int16_bytes,
                dtype=np.int16
            )

            if first_audio_at is None:
                first_audio_at = time.perf_counter() - t0

            sd.play(audio, samplerate=chunk.sample_rate)
            sd.wait()

        return first_audio_at or 0.0


# ---------------------------------------------------------------------------
# Main interaction
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--model",
        default="tiny.en",
        help="Whisper model size (default: tiny.en)"
    )

    parser.add_argument(
        "--vad-model",
        type=Path,
        default=DEFAULT_VAD
    )

    parser.add_argument(
        "--voice",
        type=Path,
        default=DEFAULT_VOICE
    )

    parser.add_argument(
        "--min-silence",
        type=float,
        default=0.4,
        help="Seconds of silence that end a participant turn"
    )

    args = parser.parse_args()

    # Make sure required model files exist
    for path, what in [
        (args.vad_model, "VAD model"),
        (args.voice, "Piper voice"),
    ]:
        if not path.is_file():
            sys.exit(
                f"{what} not found at {path}. "
                "Run ./setup.sh first."
            )

    print("Loading models...", flush=True)

    recognizer = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8"
    )

    speaker = Speaker(args.voice)

    # Configure voice activity detection
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(args.vad_model)
    config.silero_vad.min_silence_duration = args.min_silence
    config.sample_rate = SAMPLE_RATE

    vad = sherpa_onnx.VoiceActivityDetector(
        config,
        buffer_size_in_seconds=30
    )

    window = config.silero_vad.window_size
    samples_per_read = int(0.1 * SAMPLE_RATE)

    print(
        f"Ready. Push-to-talk enabled "
        f"(endpointing after {args.min_silence}s of silence)."
    )

    # -----------------------------------------------------------------------
    # Multi-turn interaction loop
    # -----------------------------------------------------------------------

    while True:
        # Participant explicitly starts each conversational turn.
        wait_for_button()

        buffer = np.empty(0, dtype=np.float32)
        heard = ""

        # IMPORTANT:
        # The microphone exists only inside this block.
        # It closes before VoiceFit speaks.
        with sd.InputStream(
            channels=1,
            dtype="float32",
            samplerate=SAMPLE_RATE
        ) as stream:

            while True:
                chunk, _ = stream.read(samples_per_read)
                buffer = np.concatenate(
                    [buffer, chunk.reshape(-1)]
                )

                # Feed audio to the voice activity detector.
                while len(buffer) > window:
                    vad.accept_waveform(buffer[:window])
                    buffer = buffer[window:]

                # VAD has detected a completed participant utterance.
                if not vad.empty():
                    utterance = np.array(
                        vad.front.samples,
                        dtype=np.float32
                    )

                    vad.pop()
                    turn_ended = time.perf_counter()

                    segments, _ = recognizer.transcribe(
                        utterance,
                        beam_size=1
                    )

                    heard = " ".join(
                        segment.text.strip()
                        for segment in segments
                    )

                    if heard:
                        asr_done = time.perf_counter()
                        break

        # We are OUTSIDE InputStream here.
        # Therefore the microphone is closed before Piper speaks.
        if not heard:
            print("No speech detected. Try again.")
            continue

        reply = respond(heard)

        print(f"\n  heard: {heard}")
        print(f"  reply: {reply}")

        tts_latency = speaker.say(reply)

        print(
            f"  [asr {asr_done - turn_ended:.2f}s | "
            f"tts first audio {tts_latency:.2f}s | "
            f"total gap "
            f"{asr_done - turn_ended + tts_latency:.2f}s]"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
