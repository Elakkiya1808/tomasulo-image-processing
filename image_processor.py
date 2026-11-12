import io
import numpy as np
from PIL import Image, ImageFilter


def load_image(uploaded_file):
    """Load an uploaded image and convert it to RGB."""
    return Image.open(uploaded_file).convert("RGB")


def grayscale(image):
    return image.convert("L")


def adjust_brightness(image, factor=1.3):
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    result = np.clip(arr * float(factor), 0, 255).astype(np.uint8)
    return Image.fromarray(result, mode="RGB")


def edge_detection(image):
    # Pillow's FIND_EDGES is a real image-processing filter.
    return image.convert("RGB").filter(ImageFilter.FIND_EDGES).convert("L")


def sharpen_image(image):
    return image.convert("RGB").filter(ImageFilter.SHARPEN).convert("RGB")


def process_image(image, operation, brightness_factor=1.3):
    if operation == "Grayscale":
        return grayscale(image)
    if operation == "Brightness":
        return adjust_brightness(image, brightness_factor)
    if operation == "Edge Detection":
        return edge_detection(image)
    if operation == "Sharpen":
        return sharpen_image(image)
    raise ValueError(f"Unsupported operation: {operation}")


def image_to_png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
