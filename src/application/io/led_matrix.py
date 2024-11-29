import rpi_ws281x as ws
from typing import Tuple


class LED_Matrix(ws.PixelStrip):
    def __init__(
        self,
        num_cols: int,  # Number of matrix collumns
        num_rows: int,  # Number of matrix rows
        pin: int,  # GPIO pin connected to the pixels (must be PWM!)
        freq_hz: int = 800000,  # LED signal frequency in hertz (usually 800khz)
        dma: int = 10,  # DMA channel to use for generating a signal (try 10)
        invert: bool = False,  # True to invert the signal (when using NPN transistor level shift)
        brightness: int = 255,  # 0 - dark, 255 - full brightness
        channel: int = 0,  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        strip_type=None,  # set unusal LED strip type
        gamma=None,  # gamma correction
    ):
        super().__init__(
            num_cols * num_rows,
            pin,
            freq_hz,
            dma,
            invert,
            brightness,
            channel,
            strip_type,
            gamma,
        )

        self._num_cols = num_cols
        self._num_rows = num_rows

    def matrixToLEDPos(self, pos: Tuple[int, int]) -> int:
        pos = (self._num_cols - pos[0] - 1, pos[1])  # mirror X axis
        return (
            self._num_cols * pos[1]
            + (pos[1] % 2) * (self._num_cols - 1)
            - pos[0] * (2 * (pos[1] % 2) - 1)
        )

    def LEDToMatixPos(self, n: int) -> Tuple[int, int]:
        row = n // self._num_cols
        off = n % self._num_cols
        pos = (off * (1 - (row % 2)) + (self._num_cols - off - 1) * (row % 2), row)
        return (self._num_cols - pos[0] - 1, pos[1])  # mirror X axis

    def setMatrixPixelColor(self, pos: Tuple[int, int], color: ws.Color):
        self[self.matrixToLEDPos(pos)] = color

    def setMatrixPixelColorRGB(
        self, pos: Tuple[int, int], red: int, green: int, blue: int, white=0
    ):
        self.setMatrixPixelColor(pos, ws.Color(red, green, blue, white))

    def getMatrixPixelColor(self, pos: Tuple[int, int]) -> ws.Color:
        return self[self.matrixToLEDPos(pos)]

    def getMatrixPixelColorRGB(self, pos: Tuple[int, int]) -> ws.RGBW:
        return ws.RGBW(self[self.matrixToLEDPos(pos)])

    def clear(self, color: ws.Color = ws.Color(0, 0, 0)):
        self[:] = color
