
"""
LunaSafe AI - Image validation and metadata extraction.

Rules:
- Never invent missing scientific metadata.
- Missing pixel scale, Sun elevation or projection remains None.
- GeoTIFF metadata is used only when it can be interpreted safely.
- User-supplied metadata is identified as user-supplied.
- Pixel scale is expressed in metres per pixel.
- Sun elevation is expressed in degrees above the horizon.

Supported image formats:
PNG, JPEG, TIFF and WEBP.
"""

import io
import math
import uuid

from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.schemas.contracts import ImageInfo


# ---------------------------------------------------------
# Supported image formats
# ---------------------------------------------------------

ALLOWED_FORMATS = {"PNG", "JPEG", "TIFF", "WEBP"}


# ---------------------------------------------------------
# GeoTIFF tag identifiers
# ---------------------------------------------------------

TAG_PIXEL_SCALE = 33550
TAG_TIEPOINT = 33922
TAG_GEOKEYS = 34735


# ---------------------------------------------------------
# Custom validation exception
# ---------------------------------------------------------

class ImageValidationError(Exception):
    """Raised when an uploaded image cannot safely be processed."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------
# Numeric validation helpers
# ---------------------------------------------------------

def _is_finite_positive(value: Any) -> bool:
    """Check whether a value is a positive finite number."""

    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError, OverflowError):
        return False


def _is_valid_sun_elevation(value: Any) -> bool:
    """Sun elevation must be strictly between 0 and 90 degrees."""

    try:
        value = float(value)
        return math.isfinite(value) and 0 < value < 90
    except (TypeError, ValueError, OverflowError):
        return False


# ---------------------------------------------------------
# GeoTIFF GeoKey parsing
# ---------------------------------------------------------

def _parse_geokeys(raw: Tuple[int, ...]) -> Dict[int, int]:
    """
    Parse the GeoKeyDirectory tag.

    GeoKeyDirectory format:
        Header: 4 values
        Each key: 4 values

    Only directly stored values are extracted here.
    """

    keys: Dict[int, int] = {}

    if raw is None:
        return keys

    try:
        raw = tuple(raw)

        if len(raw) < 4:
            return keys

        number_of_keys = int(raw[3])

        if number_of_keys < 0:
            return keys

        for index in range(number_of_keys):

            base = 4 + index * 4

            if base + 3 >= len(raw):
                break

            key_id = int(raw[base])
            tag_location = int(raw[base + 1])
            value_count = int(raw[base + 2])
            value_offset = int(raw[base + 3])

            # Only values stored directly in the GeoKey are handled.
            if tag_location == 0 and value_count == 1:
                keys[key_id] = value_offset

    except (TypeError, ValueError, OverflowError):
        return {}

    return keys


# ---------------------------------------------------------
# GeoTIFF metadata extraction
# ---------------------------------------------------------

def _read_geotiff(
    img: Image.Image,
    warnings: List[str],
) -> Dict[str, Any]:
    """
    Extract available GeoTIFF metadata.

    Does not attempt to convert geographic degrees into metres.

    Returns:
        pixel_scale_m
        crs
        geotransform
        projection
    """

    result: Dict[str, Any] = {
        "pixel_scale_m": None,
        "crs": None,
        "geotransform": None,
        "projection": None,
    }

    tags = getattr(img, "tag_v2", None)

    if tags is None:
        warnings.append(
            "TIFF file does not contain readable GeoTIFF metadata."
        )
        return result

    # -----------------------------------------------------
    # Read GeoKeys
    # -----------------------------------------------------

    try:
        raw_geokeys = tags.get(TAG_GEOKEYS, ())
        geokeys = _parse_geokeys(raw_geokeys)
    except Exception:
        geokeys = {}

    model_type = geokeys.get(1024)
    projected_epsg = geokeys.get(3072)
    geographic_epsg = geokeys.get(2048)
    linear_unit = geokeys.get(3076)

    if model_type is not None:

        epsg = projected_epsg or geographic_epsg

        result["crs"] = (
            f"GeoTIFF model_type={model_type}"
            + (f", epsg={epsg}" if epsg else "")
        )

    # -----------------------------------------------------
    # Read pixel scale
    # -----------------------------------------------------

    if TAG_PIXEL_SCALE not in tags:

        warnings.append(
            "GeoTIFF pixel-scale tag is missing. "
            "Metres per pixel cannot be determined from this file."
        )

        return result

    try:

        scale_values = tags.get(TAG_PIXEL_SCALE)

        if scale_values is None or len(scale_values) < 2:
            raise ValueError("Incomplete pixel-scale tag.")

        sx = float(scale_values[0])
        sy = float(scale_values[1])

        if not (
            math.isfinite(sx)
            and math.isfinite(sy)
            and sx > 0
            and sy > 0
        ):
            raise ValueError("Invalid pixel-scale values.")

    except (TypeError, ValueError, IndexError, OverflowError):

        warnings.append(
            "GeoTIFF pixel-scale tag is malformed or invalid. "
            "Metres per pixel were not extracted."
        )

        return result

    if abs(sx - sy) > 1e-9 * max(sx, sy):

        warnings.append(
            f"Pixel size differs in x ({sx}) and y ({sy}). "
            "The larger value will be used as a conservative "
            "approximation for scalar measurements."
        )

    # -----------------------------------------------------
    # Determine whether units are metres
    # -----------------------------------------------------

    if model_type == 1 and linear_unit == 9001:

        result["pixel_scale_m"] = max(sx, sy)

        result["projection"] = (
            "Projected CRS (units: metres) - see crs field"
        )

    elif model_type == 2:

        result["projection"] = "Geographic (degrees)"

        warnings.append(
            "GeoTIFF uses a geographic CRS. Pixel size is in "
            "degrees, not metres. Metres per pixel were NOT "
            "computed. Supply a verified pixel scale or reproject "
            "the image."
        )

    else:

        warnings.append(
            "GeoTIFF pixel-scale tag exists, but its coordinate "
            "system or linear units could not be confirmed as "
            "metres. Metres per pixel were NOT computed."
        )

    # -----------------------------------------------------
    # Read tiepoint for geotransform
    # -----------------------------------------------------

    if TAG_TIEPOINT in tags:

        try:

            tiepoints = tags.get(TAG_TIEPOINT)

            if tiepoints is not None and len(tiepoints) >= 6:

                # GeoTIFF tiepoint:
                # [i, j, k, x, y, z]
                #
                # Simplified north-up transform:
                # [pixel_width, 0, origin_x,
                #  0, -pixel_height, origin_y]

                origin_x = float(tiepoints[3])
                origin_y = float(tiepoints[4])

                if not (
                    math.isfinite(origin_x)
                    and math.isfinite(origin_y)
                ):
                    raise ValueError("Invalid tiepoint coordinates.")

                result["geotransform"] = [
                    sx,
                    0.0,
                    origin_x,
                    0.0,
                    -sy,
                    origin_y,
                ]

            else:

                warnings.append(
                    "GeoTIFF tiepoint is incomplete. "
                    "Geotransform was not extracted."
                )

        except (TypeError, ValueError, IndexError, OverflowError):

            warnings.append(
                "GeoTIFF tiepoint could not be interpreted. "
                "Geotransform was not extracted."
            )

    else:

        warnings.append(
            "GeoTIFF tiepoint is missing. "
            "Image origin could not be determined."
        )

    return result


# ---------------------------------------------------------
# Main upload processing function
# ---------------------------------------------------------

def process_upload(
    data: bytes,
    filename: str,
    settings: Settings,
    pixel_scale_m: Optional[float] = None,
    sun_elevation_deg: Optional[float] = None,
    projection: Optional[str] = None,
) -> Tuple[ImageInfo, List[str]]:
    """
    Validate an uploaded image and extract available metadata.

    Args:
        data:
            Uploaded image bytes.

        filename:
            Original uploaded filename.

        settings:
            Backend configuration.

        pixel_scale_m:
            Optional user-supplied metres per pixel.

        sun_elevation_deg:
            Optional user-supplied Sun elevation in degrees.

        projection:
            Optional user-supplied projection description.

    Returns:
        (ImageInfo, warnings)
    """

    warnings: List[str] = []
    source_parts: List[str] = []

    # -----------------------------------------------------
    # 1. Validate file size
    # -----------------------------------------------------

    if not data:

        raise ImageValidationError(
            "This file is empty.",
            400,
        )

    if len(data) > settings.max_file_size_bytes:

        raise ImageValidationError(
            f"File is too large. Maximum size is "
            f"{settings.max_file_size_mb} MB.",
            413,
        )

    # -----------------------------------------------------
    # 2. Open and verify image
    # -----------------------------------------------------

    try:

        image_stream = io.BytesIO(data)

        img = Image.open(image_stream)

        img.verify()

        # verify() invalidates the image object.
        # Reopen it to access dimensions and metadata.

        image_stream.seek(0)
        img = Image.open(image_stream)

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        SyntaxError,
        ValueError,
    ):

        raise ImageValidationError(
            "This image is corrupted or is not a supported image.",
            400,
        )

    # -----------------------------------------------------
    # 3. Validate image format
    # -----------------------------------------------------

    image_format = (img.format or "").upper()

    if image_format not in ALLOWED_FORMATS:

        img.close()

        raise ImageValidationError(
            "Only PNG, JPEG, TIFF or WEBP images are allowed.",
            415,
        )

    # -----------------------------------------------------
    # 4. Validate image dimensions
    # -----------------------------------------------------

    width, height = img.size

    if width <= 0 or height <= 0:

        img.close()

        raise ImageValidationError(
            "This image has invalid dimensions.",
            400,
        )

    if (
        width > settings.max_image_width
        or height > settings.max_image_height
    ):

        img.close()

        raise ImageValidationError(
            f"Image is too large. Maximum resolution is "
            f"{settings.max_image_width} x "
            f"{settings.max_image_height} px.",
            422,
        )

    # -----------------------------------------------------
    # 5. Extract GeoTIFF metadata where available
    # -----------------------------------------------------

    geo: Dict[str, Any] = {
        "pixel_scale_m": None,
        "crs": None,
        "geotransform": None,
        "projection": None,
    }

    if image_format == "TIFF":

        geo = _read_geotiff(img, warnings)

        if any(
            geo.get(key) is not None
            for key in (
                "pixel_scale_m",
                "crs",
                "geotransform",
                "projection",
            )
        ):
            source_parts.append("geotiff")

    img.close()

    # -----------------------------------------------------
    # 6. Resolve pixel scale
    # -----------------------------------------------------

    final_scale = geo["pixel_scale_m"]

    if pixel_scale_m is not None:

        if not _is_finite_positive(pixel_scale_m):

            raise ImageValidationError(
                "pixel_scale_m must be a positive finite number.",
                422,
            )

        pixel_scale_m = float(pixel_scale_m)

        if final_scale is not None:

            if not math.isclose(
                final_scale,
                pixel_scale_m,
                rel_tol=1e-6,
                abs_tol=1e-9,
            ):

                warnings.append(
                    f"User-supplied pixel scale ({pixel_scale_m} m/px) "
                    f"differs from the GeoTIFF value ({final_scale} m/px). "
                    "The user-supplied value will be used. "
                    "The original GeoTIFF georeferencing has not "
                    "been recalculated."
                )

        final_scale = pixel_scale_m

        source_parts.append("user_supplied_pixel_scale")

    # -----------------------------------------------------
    # 7. Resolve Sun elevation
    # -----------------------------------------------------

    if sun_elevation_deg is not None:

        if not _is_valid_sun_elevation(sun_elevation_deg):

            raise ImageValidationError(
                "sun_elevation_deg must be a finite angle "
                "between 0 and 90 degrees (exclusive).",
                422,
            )

        sun_elevation_deg = float(sun_elevation_deg)

        source_parts.append("user_supplied_sun_elevation")

    # -----------------------------------------------------
    # 8. Resolve projection
    # -----------------------------------------------------

    final_projection = geo["projection"]

    if projection is not None:

        projection = projection.strip()

        if not projection:

            raise ImageValidationError(
                "Projection cannot be an empty string.",
                422,
            )

        final_projection = projection

        source_parts.append("user_supplied_projection")

    # -----------------------------------------------------
    # 9. Check missing or unreliable metadata
    # -----------------------------------------------------

    if final_scale is None:

        warnings.append(
            "Pixel scale unavailable. Physical sizes in metres "
            "cannot be calculated."
        )

    if sun_elevation_deg is None:

        warnings.append(
            "Sun elevation unavailable. Shadow-based height "
            "cannot be calculated. Any diameter-based fallback "
            "must be labelled low confidence."
        )

    elif sun_elevation_deg < 5 or sun_elevation_deg > 80:

        warnings.append(
            f"Sun elevation ({sun_elevation_deg} degrees) is "
            "outside the recommended reliable range of "
            "5 to 80 degrees. Shadow-based height will have "
            "low confidence."
        )

    if final_projection is None:

        warnings.append(
            "Map projection unavailable."
        )

    if (
        image_format in {"PNG", "JPEG", "WEBP"}
        and final_scale is None
    ):

        warnings.append(
            f"{image_format} files normally do not carry "
            "georeferencing. Supply a verified pixel scale "
            "and Sun elevation from the original product metadata."
        )

    if (
        geo["geotransform"] is not None
        and pixel_scale_m is not None
        and geo["pixel_scale_m"] is not None
        and not math.isclose(
            geo["pixel_scale_m"],
            pixel_scale_m,
            rel_tol=1e-6,
            abs_tol=1e-9,
        )
    ):

        warnings.append(
            "The supplied pixel scale differs from the GeoTIFF "
            "scale. The original geotransform is retained and "
            "may not be consistent with the overridden scale. "
            "Geospatial alignment must be verified separately."
        )

    # -----------------------------------------------------
    # 10. Calculate incidence angle
    # -----------------------------------------------------

    # This is the complementary angle to Sun elevation,
    # assuming a locally horizontal surface.
    incidence_angle = (
        90.0 - sun_elevation_deg
        if sun_elevation_deg is not None
        else None
    )

    # -----------------------------------------------------
    # 11. Record metadata provenance
    # -----------------------------------------------------

    metadata_source = (
        ", ".join(sorted(set(source_parts)))
        if source_parts
        else "none"
    )

    # -----------------------------------------------------
    # 12. Create ImageInfo response
    # -----------------------------------------------------

    image_info = ImageInfo(
        id=f"img_{uuid.uuid4().hex[:8]}",
        width=width,
        height=height,
        pixel_scale_m=final_scale,
        sun_elevation_deg=sun_elevation_deg,
        incidence_angle_deg=incidence_angle,
        projection=final_projection,
        crs=geo["crs"],
        geotransform=geo["geotransform"],
        metadata_source=metadata_source,
    )

    return image_info, warnings
