from io.led_matrix import LED_Matrix
from rpi_ws281x import Color, RGBW
import queue
from enum import Enum
from typing import List, Tuple, Dict
from domain.actions import OutActions
from threading import Event

class Display:

    class ExtraColors(Enum):
        MARKER_CENTER = 1
        MARKER_AXIS = 2

        WATER = 3
        WAVING_MAST = 4
        AROUND_DESTROYED = 5

        BOARD_BORDER = 6
    
    def __init__(self, output_queue : queue.Queue, stop_running : Event):
        self._out_queue = output_queue
        self._stop_running = stop_running

        self._shooting = False

        self._shots_marker_pos = (0, 0)
        self._ships_marker_pos = (-1, -1)

        self._color_map = {
            OutActions.HitShips : Color(127,0,0),
            OutActions.HitShots : Color(127,0,0),

            OutActions.DestroyedShips : Color(97,44,13),
            OutActions.DestroyedShots : Color(97,44,13),
            
            OutActions.MissShips : Color(130,66,214),
            OutActions.MissShots : Color(130,66,214),

            Display.ExtraColors.WATER : Color(8,28,31),
            Display.ExtraColors.WAVING_MAST : Color(3,163,0),

            Display.ExtraColors.AROUND_DESTROYED : Color(76,87,245),

            Display.ExtraColors.MARKER_CENTER : Color(255,251,0),
            Display.ExtraColors.MARKER_AXIS : Color(255,255,255),

            Display.ExtraColors.BOARD_BORDER : Color(0,0,255)
        }

        self._shots_led_board : LED_Board = LED_Board(18, self._color_map)
        self._ships_led_board : LED_Board = LED_Board(13, self._color_map)
    
    def _handle_output_event(self, event) -> None:
        splitted = event.split(';')

        action = OutActions[splitted[0]]

        if action == OutActions.PlayerTurn:
            self._shooting = True
            return
        
        if action == OutActions.OpponentTurn:
            self._shooting = False
            return

        if action == OutActions.HoverShots:
            pos : Tuple[int, int] = eval(splitted[1])
            self._shots_marker_pos = pos
            return

        if action == OutActions.HoverShips:
            pos : Tuple[int, int] = eval(splitted[1])
            self._ships_marker_pos = pos
            return

        if not action in self._color_map:
            return
        
        pos : Tuple[int, int] = eval(splitted[1])
        color = self._color_map[action]

        if self._shooting:
            self._shots_led_board.change_cell(pos, color)
        else:
            self._ships_led_board.change_cell(pos, color)
    
    def run(self) -> None:
        while not self._stop_running.is_set():
            try:
                event = self._out_queue.get(timeout=1)
                self._handle_output_event(event)
                self._ships_led_board.draw(self._ships_marker_pos)
                self._shots_led_board.draw(self._shots_marker_pos)
            except queue.Empty:
                pass
        self.clear()
    
    def clear(self) -> None:
        self._ships_led_board.clear()
        self._shots_led_board.clear()

class LED_Board:
    def __init__(self, pin : int, color_map : Dict[OutActions | Display.ExtraColors, RGBW], size : Tuple[int,int] = (10, 10)):
        self._color_map = color_map
        self._size = size
        self._off = (int((16 - size[0]) // 2), int((16 - size[1]) // 2))
        self._tiles : List[List[RGBW]]= [[color_map[Display.ExtraColors.WATER] for x in range(size[0])] for y in range(size[1])]

        channel = 0
        if pin in (13, 19, 41, 45, 53):
            channel = 1

        self._led_matrix = LED_Matrix(num_cols=16,num_rows=16,pin=pin,brightness=20,channel=channel)
        self._led_matrix.begin()
        self._led_matrix.clear()
        self._draw_border()
        self.draw((-1,-1))
        self._led_matrix.show()

    def clear(self) -> None:
        self._led_matrix.clear()
        self._led_matrix.show()
    
    def __del__(self) -> None:
        self.clear()

    def _draw_border(self) -> None:
        for x in range(self._size[0] + 2):
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] + self._size[1]), self._color_map[Display.ExtraColors.BOARD_BORDER])

        for y in range(self._size[1] + 2):
            self._led_matrix.setMatrixPixelColor((self._off[0] - 1, y + self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
            self._led_matrix.setMatrixPixelColor((self._off[0] + self._size[0], y + self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
    
    def _lerp(c1 : RGBW, c2 : RGBW, p : float) -> RGBW:
        return Color(
            c1.r + int((c2.r - c1.r) * p),
            c1.g + int((c2.g - c1.g) * p),
            c1.b + int((c2.b - c1.b) * p),
            c1.w + int((c2.w - c1.w) * p)
        )
    
    
    def change_cell(self, pos : Tuple[int, int], color : RGBW) -> None:
        self._tiles[pos[1]][pos[0]] = color

    def draw(self, marker : Tuple[int, int]) -> None:
        for y in range(self._size[1]):
            for x in range(self._size[0]):
                draw_color : RGBW = self._tiles[y][x]
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = LED_Board._lerp(draw_color,self._color_map[Display.ExtraColors.MARKER_CENTER], 0.7)
                    elif row_match or col_match:
                        draw_color = LED_Board._lerp(draw_color,self._color_map[Display.ExtraColors.MARKER_AXIS], 0.7)
                self._led_matrix.setMatrixPixelColor((x + self._off[0], y + self._off[1]),draw_color)
        
        self._led_matrix.show()

    