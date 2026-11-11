# LunaSafe AI — ML Evaluation Results

## 1. Model Information

- **Model:** YOLOv8n-seg
- **Task:** Boulder instance segmentation
- **Pretrained weights:** COCO
- **Dataset:** BOULDERING
- **Test images:** 468
- **Ground-truth objects:** 20,989
- **Image size:** 640 × 640
- **Confidence threshold:** 0.25
- **Mask IoU threshold:** 0.50

## 2. Dataset Split

The Moon dataset was divided by source group to reduce data leakage.

| Split | Images |
|---|---:|
| Train | 3,274 |
| Validation | 936 |
| Test | 468 |
| Total | 4,678 |

## 3. Overall Mask Evaluation

| Metric | Result |
|---|---:|
| Precision | 52.71% |
| Recall | 63.66% |
| F1-score | 57.67% |
| True Positives | 13,362 |
| False Positives | 11,990 |
| False Negatives | 7,627 |

## 4. Size-wise Evaluation

Object size is calculated using the maximum dimension of the polygon bounding box in pixels.

| Boulder Size | Ground Truth | Precision | Recall |
|---|---:|---:|---:|
| Small (<5 px) | 4,722 | 37.55% | 47.10% |
| Medium (5–10 px) | 12,456 | 60.29% | 66.75% |
| Large (10–20 px) | 3,451 | 65.86% | 74.15% |
| Very Large (≥20 px) | 360 | 64.34% | 73.61% |

## 5. Ultralytics Test Metrics

| Metric | Box | Mask |
|---|---:|---:|
| Precision | 60.2% | 34.0% |
| Recall | 55.3% | 34.0% |
| mAP@50 | 56.2% | 22.0% |
| mAP@50–95 | 19.6% | 5.05% |

## 6. Observations

- Large and very large boulders show stronger detection performance.
- Small boulder detection remains a major improvement area.
- Instance segmentation performance is weaker than bounding-box detection.
- The model provides a baseline for further optimization and evaluation.

## 7. Result Files

- `lunasafe_test_metrics.json`
- `lunasafe_size_wise_metrics.json`
- `lunasafe_mask_evaluation.json`
- `lunasafe_training_config.json`

## 8. Model Checkpoint

The trained checkpoint `lunasafe_yolov8n_seg_best.pt` is maintained separately from the GitHub source repository because it is a model artifact.