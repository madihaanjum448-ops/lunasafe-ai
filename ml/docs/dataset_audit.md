
# LunaSafe AI — BOULDERING Dataset Audit

## 1. Dataset Overview

- Dataset: BOULDERING
- Application: Lunar boulder detection and instance segmentation
- Total images inspected: 4,976
- Moon candidate images: 4,678
- Unique lunar source groups: 57

## 2. Dataset Structure

- Train: images and labels
- Validation: images and labels
- Test: images and labels
- Annotation format: Detectron2 instance segmentation JSON
- Additional format: YOLO instance segmentation YAML

## 3. Image Properties

- Image dimensions: 500 × 500 pixels (verified sample)
- Image format: PNG
- Annotation geometry: Bounding boxes and segmentation masks

## 4. Annotation Validation

- Annotation records matched to images: 100%
- Sampled masks tested: 100
- Successfully decoded masks: 100
- Empty masks: 0
- Decoding failures: 0

## 5. Corrected Leakage-Free Split

| Split | Images | Source Groups |
|---|---:|---:|
| Train | 3,275 | 39 |
| Validation | 936 | 12 |
| Test | 467 | 6 |

Cross-split source overlap: 0.

## 6. Metadata Requirements

Pixel scale and sun elevation are required for physical measurements and shadow-based height estimation.

Missing metadata must remain unavailable rather than being assumed.

A complete metadata coverage audit is pending.

## 7. Licence

Licence verification is pending. Confirm the dataset's original distribution terms before redistribution.

## 8. Conclusion

The dataset has been inspected, annotations validated, and a source-group-based leakage-free Moon dataset split prepared.
