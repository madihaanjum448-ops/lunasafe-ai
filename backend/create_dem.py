
import numpy as np

# Create a 16 x 16 DEM.
# Elevation increases by 1 metre per pixel horizontally.
dem = np.tile(np.arange(16, dtype=float), (16, 1))

# Save the elevation grid as a NumPy file.
np.save("test_dem.npy", dem)

print("DEM file created successfully!")
print("Shape:", dem.shape)
print("Saved as: test_dem.npy")
