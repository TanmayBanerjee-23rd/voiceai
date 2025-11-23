import pyaudio

# Audio config (matches linear16 @ 16000Hz)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024  # ~64ms chunks

class SpeakerStream:
    def __init__(self):
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = None

    def __enter__(self):
        self.stream = self.pyaudio_instance.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        print("Speaker playing...")
        return self.stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pyaudio_instance.terminate()
        print("Speaker closed.")

# export the class
__all__ = ['SpeakerStream', 'CHUNK']
