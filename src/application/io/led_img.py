import importlib.resources as pkg_res
from application.io import resources
from PIL import Image
import rpi_ws281x as ws
import time


class Animation:
    def __init__(self, img_path: str, frame_time_ms: int):
        self._img_path = img_path
        self._frame_time = frame_time_ms
        self._frames: list[list[ws.RGBW]] = []
        self._start_time = 0

    def load(self, w: int, h: int) -> None:
        with pkg_res.path(resources, self._img_path) as img_path:
            img = Image.open(img_path)
        pixels = img.load()
        for frame_n in range(img.size[1] // h):
            frame: list[ws.RGBW] = []
            for y in range(h):
                ran = range(0, w, 1) if y % 2 else range(w - 1, -1, -1)
                for x in ran:
                    y_coord = y + frame_n * h
                    frame.append(ws.Color(*pixels[x, y_coord]))
            self._frames.append(frame)
        self._start_time = int(time.time() * 1000)

    def get_current_frame(self) -> list[ws.RGBW]:
        time_diff = int(time.time() * 1000) - self._start_time
        frame_i = (time_diff // self._frame_time) % len(self._frames)
        return self._frames[frame_i]
