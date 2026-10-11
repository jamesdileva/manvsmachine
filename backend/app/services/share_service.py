"""ShareService: shareable text summaries and PNG result cards (Implementation Guide §2.6/§5.8).

The card is rasterised with the standard library only — `zlib` for the PNG
deflate stream, `struct` for chunk framing — against a compact 5x7 bitmap font.
Master Architecture §8 lists Pillow-style image tooling under `html2canvas`
for client-side capture, which the dashboard uses for the DOM card; this
server-side renderer keeps the documented `generate_share_image` contract
without adding a native imaging dependency to the backend.
"""

import struct
import zlib

from app.schemas.session import SessionSummary

# 5x7 bitmap glyphs: '#' is ink, '.' is empty. Read top row first.
FONT: dict[str, tuple[str, ...]] = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", ".#..#", "#...#"),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "#": (".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#.", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
}

CARD_WIDTH = 600
CARD_HEIGHT = 400
GLYPH_WIDTH = 5
GLYPH_HEIGHT = 7

# Card palette (RGB).
BACKGROUND = (24, 24, 27)
INK = (250, 250, 250)
ACCENT = (244, 114, 40)
MUTED = (161, 161, 170)
HUMAN_BAR = (74, 222, 128)
AI_BAR = (248, 113, 113)


def _accuracy_label(summary: SessionSummary) -> str:
    return "N/A" if summary.accuracy is None else f"{round(summary.accuracy)}%"


class ShareService:
    """Text, image, and link generation for a finished session."""

    def generate_share_text(self, summary: SessionSummary) -> str:
        """The documented share line (Implementation Guide §2.6)."""
        return (
            f"I scored {summary.total_score} on today's Man vs. Machine "
            f"{summary.type} challenge! Can you beat my accuracy? #ManVsMachine"
        )

    def create_share_link(self, session_id: str) -> str:
        """Local replay route for the finished session."""
        return f"/s/{session_id}"

    def card_lines(self, summary: SessionSummary) -> list[str]:
        """The card's text layout, one entry per rendered line."""
        return [
            "MAN VS MACHINE",
            f"{summary.type.upper()} CHALLENGE",
            "",
            f"SCORE {summary.total_score}",
            f"ACCURACY {_accuracy_label(summary)}",
            "",
            "HUMANITY",
        ]

    def generate_share_image(self, summary: SessionSummary) -> bytes:
        """A 600x400 RGB PNG result card: stats, humanity bars, per-round tally."""
        pixels = bytearray(CARD_WIDTH * CARD_HEIGHT * 3)
        self._fill(pixels, BACKGROUND)

        lines = self.card_lines(summary)
        y = 32
        for index, line in enumerate(lines):
            colour = ACCENT if index == 0 else (INK if index == 3 else MUTED)
            scale = 4 if index == 0 else (6 if index == 3 else 3)
            if line:
                self._text(pixels, 32, y, line, colour, scale)
            y += GLYPH_HEIGHT * scale + 12

        self._humanity_bars(pixels, summary)
        self._round_tally(pixels, summary)
        return _encode_png(CARD_WIDTH, CARD_HEIGHT, pixels)

    # -----------------------------------------------------------------------
    # Card layout

    def _humanity_bars(self, pixels: bytearray, summary: SessionSummary) -> None:
        """Two labelled bars: the player's average humanity vs the AI's."""
        rounds = summary.rounds
        human = _mean(round_entry.humanity_human for round_entry in rounds)
        ai = _mean(round_entry.humanity_ai for round_entry in rounds)

        x, bar_top, bar_width, bar_height = 32, 300, CARD_WIDTH - 64, 18
        for label, value, colour, top in (
            ("YOU", human, HUMAN_BAR, bar_top),
            ("AI", ai, AI_BAR, bar_top + 26),
        ):
            self._text(pixels, x, top - 18, label, INK, 2)
            self._rect(pixels, x, top, bar_width, bar_height, (63, 63, 70))
            filled = int(bar_width * (min(max(value, 0), 100) / 100))
            if filled:
                self._rect(pixels, x, top, filled, bar_height, colour)
            self._text(
                pixels,
                x + bar_width - 8 * GLYPH_WIDTH * 2,
                top,
                f"{round(value)}%",
                INK,
                2,
            )

    def _round_tally(self, pixels: bytearray, summary: SessionSummary) -> None:
        """A compact per-round strip: green for a correct call, red for a miss."""
        x = 32
        for round_entry in summary.rounds:
            colour = (
                HUMAN_BAR if round_entry.correct else (AI_BAR if round_entry.correct is False else (90, 90, 95))
            )
            self._rect(pixels, x, 356, 28, 20, colour)
            self._text(pixels, x + 9, 359, str(round_entry.round_number), BACKGROUND, 2)
            x += 40

    # -----------------------------------------------------------------------
    # Raster primitives

    def _fill(self, pixels: bytearray, colour: tuple[int, int, int]) -> None:
        pixels[0 : len(pixels)] = bytes(colour) * (CARD_WIDTH * CARD_HEIGHT)

    def _rect(
        self,
        pixels: bytearray,
        x: int,
        y: int,
        width: int,
        height: int,
        colour: tuple[int, int, int],
    ) -> None:
        for row in range(max(0, y), min(CARD_HEIGHT, y + height)):
            start = (row * CARD_WIDTH + max(0, x)) * 3
            end = (row * CARD_WIDTH + min(CARD_WIDTH, x + width)) * 3
            if end > start:
                pixels[start:end] = bytes(colour) * ((end - start) // 3)

    def _text(
        self,
        pixels: bytearray,
        x: int,
        y: int,
        text: str,
        colour: tuple[int, int, int],
        scale: int = 3,
    ) -> None:
        cursor = x
        for character in text.upper():
            if character != " ":
                glyph = FONT.get(character, FONT[" "])
                for glyph_row in range(GLYPH_HEIGHT):
                    for glyph_column in range(GLYPH_WIDTH):
                        if glyph[glyph_row][glyph_column] == "#":
                            self._rect(
                                pixels,
                                cursor + glyph_column * scale,
                                y + glyph_row * scale,
                                scale,
                                scale,
                                colour,
                            )
            cursor += (GLYPH_WIDTH + 1) * scale


def _mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    present = [value for value in values if value is not None]
    if not present:
        return 0.0
    return sum(present) / len(present)


def _encode_png(width: int, height: int, pixels: bytearray) -> bytes:
    """Wrap raw RGB pixels in a minimal, single-IDAT PNG stream."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    stride = width * 3
    raw = bytearray()
    for row in range(height):
        raw.append(0)  # filter type 0 (None) for every scanline
        raw.extend(pixels[row * stride : (row + 1) * stride])

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit truecolor
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", header),
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            chunk(b"IEND", b""),
        ]
    )
