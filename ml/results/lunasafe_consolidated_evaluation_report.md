# LunaSafe AI — Consolidated Model Evaluation Report

## 1. Model identification

- Model: YOLOv8n-seg
- Architecture: YOLOv8 Nano Segmentation
- Task: Instance segmentation
- Class: boulder
- Checkpoint: lunasafe_yolov8n_seg_best.pt
- Checkpoint size: 6.71 MB
- SHA256: d4aa9172acba9c305d786593778726471ba6b5fbfd7288bb72ca64e431f05646

## 2. Training configuration

- Dataset YAML recorded in checkpoint: /kaggle/working/lunasafe_yolo_dataset/lunasafe.yaml
- Epochs configured: 50
- Epochs completed: 27
- Best epoch: 17 (from the existing training record)
- Image size: 640
- Batch size: 8
- Optimizer: SGD
- Initial learning rate: 0.01
- Patience: 10
- Workers: 2
- Pretrained weights: YOLOv8n-seg
- Seed: 2002
- Deterministic: true

The original Kaggle training run directory and dataset YAML are no longer
available. Training arguments were recovered from checkpoint metadata.

## 3. Checkpoint-saved validation metrics

These metrics are stored in the checkpoint's train_metrics field.

| Metric | Bounding box | Segmentation mask |
|---|---:|---:|
| Precision | 0.62765 | 0.37279 |
| Recall | 0.55341 | 0.37856 |
| mAP@50 | 0.58890 | 0.27882 |
| mAP@50-95 | 0.20617 | 0.07098 |

Additional saved validation values:
- Box loss: 2.37604
- Segmentation loss: 2.38833
- Classification loss: 1.34048
- Fitness: 0.27715

These are checkpoint-saved validation metrics, not independent test metrics.

## 4. Previously recorded 468-image evaluation

The existing lunasafe_test_metrics.json records:

- Images: 468
- Ground-truth instances: 20,989
- Checkpoint filename: lunasafe_yolov8n_seg_best.pt

| Metric | Bounding box | Mask |
|---|---:|---:|
| Precision | 0.602 | 0.340 |
| Recall | 0.553 | 0.340 |
| mAP@50 | 0.562 | 0.220 |
| mAP@50-95 | 0.196 | 0.0505 |

The original JSON does not record the confidence threshold used for these
Ultralytics metrics.

## 5. Custom mask evaluation

Source record: lunasafe_mask_evaluation.json

- Dataset split label: test
- Images: 468
- Confidence threshold: 0.25
- Mask IoU matching threshold: 0.50
- Ground-truth objects: 20,989
- Predictions: 25,352

| Metric | Value |
|---|---:|
| True positives | 13,362 |
| False positives | 11,990 |
| False negatives | 7,627 |
| Precision | 0.527059 |
| Recall | 0.636619 |
| F1 score | 0.576682 |

These custom mask metrics use one-to-one mask matching at the stated IoU
threshold. They are distinct from Ultralytics mAP metrics.

## 6. Size-wise custom mask evaluation

Object size is defined as the maximum dimension of the ground-truth
polygon bounding box in pixels.

| Size category | Ground truth | Matched GT | Recall | Precision |
|---|---:|---:|---:|---:|
| Small (<5 px) | 4,722 | 2,224 | 0.4710 | 0.3755 |
| Medium (5–10 px) | 12,456 | 8,314 | 0.6675 | 0.6029 |
| Large (10–20 px) | 3,451 | 2,559 | 0.7415 | 0.6586 |
| Very large (>=20 px) | 360 | 265 | 0.7361 | 0.6434 |

Source: lunasafe_size_wise_metrics.json

## 7. Five-image exploratory evaluation

A separate exploratory evaluation on five reconstructed test-inventory
images recorded:

- True positives: 129
- False positives: 134
- False negatives: 67
- Micro precision: 0.4905
- Micro recall: 0.6582
- Micro F1: 0.5624

This five-image result is not a substitute for the 468-image evaluation
and is not presented as a final test-set result.

## 8. Dataset provenance and test-set independence

The reconstructed lunar inventory contains:

- Total lunar images: 4,678
- Source groups: 58
- Reconstructed train: 3,274 images across 32 groups
- Reconstructed validation: 936 images across 15 groups
- Reconstructed test: 468 images across 11 groups

All 4,678 image files and all 4,678 annotation files were found.

The reconstructed split uses seed 2002 and source-group separation.
Its manifest and complete inventory are preserved separately.

Important limitation:
The original training YAML and original Kaggle training run directory
are no longer available. The checkpoint records the YAML path, but does
not preserve the historical contents of its train, validation, and test
directories.

Therefore, the reconstructed 468-image split has not been proven to be
identical to the original evaluation split or independent of training.
The previously recorded 468-image metrics must be treated as historical
evaluation results with unresolved split provenance, not independently
verified held-out test performance.

## 9. Inference configuration and reproducibility

The custom mask evaluation records:
- Confidence threshold: 0.25
- Mask IoU matching threshold: 0.50

The original Ultralytics evaluation JSON does not preserve its confidence
threshold or all evaluation command arguments.

A reproducible inference command for future evaluation is:

```python
from ultralytics import YOLO

model = YOLO("lunasafe_yolov8n_seg_best.pt")

results = model.predict(
    source="path/to/image.png",
    imgsz=640,
    conf=0.25,
    iou=0.7
)
```

## 10. Final evidence status

### Verified
- Checkpoint identity by SHA256.
- Checkpoint architecture and class.
- Embedded training arguments and validation metrics.
- Reconstructed lunar inventory: 4,678 images and 4,678 annotations.
- Recorded custom mask evaluation thresholds and metrics.
- Recorded size-wise evaluation methodology.

### Not independently verified
- Exact historical contents of the original training dataset folders.
- Independence of the reconstructed 468-image test set from training.
- Confidence threshold used for historical Ultralytics metrics.
- Whether the historical 468-image evaluation used this exact checkpoint SHA256.

### Conclusion

The model checkpoint, training configuration, validation metrics,
reconstructed lunar inventory, and historical evaluation records are
documented.

Test-set independence and some historical evaluation settings remain
unverified and must be disclosed in project reporting.
