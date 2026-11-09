
from pathlib import Path
import numpy as np

# Create a 16 x 16 DEM.
# Elevation increases by 1 metre per pixel horizontally.
dem = np.tile(np.arange(16, dtype=float), (16, 1))

# Save the elevation grid to tests/fixtures/test_dem.npy
out_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "test_dem.npy"
out_path.parent.mkdir(parents=True, exist_ok=True)
np.save(out_path, dem)

print("DEM file created successfully!")
print("Shape:", dem.shape)
print(f"Saved as: {out_path}")
