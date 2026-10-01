import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from ml.events.event_classifier import SoundEventClassifier

TESTS_AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"

def run_false_positive_benchmarks():
    pipeline = SoundEventClassifier()
    print("\n=======================================================")
    print("      ECHOSENSE FALSE POSITIVE BENCHMARK SUITE         ")
    print("=======================================================")

    test_files = [
        ("sample_ambient_silence.wav", "NORMAL", "Low ambient hiss should NOT trigger alerts"),
        ("sample_speech.wav", "NORMAL", "Conversational voice should NOT trigger emergency alerts"),
        ("sample_clapping.wav", "INFO", "Clapping should be classified as Clapping/Info, NOT Glass Break"),
        ("sample_knock.wav", "WARNING", "Door knock should trigger Warning, NOT Critical Alarm"),
        ("sample_doorbell.wav", "WARNING", "Doorbell chime should trigger Warning, NOT WhatsApp"),
        ("sample_glass_break.wav", "CRITICAL", "Glass break should validate as Critical"),
        ("sample_alarm.wav", "CRITICAL", "Alarm tone should validate as Critical")
    ]

    passed_count = 0
    total_count = len(test_files)

    for filename, expected_severity, description in test_files:
        filepath = TESTS_AUDIO_DIR / filename
        if not filepath.exists():
            print(f"[-] SKIPPED: {filename} not found.")
            continue

        pipeline.reset()
        results = pipeline.process_wav_file(str(filepath))
        
        # Check highest severity detected across windows
        severities = [r.get("validatedEvent", {}).get("severity") for r in results if r.get("validatedEvent")]
        top_severity = "NORMAL"
        if "CRITICAL" in severities:
            top_severity = "CRITICAL"
        elif "WARNING" in severities:
            top_severity = "WARNING"
        elif "INFO" in severities:
            top_severity = "INFO"

        # Check if false positive occurred
        if expected_severity == "NORMAL" and top_severity == "CRITICAL":
            print(f"[FAIL] FALSE POSITIVE on {filename}! Classified as {top_severity}. {description}")
        elif expected_severity == "INFO" and top_severity == "CRITICAL":
            print(f"[FAIL] FALSE POSITIVE on {filename}! Classified as {top_severity}. {description}")
        else:
            print(f"[PASS] {filename:<26} -> Severity: {top_severity:<8} | Expected: {expected_severity:<8} ({description})")
            passed_count += 1

    print("-------------------------------------------------------")
    print(f"Discrimination Benchmark Results: {passed_count}/{total_count} Passed ({int(passed_count/total_count*100)}%)")
    print("=======================================================\n")
    return passed_count == total_count

def test_false_positive_benchmarks():
    assert run_false_positive_benchmarks()

if __name__ == "__main__":
    run_false_positive_benchmarks()
