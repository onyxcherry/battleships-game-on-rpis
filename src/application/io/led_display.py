from application.io.led_matrix import LED_Matrix
from rpi_ws281x import Color, RGBW
import janus
import enum
from typing import Final
from application.io.actions import OutActions, InfoActions, ActionEvent, DisplayBoard
from threading import Event
import time
from dataclasses import dataclass

class ExtraColors(enum.StrEnum):
    BoardBorderReady = "BoardBorderReady"
    BoardBorderNotReady = "BoardBorderNotReady"
    
    MarkerCenter = "MarkerCenter"
    MarkerAxis = "MarkerAxis"

    Water = "Water"
    AroundDestroyed = "AroundDestroyed"

@dataclass(frozen=True)
class LEDConfig:
    matrix_size : tuple[int, int]
    shots_matrix_pin : int
    ships_matrix_pin : int
    matrix_brightness : int
    blink_duration_ms : int
    color_map : dict[OutActions | ExtraColors, RGBW]

LED_CONFIG: Final = LEDConfig(
    matrix_size = (16, 16),
    shots_matrix_pin = 18,
    ships_matrix_pin = 13,
    matrix_brightness = 20,
    blink_duration_ms = 500,
    color_map = {
        OutActions.UnknownShots : Color(127,0,127),

        OutActions.HitShips : Color(127,0,0),
        OutActions.HitShots : Color(127,0,0),

        OutActions.DestroyedShips : Color(97,44,13),
        OutActions.DestroyedShots : Color(97,44,13),
        
        OutActions.MissShips : Color(130,66,214),
        OutActions.MissShots : Color(130,66,214),

        ExtraColors.Water : Color(4,15,15),
        OutActions.NoShip : Color(4,15,15),
        OutActions.Ship : Color(3,163,0),

        OutActions.BlinkShips : Color(127,0,0),

        ExtraColors.AroundDestroyed : Color(76,87,245),

        ExtraColors.MarkerCenter : Color(255,251,0),
        ExtraColors.MarkerAxis : Color(255,255,255),

        ExtraColors.BoardBorderReady : Color(0,0,255),
        ExtraColors.BoardBorderNotReady : Color(255,255,0)
    }
)

class Display:
    
    def __init__(self, output_queue : janus.SyncQueue[ActionEvent], stop_running : Event):
        self._board_size = -1
        self._out_queue = output_queue
        self._stop_running = stop_running

        self._shooting = False
        self._place_ships = False

        self._show_player_board = False
        self._show_opponent_board = False

        self._ships_marker_pos = (0, 0)
        self._shots_marker_pos = (-1, -1)

        self._shots_led_board : LED_Board = LED_Board(LED_CONFIG.shots_matrix_pin)
        time.sleep(0.5)
        self._ships_led_board : LED_Board = LED_Board(LED_CONFIG.ships_matrix_pin)
    
    def set_board_size(self, size : int):
        self._board_size = size
    
    def _init_boards(self) -> None:
        self._ships_led_board.set_size(self._board_size)
        self._shots_led_board.set_size(self._board_size)

        self._ships_led_board.set_mode(LED_Board.Mode.NORMAL)

    def _blink_event(self, event : ActionEvent) -> None:
        if not event.action in LED_CONFIG.color_map:
            return
        
        color = LED_CONFIG.color_map[event.action]

        if event.board == DisplayBoard.Shots:
            self._shots_led_board.blink_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_led_board.blink_cell(event.tile, color)
    
    def _color_event(self, event : ActionEvent) -> None:
        if not event.action in LED_CONFIG.color_map:
            return
        
        color = LED_CONFIG.color_map[event.action]

        if event.board == DisplayBoard.Shots:
            self._shots_led_board.change_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_led_board.change_cell(event.tile, color)

    def _handle_output_event(self, event : ActionEvent) -> None:

        match event.action:
            case InfoActions.PlayerConnected:
                self._show_player_board = True
                self._init_boards()
            
            case InfoActions.PlayerDisconnected:
                self._show_player_board = False

            case InfoActions.OpponentConnected:
                self._show_opponent_board = True
                self._shots_led_board.set_mode(LED_Board.Mode.NORMAL)
            
            case InfoActions.OpponentDisconnected:
                self._show_opponent_board = False
                self._shots_led_board.set_mode(LED_Board.Mode.DISCONNECTED)
            
            case InfoActions.OpponentReady:
                self._shots_led_board.set_ready(True)
            
            case InfoActions.PlayerWon:
                self._ships_led_board.set_mode(LED_Board.Mode.WON)

            case InfoActions.OpponentWon:
                self._shots_led_board.set_mode(LED_Board.Mode.LOST)

            case OutActions.PlaceShips:
                self._place_ships = True

            case OutActions.FinishedPlacing:
                self._place_ships = False
                self._ships_marker_pos = (-1,-1)
                self._ships_led_board.set_ready(True)
            
            case OutActions.PlayerTurn:
                self._shooting = True

            case OutActions.OpponentTurn:
                self._shooting = False
            
            case OutActions.HoverShots:
                self._shots_marker_pos = event.tile

            case OutActions.HoverShips:
                self._ships_marker_pos = event.tile
            
            case OutActions.BlinkShips:
                self._blink_event(event)

            case _:
                self._color_event(event)
    
    def run(self) -> None:
        while not self._stop_running.is_set():
            try:
                event = self._out_queue.get(timeout=0.1)
                self._handle_output_event(event)
            except janus.SyncQueueEmpty:
                pass
            finally:
                self._ships_led_board.draw(self._ships_marker_pos)
                self._shots_led_board.draw(self._shots_marker_pos if self._shooting else (-1, -1))
        self.clear()
    
    def clear(self) -> None:
        self._ships_led_board.clear()
        self._shots_led_board.clear()

class LED_Board:
    class Mode(enum.Enum):
        WAIT_FOR_CONNECT = 0
        NORMAL = 1
        DISCONNECTED = 2
        WON = 3
        LOST = 4
    
    class BlinkingTile:
        def __init__(self, x, y, color):
            self.x : int = x
            self.y : int = y
            self.color : RGBW = color

    def __init__(self, pin : int):
        self._size = -1
        self._mode : LED_Board.Mode = LED_Board.Mode.WAIT_FOR_CONNECT
        self._player_ready = False

        channel = 0
        if pin in (13, 19, 41, 45, 53):
            channel = 1

        self._led_matrix = LED_Matrix(
            num_cols=LED_CONFIG.matrix_size[0],
            num_rows=LED_CONFIG.matrix_size[1],
            pin=pin,
            brightness=LED_CONFIG.matrix_brightness,
            channel=channel
        )
        self._led_matrix.begin()
        self._led_matrix.clear()
        self._led_matrix.show()

    def clear(self) -> None:
        self._led_matrix.clear()
        self._led_matrix.show()
    
    def __del__(self) -> None:
        self.clear()
    
    def set_size(self, board_size : int) -> None:
        self._size = board_size
        self._tiles : list[list[RGBW]]= [
            [LED_CONFIG.color_map[ExtraColors.Water] for x in range(self._size)] 
            for y in range(self._size)
        ]
        self._blinking_tiles : dict[LED_Board.BlinkingTile, int] = dict()
        self._off = (int((16 - self._size) // 2), int((16 - self._size) // 2))
        self._draw_border()
        self.draw((-1,-1))
    
    def set_mode(self, mode : Mode) -> None:
        self._mode = mode

    def set_ready(self, ready : bool) -> None:
        self._player_ready = ready

    def _draw_border(self) -> None:
        if self._player_ready:
            color = LED_CONFIG.color_map[ExtraColors.BoardBorderReady]
        else:
            color = LED_CONFIG.color_map[ExtraColors.BoardBorderNotReady]

        for x in range(self._size + 2):
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] - 1), color)
            self._led_matrix.setMatrixPixelColor((x + self._off[0] - 1, self._off[1] + self._size), color)

        for y in range(self._size + 2):
            self._led_matrix.setMatrixPixelColor((self._off[0] - 1, y + self._off[1] - 1), color)
            self._led_matrix.setMatrixPixelColor((self._off[0] + self._size, y + self._off[1] - 1), color)
    
    def _lerp(c1 : RGBW, c2 : RGBW, p : float) -> RGBW:
        return Color(
            c1.r + int((c2.r - c1.r) * p),
            c1.g + int((c2.g - c1.g) * p),
            c1.b + int((c2.b - c1.b) * p),
            c1.w + int((c2.w - c1.w) * p)
        )
    
    
    def change_cell(self, pos : tuple[int, int], color : RGBW) -> None:
        self._tiles[pos[1]][pos[0]] = color
    
    def blink_cell(self, pos : tuple[int, int], color : RGBW) -> None:
        current_time = int(time.time() * 1000)
        self._blinking_tiles[LED_Board.BlinkingTile(pos[0],pos[1],color)] = current_time
    
    def _draw_wait_for_connect(self) -> None:
        self._led_matrix.clear(Color(0,0,127))

    def _draw_disconnected(self) -> None:
        self._led_matrix.clear(Color(127,0,0))

    def _draw_won(self) -> None:
        self._led_matrix.clear(Color(50,50,50))

    def _draw_lost(self) -> None:
        self._led_matrix.clear(Color(0,10,10))

    def _draw_normal(self, marker : tuple[int, int]) -> None:
        self._draw_border()
        for y in range(self._size):
            for x in range(self._size):
                draw_color : RGBW = self._tiles[y][x]
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = LED_Board._lerp(draw_color,LED_CONFIG.color_map[ExtraColors.MarkerCenter], 0.1)
                    elif row_match or col_match:
                        draw_color = LED_Board._lerp(draw_color,LED_CONFIG.color_map[ExtraColors.MarkerAxis], 0.1)
                self._led_matrix.setMatrixPixelColor((x + self._off[0], y + self._off[1]),draw_color)

        current_time = int(time.time() * 1000)
        self._blinking_tiles = {
            tile: start_time for tile, start_time in self._blinking_tiles.items() 
            if current_time - start_time < LED_CONFIG.blink_duration_ms
        }

        for tile in self._blinking_tiles:
            self._led_matrix.setMatrixPixelColor(
                (tile.x + self._off[0], tile.y + self._off[1]),
                tile.color
            )

    def draw(self, marker : tuple[int, int]) -> None:
        self._led_matrix.clear()
        match self._mode:
            case LED_Board.Mode.WAIT_FOR_CONNECT:
                self._draw_wait_for_connect()
            case LED_Board.Mode.NORMAL:
                self._draw_normal(marker)
            case LED_Board.Mode.DISCONNECTED:
                self._draw_disconnected()
            case LED_Board.Mode.WON:
                self._draw_won()
            case LED_Board.Mode.LOST:
                self._draw_lost()
        
        self._led_matrix.show()

    