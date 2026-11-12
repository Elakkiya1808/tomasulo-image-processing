from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Instruction:
    op: str
    dst: str
    src1: str
    src2: str
    description: str = ""


def generate_instructions(operation: str, tile_count: int = 16) -> List[Instruction]:
    """
    Generate a reproducible instruction trace representing independent image tiles.
    Each tile uses unique virtual registers, so dependencies are explicit and
    separate tiles can execute in parallel.

    The trace is representative of arithmetic work; it is not a compiler-generated
    trace of the actual Pillow/NumPy implementation.
    """
    if tile_count < 1:
        raise ValueError("tile_count must be at least 1")

    instructions = []

    for t in range(tile_count):
        suffix = f"_{t}"

        if operation == "Grayscale":
            instructions.extend([
                Instruction("MUL", f"F_R{suffix}", f"R{suffix}", "C0299",
                            f"Tile {t}: red contribution"),
                Instruction("MUL", f"F_G{suffix}", f"G{suffix}", "C0587",
                            f"Tile {t}: green contribution"),
                Instruction("MUL", f"F_B{suffix}", f"B{suffix}", "C0114",
                            f"Tile {t}: blue contribution"),
                Instruction("ADD", f"F_RG{suffix}", f"F_R{suffix}", f"F_G{suffix}",
                            f"Tile {t}: combine red and green"),
                Instruction("ADD", f"F_GRAY{suffix}", f"F_RG{suffix}", f"F_B{suffix}",
                            f"Tile {t}: grayscale intensity"),
            ])

        elif operation == "Brightness":
            instructions.extend([
                Instruction("MUL", f"F_R{suffix}", f"R{suffix}", "FACTOR",
                            f"Tile {t}: adjust red"),
                Instruction("MUL", f"F_G{suffix}", f"G{suffix}", "FACTOR",
                            f"Tile {t}: adjust green"),
                Instruction("MUL", f"F_B{suffix}", f"B{suffix}", "FACTOR",
                            f"Tile {t}: adjust blue"),
            ])

        elif operation == "Edge Detection":
            instructions.extend([
                Instruction("MUL", f"F_X1{suffix}", f"P1{suffix}", "K1",
                            f"Tile {t}: horizontal gradient term 1"),
                Instruction("MUL", f"F_X2{suffix}", f"P2{suffix}", "K2",
                            f"Tile {t}: horizontal gradient term 2"),
                Instruction("ADD", f"F_GX{suffix}", f"F_X1{suffix}", f"F_X2{suffix}",
                            f"Tile {t}: combine horizontal terms"),
                Instruction("MUL", f"F_Y1{suffix}", f"P3{suffix}", "K1",
                            f"Tile {t}: vertical gradient term"),
                Instruction("SUB", f"F_G{suffix}", f"F_GX{suffix}", f"F_Y1{suffix}",
                            f"Tile {t}: combine gradient terms"),
            ])

        elif operation == "Sharpen":
            instructions.extend([
                Instruction("MUL", f"F_CENTER{suffix}", f"CENTER{suffix}", "K5",
                            f"Tile {t}: center contribution"),
                Instruction("MUL", f"F_TOP{suffix}", f"TOP{suffix}", "KN",
                            f"Tile {t}: top contribution"),
                Instruction("MUL", f"F_BOTTOM{suffix}", f"BOTTOM{suffix}", "KN",
                            f"Tile {t}: bottom contribution"),
                Instruction("MUL", f"F_LEFT{suffix}", f"LEFT{suffix}", "KN",
                            f"Tile {t}: left contribution"),
                Instruction("MUL", f"F_RIGHT{suffix}", f"RIGHT{suffix}", "KN",
                            f"Tile {t}: right contribution"),
                Instruction("SUB", f"F_S1{suffix}", f"F_CENTER{suffix}", f"F_TOP{suffix}",
                            f"Tile {t}: subtract top"),
                Instruction("SUB", f"F_S2{suffix}", f"F_S1{suffix}", f"F_BOTTOM{suffix}",
                            f"Tile {t}: subtract bottom"),
                Instruction("SUB", f"F_S3{suffix}", f"F_S2{suffix}", f"F_LEFT{suffix}",
                            f"Tile {t}: subtract left"),
                Instruction("SUB", f"F_OUT{suffix}", f"F_S3{suffix}", f"F_RIGHT{suffix}",
                            f"Tile {t}: subtract right"),
            ])

        else:
            raise ValueError(f"Unsupported operation: {operation}")

    return instructions


def initialize_registers(simulator, operation: str, tile_count: int,
                         brightness_factor: float = 1.3, image=None):
    """Initialize source registers using average image intensities when available."""
    if image is not None:
        import numpy as np
        arr = np.asarray(image.convert("RGB"), dtype=np.float32)
        mean_rgb = arr.reshape(-1, 3).mean(axis=0)
        r, g, b = map(float, mean_rgb)
    else:
        r, g, b = 100.0, 150.0, 200.0

    constants = {
        "C0299": 0.299,
        "C0587": 0.587,
        "C0114": 0.114,
        "FACTOR": float(brightness_factor),
        "K1": 1.0,
        "K2": 2.0,
        "K5": 5.0,
        "KN": 1.0,
    }
    for name, value in constants.items():
        simulator.set_register(name, value)

    for t in range(tile_count):
        suffix = f"_{t}"
        for prefix, value in [("R", r), ("G", g), ("B", b)]:
            simulator.set_register(f"{prefix}{suffix}", value)

        # Illustrative neighborhood samples for the edge/sharpen instruction traces.
        samples = {
            f"P1{suffix}": r,
            f"P2{suffix}": g,
            f"P3{suffix}": b,
            f"CENTER{suffix}": (r + g + b) / 3.0,
            f"TOP{suffix}": r,
            f"BOTTOM{suffix}": g,
            f"LEFT{suffix}": b,
            f"RIGHT{suffix}": (r + g) / 2.0,
        }
        for name, value in samples.items():
            simulator.set_register(name, value)
