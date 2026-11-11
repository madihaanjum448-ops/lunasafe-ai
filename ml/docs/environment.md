
# LunaSafe AI — ML Environment

## Model Development Environment

- Framework: PyTorch
- Computer Vision: Torchvision
- Architecture: Mask R-CNN
- Backbone: ResNet-50 FPN
- Pretrained Weights: COCO
- Number of Classes: 2 (Background, Boulder)

## Training Environment

- Platform: Kaggle Notebooks
- GPU: NVIDIA Tesla T4
- GPU Memory: Approximately 13 GB
- PyTorch: 2.11.0+cu130
- Torchvision: 0.26.0+cu130
- CUDA Device: cuda:0

## Dataset

- Dataset: BOULDERING
- Target: Lunar boulder detection and instance segmentation
- Corrected Moon images: 4,678
- Unique lunar source groups: 57

## Corrected Dataset Split

| Split | Images | Source Groups |
|---|---:|---:|
| Train | 3,275 | 39 |
| Validation | 936 | 12 |
| Test | 467 | 6 |

## Status

- GPU environment verified.
- Dataset inspected and annotations validated.
- Mask R-CNN training completed.
- YOLO baseline pending.
- Final held-out evaluation pending.
