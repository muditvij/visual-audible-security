"""
Synthetic Audio Benchmark Generator for EchoSense.
Creates calibrated 16000 Hz, 16-bit Mono WAV audio benchmarks with authentic
spectral signatures for Glass Break, Alarm, Doorbell, Knock, Speech, Clapping, and Silence.
"""

import os
import wave
import numpy as np
from pathlib import Path

SAMPLE_RATE = 16000

def save_wav(filepath: Path, samples: np.ndarray):
    """Save 1D float32 [-1.0, 1.0] samples to 16-bit PCM WAV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # Clip and convert to int16
    samples_clipped = np.clip(samples, -1.0, 1.0)
    int16_samples = (samples_clipped * 32767).astype(np.int16)
    
    with wave.open(str(filepath), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16_samples.tobytes())
    print(f"Generated benchmark WAV: {filepath.name} (Duration: {len(samples)/SAMPLE_RATE:.1f}s)")

def generate_benchmarks():
    target_dir = Path(__file__).resolve().parent

    # 1. Continuous Tonal Alarm / Smoke Detector (3.0s, 3100Hz pulsed tone)
    duration = 3.0
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # 0.5s on, 0.5s off pulse
    pulse_gate = (np.sin(2 * np.pi * 1.0 * t) > 0).astype(float)
    carrier = np.sin(2 * np.pi * 3100 * t) + 0.3 * np.sin(2 * np.pi * 6200 * t)
    alarm_samples = carrier * pulse_gate * 0.4
    save_wav(target_dir / "sample_alarm.wav", alarm_samples)

    # 2. Glass Break / Shatter (2.5s, sharp high-frequency transient + resonance > 4.5kHz)
    glass_samples = np.zeros(int(SAMPLE_RATE * 2.5), dtype=np.float32)
    # 3 impact bursts
    for burst_start_sec in [0.2, 0.8, 1.5]:
        start_idx = int(burst_start_sec * SAMPLE_RATE)
        burst_len = int(0.35 * SAMPLE_RATE)
        tb = np.linspace(0, 0.35, burst_len, endpoint=False)
        decay = np.exp(-tb * 16.0)
        # High frequency noise + harmonics
        noise = np.random.uniform(-1.0, 1.0, burst_len)
        shatter_tone = np.sin(2 * np.pi * 4800 * tb) + np.sin(2 * np.pi * 6500 * tb)
        glass_burst = (noise * 0.5 + shatter_tone * 0.5) * decay * 0.65
        glass_samples[start_idx:start_idx + burst_len] += glass_burst
    save_wav(target_dir / "sample_glass_break.wav", glass_samples)

    # 3. Doorbell Chime (3.0s, dual tone 784Hz [G5] then 523Hz [C5])
    doorbell_samples = np.zeros(int(SAMPLE_RATE * 3.0), dtype=np.float32)
    # Ding (784Hz)
    t1 = np.linspace(0, 1.2, int(SAMPLE_RATE * 1.2), endpoint=False)
    ding = np.sin(2 * np.pi * 784 * t1) * np.exp(-t1 * 3.5) * 0.5
    doorbell_samples[int(0.2 * SAMPLE_RATE):int(0.2 * SAMPLE_RATE) + len(ding)] += ding
    # Dong (523Hz)
    t2 = np.linspace(0, 1.5, int(SAMPLE_RATE * 1.5), endpoint=False)
    dong = np.sin(2 * np.pi * 523 * t2) * np.exp(-t2 * 2.5) * 0.5
    doorbell_samples[int(1.1 * SAMPLE_RATE):int(1.1 * SAMPLE_RATE) + len(dong)] += dong
    save_wav(target_dir / "sample_doorbell.wav", doorbell_samples)

    # 4. Knock / Tap (2.0s, low-frequency 180Hz thump)
    knock_samples = np.zeros(int(SAMPLE_RATE * 2.0), dtype=np.float32)
    for knock_time in [0.3, 0.6, 0.9]:
        idx = int(knock_time * SAMPLE_RATE)
        tk = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15), endpoint=False)
        decay = np.exp(-tk * 28.0)
        thump = np.sin(2 * np.pi * 180 * tk) * decay * 0.6
        knock_samples[idx:idx + len(thump)] += thump
    save_wav(target_dir / "sample_knock.wav", knock_samples)

    # 5. Conversational Speech (3.0s, formant modulated energy 300Hz - 2200Hz)
    ts = np.linspace(0, 3.0, int(SAMPLE_RATE * 3.0), endpoint=False)
    f0 = 140 + 20 * np.sin(2 * np.pi * 3.0 * ts)  # Pitch modulation
    vowel = (np.sin(2 * np.pi * f0 * ts) +
             0.5 * np.sin(2 * np.pi * (f0 * 3) * ts) +
             0.3 * np.sin(2 * np.pi * (f0 * 7) * ts))
    envelope = (np.sin(2 * np.pi * 1.5 * ts)**2) * 0.35
    speech_samples = vowel * envelope
    save_wav(target_dir / "sample_speech.wav", speech_samples)

    # 6. Clapping (2.5s, sharp broad transients for false positive testing)
    clap_samples = np.zeros(int(SAMPLE_RATE * 2.5), dtype=np.float32)
    for clap_time in [0.2, 0.6, 1.0, 1.4]:
        idx = int(clap_time * SAMPLE_RATE)
        tc = np.linspace(0, 0.08, int(SAMPLE_RATE * 0.08), endpoint=False)
        burst = np.random.uniform(-0.8, 0.8, len(tc)) * np.exp(-tc * 60.0)
        clap_samples[idx:idx + len(burst)] += burst
    save_wav(target_dir / "sample_clapping.wav", clap_samples)

    # 7. Ambient Room Silence / Noise Floor (3.0s, very quiet hiss)
    silence_samples = np.random.normal(0, 0.003, int(SAMPLE_RATE * 3.0)).astype(np.float32)
    save_wav(target_dir / "sample_ambient_silence.wav", silence_samples)

if __name__ == "__main__":
    generate_benchmarks()
