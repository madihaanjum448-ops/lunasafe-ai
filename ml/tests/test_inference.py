from types import SimpleNamespace

import cv2
import numpy as np
import pytest

import ml.src.inference as inference


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def __getitem__(self, index):
        return FakeTensor(self.value[index])

    def cpu(self):
        return self

    def numpy(self):
        return np.array(self.value)

    def tolist(self):
        return self.value

    def item(self):
        return self.value


class FakeBox:
    def __init__(self):
        self.xyxy = FakeTensor([[10.0, 20.0, 40.0, 60.0]])
        self.conf = FakeTensor([0.92])
        self.cls = FakeTensor([0])


class FakeModel:
    task = "segment"
    names = {0: "boulder"}

    def predict(self, **kwargs):
        return [
            SimpleNamespace(
                boxes=[FakeBox()],
                masks=SimpleNamespace(
                    xy=[
                        np.array([
                            [10.0, 20.0],
                            [40.0, 20.0],
                            [40.0, 60.0],
                            [10.0, 60.0],
                        ])
                    ]
                ),
            )
        ]


def create_image(path):
    image = np.full((100, 120, 3), 180, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def mock_yolo(monkeypatch, task="segment"):
    class Model(FakeModel):
        pass

    Model.task = task

    monkeypatch.setattr(
        inference,
        "YOLO",
        lambda path: Model(),
    )


def test_predict_returns_detection_output(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()

    image_path = tmp_path / "sample.png"
    create_image(image_path)

    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    result = detector.predict(
        image_path,
        pixel_scale_m=0.5,
        sun_elevation_deg=33.0,
        projection="test-projection",
    )

    assert result["image"]["id"] == "sample"
    assert result["image"]["width"] == 120
    assert result["image"]["height"] == 100
    assert result["image"]["pixel_scale_m"] == 0.5
    assert result["image"]["sun_elevation_deg"] == 33.0
    assert result["image"]["projection"] == "test-projection"

    assert result["model_name"] == "YOLOv8n-seg"
    assert result["is_mock"] is False
    assert len(result["detections"]) == 1

    detection = result["detections"][0]

    assert detection["id"] == 1
    assert detection["bbox"] == [10.0, 20.0, 40.0, 60.0]
    assert detection["confidence"] == 0.92
    assert detection["class_name"] == "boulder"
    assert detection["size_m"] is None
    assert len(detection["polygon"]) == 4


def test_missing_checkpoint_raises_error(tmp_path):
    missing_checkpoint = tmp_path / "missing.pt"

    with pytest.raises(FileNotFoundError):
        inference.LunaSafeInference(
            model_path=missing_checkpoint
        )


def test_non_segmentation_model_raises_error(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()

    mock_yolo(monkeypatch, task="detect")

    with pytest.raises(ValueError, match="segmentation model"):
        inference.LunaSafeInference(
            model_path=checkpoint
        )


def test_missing_image_raises_error(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()

    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    with pytest.raises(FileNotFoundError):
        detector.predict(tmp_path / "missing.png")


def test_unreadable_image_raises_error(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()

    image_path = tmp_path / "invalid.png"
    image_path.write_text("not an image")

    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    with pytest.raises(ValueError, match="Could not read image"):
        detector.predict(image_path)


def test_invalid_confidence_raises_error(tmp_path, monkeypatch):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()

    image_path = tmp_path / "sample.png"
    create_image(image_path)

    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    with pytest.raises(ValueError, match="Confidence"):
        detector.predict(image_path, confidence=1.5)


@pytest.mark.parametrize("iou", [-0.1, 1.1])
def test_invalid_iou_raises_error(tmp_path, monkeypatch, iou):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()
    mock_yolo(monkeypatch)

    with pytest.raises(ValueError, match="IoU"):
        inference.LunaSafeInference(
            model_path=checkpoint,
            iou=iou,
        )


@pytest.mark.parametrize("image_size", [0, -640, 640.5])
def test_invalid_image_size_raises_error(
    tmp_path, monkeypatch, image_size
):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()
    mock_yolo(monkeypatch)

    with pytest.raises(ValueError, match="(?i)image size"):
        inference.LunaSafeInference(
            model_path=checkpoint,
            image_size=image_size,
        )


@pytest.mark.parametrize("pixel_scale", [0, -0.5])
def test_invalid_pixel_scale_raises_error(
    tmp_path, monkeypatch, pixel_scale
):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()
    image_path = tmp_path / "sample.png"
    create_image(image_path)
    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    with pytest.raises(ValueError, match="(?i)pixel scale"):
        detector.predict(
            image_path,
            pixel_scale_m=pixel_scale,
        )


@pytest.mark.parametrize("sun_elevation", [-1, 91])
def test_invalid_sun_elevation_raises_error(
    tmp_path, monkeypatch, sun_elevation
):
    checkpoint = tmp_path / "model.pt"
    checkpoint.touch()
    image_path = tmp_path / "sample.png"
    create_image(image_path)
    mock_yolo(monkeypatch)

    detector = inference.LunaSafeInference(
        model_path=checkpoint
    )

    with pytest.raises(ValueError, match="(?i)sun elevation"):
        detector.predict(
            image_path,
            sun_elevation_deg=sun_elevation,
        )
