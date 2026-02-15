import numpy as np
import sounddevice as sd

# Pick the first valid output device
devices = sd.query_devices()

# Filter for output devices
output_devices = [d for d in devices if d["max_output_channels"] > 0]

if not output_devices:
    raise RuntimeError("No output devices found!")

device_info = devices[0]
print(f"Found output device: {device_info}")

device_id = device_info["index"]
samplerate = device_info["default_samplerate"]
channels = min(2, device_info["max_output_channels"])

print(f"Using device {device_info['name']} with sample rate {samplerate}")

# Generate a test tone
duration = 2  # seconds
frequency = 440  # Hz (A4 note)
t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
audio = 0.5 * np.sin(2 * np.pi * frequency * t)

# Play the tone
with sd.OutputStream(
    # device=device_id,
    samplerate=samplerate,
    channels=channels,
):
    sd.play(audio, samplerate=samplerate)
    sd.wait()

print("Finished playing test tone.")
