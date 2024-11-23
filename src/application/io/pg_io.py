import pygame as pg
import janus
import enum
from typing import Final
from application.io.actions import InActions, OutActions, ActionEvent, DisplayBoard
from threading import Event as th_Event
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict

class ExtraColors(enum.StrEnum):
    MainBg = "MainBg"
    BoardBg = "BoardBg"
    
    MarkerCenter = "MarkerCenter"
    MarkerAxis = "MarkerAxis"

    Water = "Water"
    WavingMast = "WavingMast"
    AroundDestroyed = "AroundDestroyed"

@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
class PgConfig:
    caption : str
    dest_fps : int
    board_margin : pg.math.Vector2
    board_display_size : pg.math.Vector2
    tile_border : pg.math.Vector2
    blink_duration_ms : int
    color_map : dict[OutActions | ExtraColors, pg.Color]

PG_CONFIG: Final = PgConfig(
    caption = "Battleships PC Client",
    dest_fps = 60,
    board_margin = pg.math.Vector2(20,20),
    board_display_size = pg.math.Vector2(400,400),
    tile_border = pg.math.Vector2(2,2),
    blink_duration_ms = 500,
    color_map = {
        OutActions.UnknownShots : pg.Color('chartreuse4'),

        OutActions.HitShips : pg.Color('red'),
        OutActions.HitShots : pg.Color('red'),

        OutActions.DestroyedShips : pg.Color('red4'),
        OutActions.DestroyedShots : pg.Color('red4'),
        
        OutActions.MissShips : pg.Color('blueviolet'),
        OutActions.MissShots : pg.Color('blueviolet'),

        ExtraColors.Water : pg.Color('aqua'),
        OutActions.NoShip : pg.Color('aqua'),
        OutActions.Ship : pg.Color('gray20'),

        OutActions.BlinkShips : pg.Color('red'),

        ExtraColors.AroundDestroyed : pg.Color('royalblue'),

        ExtraColors.MainBg : pg.Color('aquamarine'),
        ExtraColors.BoardBg : pg.Color('azure4'),
        ExtraColors.MarkerCenter : pg.Color('springgreen4'),
        ExtraColors.MarkerAxis : pg.Color('springgreen')
    }
)

class IO:

    def __init__(self, board_size : int, input_queue : janus.SyncQueue[ActionEvent], output_queue : janus.SyncQueue[ActionEvent], stop_running : th_Event):
        self._board_size = board_size
        self._in_queue = input_queue
        self._out_queue = output_queue
        self._stop_running = stop_running

        self._shots_pg_board : PgBoard = None
        self._ships_pg_board : PgBoard = None

        self._place_ships = False
        self._shooting = False

        self._ships_marker_pos : tuple[int, int] = (0, 0)
        self._shots_marker_pos : tuple[int, int] = (-1, -1)

        self._ships_internal_marker_pos : tuple[int, int] = (-1,-1)
        self._shots_internal_marker_pos : tuple[int, int] = (-1,-1)
    
    def _try_put_in_queue(self, event : ActionEvent) -> None:
        try:
            self._in_queue.put_nowait(event)
        except janus.SyncQueueFull:
            print("out queue full!")
    
    def _blink_event(self, event : ActionEvent) -> None:
        if not event.action in PG_CONFIG.color_map:
            return
                
        color = PG_CONFIG.color_map[event.action]
        if event.board == DisplayBoard.Shots:
            self._shots_pg_board.blink_tile(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_pg_board.blink_tile(event.tile, color)
    
    def _color_event(self, event : ActionEvent) -> None:
        if not event.action in PG_CONFIG.color_map:
            return
        
        color = PG_CONFIG.color_map[event.action]

        if event.board == DisplayBoard.Shots:
            self._shots_pg_board.change_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_pg_board.change_cell(event.tile, color)

    
    def _handle_pg_marker_keydown(self, event : pg.event.Event) -> bool:
        if event.key == pg.K_SPACE:
            if self._shooting:
                self._try_put_in_queue(
                    ActionEvent(InActions.Select, self._shots_marker_pos, DisplayBoard.Shots)
                    )
                return True
            elif self._place_ships:
                self._try_put_in_queue(
                    ActionEvent(InActions.Select, self._ships_marker_pos, DisplayBoard.Ships)
                    )
                return True


        marker_diff = (0,0)

        if event.key == pg.K_w:
            marker_diff = (0,-1)

        elif event.key == pg.K_s:
            marker_diff = (0,1)

        elif event.key == pg.K_a:
            marker_diff = (-1,0)
            
        elif event.key == pg.K_d:
            marker_diff = (1,0)
        
        if marker_diff == (0,0):
            return False
        
        if self._shooting:
            new_marker_pos = (self._shots_marker_pos[0] + marker_diff[0], 
                                self._shots_marker_pos[1] + marker_diff[1])
            new_marker_pos = (
                max(0, min(self._board_size-1, new_marker_pos[0])),
                max(0, min(self._board_size-1, new_marker_pos[1])))
            
            if new_marker_pos != self._shots_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, new_marker_pos, DisplayBoard.Shots)
                )
        
        elif self._place_ships:
            
            new_marker_pos = (self._ships_marker_pos[0] + marker_diff[0], 
                                self._ships_marker_pos[1] + marker_diff[1])
            new_marker_pos = (
                max(0, min(self._board_size-1, new_marker_pos[0])),
                max(0, min(self._board_size-1, new_marker_pos[1])))

            if new_marker_pos != self._ships_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, new_marker_pos, DisplayBoard.Ships)
                )
        
        return True
    
    def _handle_pg_input_event(self, event : pg.event.Event) -> None:
        if event.type == pg.MOUSEMOTION:
            pos=event.pos
            if self._shooting:
                tile : tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                if tile == self._shots_internal_marker_pos:
                    return
                self._shots_internal_marker_pos = tile
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, tile)
                )
            elif self._place_ships:
                tile : tuple[int,int] = self._ships_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                if tile == self._ships_internal_marker_pos:
                    return
                self._ships_internal_marker_pos = tile
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, tile)
                )
        
        elif event.type == pg.MOUSEBUTTONDOWN:
            pos=event.pos
            if self._shooting:
                tile : tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.Select, tile)
                )
            elif self._place_ships:
                tile : tuple[int,int] = self._ships_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.Select, tile)
                )
        
        elif event.type == pg.KEYDOWN:
            if self._handle_pg_marker_keydown(event): return
            if event.key == pg.K_f:
                self._try_put_in_queue(ActionEvent(InActions.Confirm))

    def _handle_output_event(self, event : ActionEvent) -> None:

        match event.action:
            case OutActions.PlaceShips:
                self._place_ships = True

            case OutActions.FinishedPlacing:
                self._place_ships = False
                self._ships_marker_pos = (-1,-1)

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


    def _draw(self) -> None:
        self._shots_pg_board.draw(self._shots_marker_pos if self._shooting else (-1,-1))
        self._ships_pg_board.draw(self._ships_marker_pos)
    
    def _game_loop(self) -> None:
        while not self._stop_running.is_set():
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self._stop_running.set()
                    break
                self._handle_pg_input_event(event)

            while True:
                try:
                    event = self._out_queue.get_nowait()
                    self._handle_output_event(event)
                except janus.SyncQueueEmpty:
                    break

            self._screen.fill(PG_CONFIG.color_map[ExtraColors.MainBg])
            self._draw()
            pg.display.flip()
            self._clock.tick(PG_CONFIG.dest_fps)
    
    def run(self) -> None:
        pg.init()

        pg.display.set_caption(PG_CONFIG.caption)
        self._screen = pg.display.set_mode((
            2 * PG_CONFIG.board_margin.x + PG_CONFIG.board_display_size.x,
            4 * PG_CONFIG.board_margin.y + 2 * PG_CONFIG.board_display_size.y
        ))
        self._clock = pg.time.Clock()

        self._shots_pg_board = PgBoard(self._screen, PG_CONFIG.board_margin, self._board_size)
        self._ships_pg_board = PgBoard(
            self._screen,
            pg.math.Vector2(
                PG_CONFIG.board_margin.x,
                3 * PG_CONFIG.board_margin.y + PG_CONFIG.board_display_size.y
            ),
            self._board_size
        )

        self._game_loop()
        pg.quit()


class PgBoard:
    class PgTile:
        def __init__(self, rect : pg.Rect, color : pg.Color):
            self.rect = rect
            self.color = color

    def __init__(self, screen : pg.surface.Surface, pos : pg.math.Vector2, board_size : int):
        self._screen = screen
        self._rect = pg.Rect(pos, PG_CONFIG.board_display_size + (PG_CONFIG.tile_border * 2))
        self._size = board_size
        self._tilesize = PG_CONFIG.board_display_size / self._size

        self._blinking_tiles : dict[PgBoard.PgTile, int] = dict()

        self._tiles : list[list[PgBoard.PgTile]] = []
        for y in range(self._size):
            row : list[PgBoard.PgTile] = []
            for x in range(self._size):
                rect = pg.Rect(
                    self._rect.topleft + (self._tilesize.elementwise() * pg.math.Vector2(x,y) + (PG_CONFIG.tile_border * 2)),
                    self._tilesize - (PG_CONFIG.tile_border * 2)
                )
                row.append(PgBoard.PgTile(rect, PG_CONFIG.color_map[ExtraColors.Water]))
            self._tiles.append(row)
    
    def draw(self, marker : tuple[int, int]) -> None:
        pg.draw.rect(self._screen, PG_CONFIG.color_map[ExtraColors.BoardBg], self._rect)
        for y in range(self._size):
            for x in range(self._size):
                pg_tile = self._tiles[y][x]
                draw_color : pg.Color = pg_tile.color
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = draw_color.lerp(PG_CONFIG.color_map[ExtraColors.MarkerCenter], 0.5)
                    elif row_match or col_match:
                        draw_color = draw_color.lerp(PG_CONFIG.color_map[ExtraColors.MarkerAxis], 0.5)
                pg.draw.rect(self._screen, draw_color, pg_tile.rect)
        
        current_time = pg.time.get_ticks()
        self._blinking_tiles = {
            pg_tile: time for pg_tile, time in self._blinking_tiles.items() if current_time - time < PG_CONFIG.blink_duration_ms
        }

        for pg_tile in self._blinking_tiles:
            pg.draw.rect(self._screen, pg_tile.color, pg_tile.rect)

    def get_cell_from_mousecoords(self, pos : tuple[int, int]) -> tuple[int,int]:
        rel_pos = (pos[0] - self._rect.x, pos[1] - self._rect.y)
        cell = (int(rel_pos[0] // self._tilesize.x), int(rel_pos[1] // self._tilesize.y))

        if cell[0] < 0 or cell[0] >= self._size or cell[1] < 0 or cell[1] >= self._size:
            return (-1,-1)
        
        cell_off = (rel_pos[0] - self._tilesize.x * cell[0], rel_pos[1] - self._tilesize.y * cell[1])
    
        if cell_off[0] < PG_CONFIG.tile_border.x or cell_off[0] > self._tilesize.x - PG_CONFIG.tile_border.x \
            or cell_off[1] < PG_CONFIG.tile_border.y or cell_off[1] > self._tilesize.y - PG_CONFIG.tile_border.y:
            
            return (-1, -1)
        
        return cell

    def change_cell(self, pos : tuple[int, int], color : pg.Color) -> None:
        self._tiles[pos[1]][pos[0]].color = color
    
    def blink_tile(self, pos : tuple[int, int], color : pg.Color) -> None:
        rect = self._tiles[pos[1]][pos[0]].rect
        tile = PgBoard.PgTile(rect,color)
        current_time = pg.time.get_ticks()
        self._blinking_tiles[tile] = current_time