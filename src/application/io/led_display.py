from application.io.led_matrix import LED_Matrix
from rpi_ws281x import Color, RGBW
import janus
from enum import Enum
from typing import List, Tuple, Dict
from application.io.actions import OutActions, ActionEvent, DisplayBoard
from threading import Event
from time import sleep

class Display:

    class ExtraColors(Enum):
        MARKER_CENTER = 1
        MARKER_AXIS = 2

        WATER = 3
        AROUND_DESTROYED = 4

        BOARD_BORDER = 5
    
    def __init__(self, output_queue : janus.SyncQueue[ActionEvent], stop_running : Event):
        self._board_size = -1
        self._out_queue = output_queue
        self._stop_running = stop_running

        self._shooting = False
        self._place_ships = False

        self._shots_marker_pos = (0, 0)
        self._ships_marker_pos = (0, 0)

        self._color_map = {
            OutActions.UnknownShots : Color(127,0,127),

            OutActions.HitShips : Color(127,0,0),
            OutActions.HitShots : Color(127,0,0),

            OutActions.DestroyedShips : Color(97,44,13),
            OutActions.DestroyedShots : Color(97,44,13),
            
            OutActions.MissShips : Color(130,66,214),
            OutActions.MissShots : Color(130,66,214),

            Display.ExtraColors.WATER : Color(4,15,15),
            OutActions.NoShip : Color(4,15,15),
            OutActions.Ship : Color(3,163,0),

            Display.ExtraColors.AROUND_DESTROYED : Color(76,87,245),

            Display.ExtraColors.MARKER_CENTER : Color(255,251,0),
            Display.ExtraColors.MARKER_AXIS : Color(255,255,255),

            Display.ExtraColors.BOARD_BORDER : Color(0,0,255)
        }

        self._shots_led_board : LED_Board = LED_Board(18, self._color_map, self._board_size)
        sleep(0.5)
        self._ships_led_board : LED_Board = LED_Board(13, self._color_map, self._board_size)
    
    def set_board_size(self, size : int):
        self._board_size = size
    
    def _handle_output_event(self, event : ActionEvent) -> None:
        if event.action == OutActions.PlaceShips:
            self._place_ships = True
            return
        
        if event.action == OutActions.FinishedPlacing:
            self._place_ships = False
            self._ships_marker_pos = (-1,-1)
            return

        if event.action == OutActions.PlayerTurn:
            self._shooting = True
            return
        
        if event.action == OutActions.OpponentTurn:
            self._shooting = False
            return

        if event.action == OutActions.HoverShots:
            self._shots_marker_pos = event.tile
            return

        if event.action == OutActions.HoverShips:
            self._ships_marker_pos = event.tile
            return

        if not event.action in self._color_map:
            return
        
        color = self._color_map[event.action]

        if event.board == DisplayBoard.Shots:
            self._shots_led_board.change_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_led_board.change_cell(event.tile, color)
    
    def run(self) -> None:
        while not self._stop_running.is_set():
            try:
                event = self._out_queue.get(timeout=1)
                self._handle_output_event(event)
                self._ships_led_board.draw(self._ships_marker_pos if not self._shooting else (-1, -1))
                self._shots_led_board.draw(self._shots_marker_pos if self._shooting else (-1, -1))
            except janus.SyncQueueEmpty:
                pass
        self.clear()
    
    def clear(self) -> None:
        self._ships_led_board.clear()
        self._shots_led_board.clear()

class LED_Board:
    def __init__(self, pin : int, color_map : Dict[OutActions | Display.ExtraColors, RGBW], size : int):
        self._color_map = color_map
        self._size = size
        self._off = (int((16 - size) // 2), int((16 - size) // 2))
        self._tiles : List[List[RGBW]]= [[color_map[Display.ExtraColors.WATER] for x in range(size)] for y in range(size)]

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
        for x in range(self._size + 2):
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] + self._size), self._color_map[Display.ExtraColors.BOARD_BORDER])

        for y in range(self._size + 2):
            self._led_matrix.setMatrixPixelColor((self._off[0] - 1, y + self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
            self._led_matrix.setMatrixPixelColor((self._off[0] + self._size, y + self._off[1] - 1), self._color_map[Display.ExtraColors.BOARD_BORDER])
    
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
        for y in range(self._size):
            for x in range(self._size):
                draw_color : RGBW = self._tiles[y][x]
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = LED_Board._lerp(draw_color,self._color_map[Display.ExtraColors.MARKER_CENTER], 0.1)
                    elif row_match or col_match:
                        draw_color = LED_Board._lerp(draw_color,self._color_map[Display.ExtraColors.MARKER_AXIS], 0.1)
                self._led_matrix.setMatrixPixelColor((x + self._off[0], y + self._off[1]),draw_color)
        
        self._led_matrix.show()

    