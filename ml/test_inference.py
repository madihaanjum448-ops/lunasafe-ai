
from pathlib import Path
import json

from ml.src.inference import LunaSafeInference


# Project root
ROOT = Path(__file__).resolve().parents[1]

# Replace this with the actual test image path
IMAGE_PATH = (
    ROOT / "ml" / "data" / "sample"
    / "M1098366480_0922_image.png"
)

# Initialize model
detector = LunaSafeInference(
    confidence=0.25,
    device="cpu"
)

# Run inference
output = detector.predict(IMAGE_PATH)

# Display results
print("INFERENCE SUCCESSFUL")
print("Image:", output["image"])
print("Total detections:", len(output["detections"]))

if output["detections"]:
    print("\nFirst detection:")
    print(json.dumps(output["detections"][0], indent=4))

# Save JSON
OUTPUT_PATH = ROOT / "ml" / "results" / "sample_inference.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_PATH, "w") as file:
    json.dump(output, file, indent=4)

print("\nJSON saved at:", OUTPUT_PATH)
