"""
EchoSense Universal Launcher & CLI Entrypoint.
Supports:
1. Production Server:    python run.py --server [--port 8000]
2. Audio Replay Mode:    python run.py --replay tests/audio/sample_glass_break.wav
3. Test Suite Runner:    python run.py --test
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def run_server(host: str = "0.0.0.0", port: int = 8000, use_laptop_mic: bool = False):
    """Start FastAPI Uvicorn web server."""
    import uvicorn
    import os
    if use_laptop_mic:
        os.environ["USE_LAPTOP_MIC"] = "True"
        
    from backend.config.settings import settings
    print("=================================================================")
    print("          STARTING ECHOSENSE PRODUCTION INTELLIGENCE HUB         ")
    print(f"  URL:       http://localhost:{port}")
    print(f"  Network:   http://{host}:{port}")
    print(f"  WebSocket: ws://localhost:{port}/ws/live")
    if use_laptop_mic:
        print("  Mic Mode:  🎤 HOST LAPTOP BUILT-IN MICROPHONE (Active)")
    else:
        print("  Mic Mode:  ESP32 Digital I2S Microphone (Waiting stream)")
    print("=================================================================")
    uvicorn.run("backend.server:app", host=host, port=port, reload=False)

def run_replay(audio_filepath: str):
    """Execute bit-exact audio replay mode on a recorded WAV file."""
    from ml.events.event_classifier import SoundEventClassifier
    from ml.audio.preprocessor import AudioPreprocessor
    
    path = Path(audio_filepath)
    if not path.exists():
        print(f"[ERROR] Audio benchmark file not found: {audio_filepath}")
        sys.exit(1)

    print(f"\n[REPLAY MODE] Loading benchmark audio: {path.name}")
    prep = AudioPreprocessor()
    audio, sr = prep.load_wav_file(str(path))
    windows = prep.extract_windows(audio)
    
    print(f"[REPLAY] Loaded {len(audio)} samples ({len(audio)/sr:.2f}s) at {sr} Hz.")
    print(f"[REPLAY] Extracted {len(windows)} sliding windows (0.975s, 50% overlap).")
    print("-----------------------------------------------------------------")

    classifier = SoundEventClassifier()
    events_triggered = []

    for idx, win in enumerate(windows):
        t_sec = idx * 0.5
        res = classifier.process_window(win)
        
        top_pred = res["topPredictions"][0] if res.get("topPredictions") else {"label": "None", "score": 0.0}
        confs = res["validation"]["confirmations"]
        req = res["validation"]["required"]
        
        print(f"Window {idx+1:02d} [{t_sec:4.1f}s - {t_sec+0.975:4.1f}s]: "
              f"Raw: {top_pred['label']:<18} ({top_pred['score']:.2f}) | "
              f"Status: {res['status']:<10} | "
              f"Validation: {confs}/{req} | "
              f"RMS: {res['rms']:.4f}")
        
        if res.get("validatedEvent"):
            ve = res["validatedEvent"]
            events_triggered.append(ve)
            print("\n" + "=" * 55)
            print("  🚨 VALIDATED SAFETY EVENT TRIGGERED!")
            print(f"  Final Event:  {ve['displayLabel']}")
            print(f"  Severity:     {ve['severity']}")
            print(f"  Confidence:   {ve['confidence']:.2f}")
            print(f"  LCD Text:     [{ve['lcdLine1']}] / [{ve['lcdLine2']}]")
            print(f"  RGB Mode:     {ve['rgbMode']}")
            print(f"  Buzzer:       {ve['buzzerPattern']}")
            print(f"  WhatsApp:     {'TRIGGERED' if ve['notificationRequired'] else 'NOT REQUIRED'}")
            print("=" * 55 + "\n")

    print("\n-----------------------------------------------------------------")
    print(f"[REPLAY SUMMARY] Completed {len(windows)} windows. Validated Events: {len(events_triggered)}")
    if events_triggered:
        for e in events_triggered:
            print(f" - {e['displayLabel']} (Severity: {e['severity']}, Conf: {e['confidence']})")
    else:
        print(" - No critical or warning safety alerts validated (Normal/Ambient).")
    print("=================================================================\n")

def run_tests():
    """Run pytest suite and false positive benchmarks."""
    import subprocess
    print("\n--- Running Unit & Integration Tests ---")
    ret1 = subprocess.run([sys.executable, "-m", "pytest", "tests/integration/test_end_to_end.py", "-v"])
    
    print("\n--- Running False Positive Benchmarks ---")
    ret2 = subprocess.run([sys.executable, "tests/integration/test_false_positives.py"])
    
    if ret1.returncode == 0 and ret2.returncode == 0:
        print("\n✅ ALL TESTS AND BENCHMARKS PASSED SUCCESSFULLY!")
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="EchoSense Universal System CLI")
    parser.add_argument("--server", action="store_true", help="Launch EchoSense web backend and dashboard")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--mic", "--use-laptop-mic", action="store_true", dest="mic", help="Capture live environmental audio directly from host laptop built-in microphone")
    parser.add_argument("--replay", type=str, help="Run an audio WAV file through the ML validation pipeline")
    parser.add_argument("--test", action="store_true", help="Run automated test suite and benchmarks")

    args = parser.parse_args()

    if args.replay:
        run_replay(args.replay)
    elif args.test:
        run_tests()
    elif args.server or args.mic:
        run_server(host=args.host, port=args.port, use_laptop_mic=args.mic)
    else:
        # Default behavior: run replay demonstration then start server instructions
        parser.print_help()

if __name__ == "__main__":
    main()
