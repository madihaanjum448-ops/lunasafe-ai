# LunaSafe AI — Member 1 ML Handoff

## 1. Model identification

- Model: YOLOv8n-seg
- Architecture: YOLOv8 Nano Segmentation
- Task: Boulder detection and instance segmentation
- Classes: 1 (boulder)
- Best epoch: 17
- Epochs completed: 27

## 2. Checkpoint

- File: lunasafe_yolov8n_seg_best.pt
- Size: 6.71 MB
- SHA256: d4aa9172acba9c305d786593778726471ba6b5fbfd7288bb72ca64e431f05646
- Location in project: ml/models/lunasafe_yolov8n_seg_best.pt
- Checkpoint is not committed to Git.

## 3. Training configuration

- Configured epochs: 50
- Image size: 640
- Batch size: 8
- Optimizer: SGD
- Initial learning rate: 0.01
- Patience: 10
- Workers: 2
- Pretrained weights: Yes
- Seed: 2002
- Deterministic: True
- Training device: CUDA 0

## 4. Recorded bounding-box test metrics

Source: lunasafe_test_metrics.json

- Test images: 468
- Test instances: 20,989
- Precision: 60.2%
- Recall: 55.3%
- mAP@50: 56.2%
- mAP@50-95: 19.6%

## 5. Recorded mask metrics — primary test record

Source: lunasafe_test_metrics.json

- Precision: 34.0%
- Recall: 34.0%
- mAP@50: 22.0%
- mAP@50-95: 5.05%

## 6. Threshold-based mask evaluation

Source: lunasafe_mask_evaluation.json

- Test images: 468
- Ground-truth objects: 20,989
- Predictions: 25,352
- True positives: 13,362
- False positives: 11,990
- False negatives: 7,627
- Confidence threshold: 0.25
- Mask IoU threshold: 0.50
- Precision: 52.71%
- Recall: 63.66%
- F1 score: 57.67%

Note: The primary test record and threshold-based mask evaluation report different precision and recall values. They are separate recorded evaluation outputs. Their procedures must be reconciled before treating them as directly comparable.

## 7. Size-wise detection performance

Source: lunasafe_size_wise_metrics.json

Size is based on the maximum dimension of the polygon bounding box in pixels.

| Boulder size | Precision | Recall |
|---|---:|---:|
| Small (<5 px) | 37.55% | 47.10% |
| Medium (5–10 px) | 60.29% | 66.75% |
| Large (10–20 px) | 65.86% | 74.15% |
| Very large (>=20 px) | 64.34% | 73.61% |

Small boulders are the weakest category in the recorded size-wise evaluation.

## 8. Independent LROC image evaluation

- Product: M174800267RE
- Paired CDR product: M174800267RC
- Orbit: 10894
- Image crop: 2000 x 2000 pixels
- Tiled inference at confidence threshold 0.25 produced 484 detections.
- No verified ground-truth annotations were available for this image.
- Detection confidence is not an accuracy measurement.
- Manual review did not establish confirmed boulder-shadow associations.

This is exploratory independent-image inference, not a quantitative accuracy evaluation.

## 9. Shadow measurement and physical height

- Shadow extraction remains experimental.
- Observation geometry has been recorded.
- Seven preliminary shadow-review records are available.
- Detection 35 was manually inspected; no distinct continuous boulder-associated shadow was confirmed.
- Shadow length: not validated.
- Physical height: not validated.

Do not present experimental shadow candidates as verified measurements.

## 10. Dataset and evaluation caveats

- Lunar inventory: 4,678 images.
- Reconstructed split: 3,274 train, 936 validation, 468 test.
- Test-set independence and some historical evaluation settings remain unverified.
- These limitations must be disclosed in project reporting.

## 11. Relevant project files

- ml/results/lunasafe_test_metrics.json
- ml/results/lunasafe_mask_evaluation.json
- ml/results/lunasafe_size_wise_metrics.json
- ml/results/lunasafe_training_config.json
- ml/results/lunasafe_checkpoint_evidence.json
- ml/results/lunasafe_consolidated_evaluation_report.md
- ml/results/lroc_validation/observation_geometry.json
- ml/results/lroc_validation/shadow_manual_review.csv

## 12. Handoff status

This sheet summarizes recorded Member 1 results and limitations.

Checkpoint transfer to Member 2 must happen separately. Verify the SHA256 after transfer.

Known-site validation and shadow-height validation are not established by the evidence recorded here.
