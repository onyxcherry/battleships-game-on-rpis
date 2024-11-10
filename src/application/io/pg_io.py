import pygame as pg
import janus
from enum import Enum
from typing import List, Tuple, Dict
from application.io.actions import InActions, OutActions, ActionEvent, DisplayBoard
from threading import Event as th_Event

class IO:

    BOARD_MARGIN = pg.math.Vector2(20,20)
    BOARD_DISPLAY_SIZE = pg.math.Vector2(400,400)
    TILE_BORDER = pg.math.Vector2(2,2)

    class ExtraColors(Enum):
        MAIN_BG = 1
        BOARD_BG = 2
        
        MARKER_CENTER = 3
        MARKER_AXIS = 4

        WATER = 5
        WAVING_MAST = 6
        AROUND_DESTROYED = 7


    def __init__(self, board_size : int, input_queue : janus.SyncQueue[ActionEvent], output_queue : janus.SyncQueue[ActionEvent], stop_running : th_Event):
        self._board_size = board_size
        self._in_queue = input_queue
        self._out_queue = output_queue
        self._stop_running = stop_running
        self._FPS = 60

        self._shots_pg_board : PgBoard = None
        self._ships_pg_board : PgBoard = None

        self._place_ships = False
        self._shooting = False

        self._ships_marker_pos : Tuple[int, int] = (0, 0)
        self._shots_marker_pos : Tuple[int, int] = (0, 0)

        self._color_map = {
            OutActions.UnknownShots : pg.Color('chartreuse4'),

            OutActions.HitShips : pg.Color('red'),
            OutActions.HitShots : pg.Color('red'),

            OutActions.DestroyedShips : pg.Color('red4'),
            OutActions.DestroyedShots : pg.Color('red4'),
            
            OutActions.MissShips : pg.Color('blueviolet'),
            OutActions.MissShots : pg.Color('blueviolet'),

            IO.ExtraColors.WATER : pg.Color('aqua'),
            OutActions.NoShip : pg.Color('aqua'),
            OutActions.Ship : pg.Color('gray20'),

            IO.ExtraColors.AROUND_DESTROYED : pg.Color('royalblue'),

            IO.ExtraColors.MAIN_BG : pg.Color('aquamarine'),
            IO.ExtraColors.BOARD_BG : pg.Color('azure4'),
            IO.ExtraColors.MARKER_CENTER : pg.Color('springgreen4'),
            IO.ExtraColors.MARKER_AXIS : pg.Color('springgreen')
        }
    
    def _try_put_in_queue(self, event : ActionEvent) -> None:
        try:
            self._in_queue.put_nowait(event)
        except janus.SyncQueueFull:
            print("out queue full!")
    
    def _handle_pg_marker_keydown(self, event : pg.event.Event) -> bool:
        if event.key == pg.K_SPACE:
            if self._shooting:
                self._try_put_in_queue(
                    ActionEvent(InActions.SelectShots, self._shots_marker_pos, DisplayBoard.Shots)
                    )
                return True
            elif self._place_ships:
                self._try_put_in_queue(
                    ActionEvent(InActions.SelectShips, self._ships_marker_pos, DisplayBoard.Ships)
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
                                self._shots_marker_pos[0] + marker_diff[1])
            new_marker_pos = (
                max(0, min(self._board_size-1, new_marker_pos[0])),
                max(0, min(self._board_size-1, new_marker_pos[1])))
            
            if new_marker_pos != self._shots_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.HoverShots, new_marker_pos, DisplayBoard.Shots)
                )
        
        elif self._place_ships:
            
            new_marker_pos = (self._ships_marker_pos[0] + marker_diff[0], 
                                self._ships_marker_pos[1] + marker_diff[1])
            new_marker_pos = (
                max(0, min(self._board_size-1, new_marker_pos[0])),
                max(0, min(self._board_size-1, new_marker_pos[1])))

            if new_marker_pos != self._ships_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.HoverShips, new_marker_pos, DisplayBoard.Ships)
                )
        
        return True
    
    def _handle_pg_input_event(self, event : pg.event.Event) -> None:
        if event.type == pg.MOUSEMOTION:
            pos=event.pos
            if self._shooting:
                tile : Tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                if tile == self._shots_marker_pos:
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.HoverShots, tile, DisplayBoard.Shots)
                )
            elif self._place_ships:
                tile : Tuple[int,int] = self._ships_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                if tile == self._ships_marker_pos:
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.HoverShips, tile, DisplayBoard.Ships)
                )
        
        elif event.type == pg.MOUSEBUTTONDOWN:
            pos=event.pos
            if self._shooting:
                tile : Tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.SelectShots, tile, DisplayBoard.Shots)
                )
            elif self._place_ships:
                tile : Tuple[int,int] = self._ships_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(
                    ActionEvent(InActions.SelectShips, tile, DisplayBoard.Ships)
                )
        
        elif event.type == pg.KEYDOWN:
            if self._handle_pg_marker_keydown(event): return
            if event.key == pg.K_f:
                self._try_put_in_queue(ActionEvent(InActions.FinishedPlacing))

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
            self._shots_pg_board.change_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_pg_board.change_cell(event.tile, color)


    def _draw(self) -> None:
        self._shots_pg_board.draw(self._shots_marker_pos if self._shooting else (-1, -1))
        self._ships_pg_board.draw(self._ships_marker_pos if not self._shooting else (-1, -1))
    
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

            self._screen.fill(self._color_map[IO.ExtraColors.MAIN_BG])
            self._draw()
            pg.display.flip()
            self._clock.tick(self._FPS)
    
    def run(self) -> None:
        pg.init()

        pg.display.set_caption("Battleships PC Client")
        self._screen : pg.Surface = pg.display.set_mode((2*IO.BOARD_MARGIN.x+IO.BOARD_DISPLAY_SIZE.x, 4*IO.BOARD_MARGIN.y+2*IO.BOARD_DISPLAY_SIZE.y))
        self._clock = pg.time.Clock()

        self._shots_pg_board = PgBoard(self._screen, IO.BOARD_MARGIN, self._board_size, self._color_map)
        self._ships_pg_board = PgBoard(self._screen, pg.math.Vector2(IO.BOARD_MARGIN.x, 3*IO.BOARD_MARGIN.y+IO.BOARD_DISPLAY_SIZE.y), self._board_size, self._color_map)

        self._game_loop()
        pg.quit()


class PgBoard:
    class PgTile:
        def __init__(self, rect : pg.Rect, color : pg.Color):
            self.rect = rect
            self.color = color

    def __init__(self, screen : pg.surface.Surface, pos : pg.math.Vector2, board_size : int, color_map : Dict[OutActions | IO.ExtraColors, pg.Color]):
        self._screen = screen
        self._rect = pg.Rect(pos, IO.BOARD_DISPLAY_SIZE + (IO.TILE_BORDER * 2))
        self._size = board_size
        self._tilesize = IO.BOARD_DISPLAY_SIZE / self._size
        self._color_map = color_map

        self._tiles : List[List[PgBoard.PgTile]] = []
        for y in range(self._size):
            row : List[PgBoard.PgTile] = []
            for x in range(self._size):
                rect = pg.Rect(
                    self._rect.topleft + (self._tilesize.elementwise() * pg.math.Vector2(x,y) + (IO.TILE_BORDER * 2)),
                    self._tilesize - (IO.TILE_BORDER * 2)
                )
                row.append(PgBoard.PgTile(rect, self._color_map[IO.ExtraColors.WATER]))
            self._tiles.append(row)
    
    def draw(self, marker : Tuple[int, int]) -> None:
        pg.draw.rect(self._screen, self._color_map[IO.ExtraColors.BOARD_BG], self._rect)
        for y in range(self._size):
            for x in range(self._size):
                pg_tile = self._tiles[y][x]
                draw_color : pg.Color = pg_tile.color
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = draw_color.lerp(self._color_map[IO.ExtraColors.MARKER_CENTER], 0.5)
                    elif row_match or col_match:
                        draw_color = draw_color.lerp(self._color_map[IO.ExtraColors.MARKER_AXIS], 0.5)
                pg.draw.rect(self._screen, draw_color, pg_tile.rect)

    def get_cell_from_mousecoords(self, pos : Tuple[int, int]) -> Tuple[int,int]:
        rel_pos = (pos[0] - self._rect.x, pos[1] - self._rect.y)
        cell = (int(rel_pos[0] // self._tilesize.x), int(rel_pos[1] // self._tilesize.y))

        if cell[0] < 0 or cell[0] >= self._size or cell[1] < 0 or cell[1] >= self._size:
            return (-1,-1)
        
        cell_off = (rel_pos[0] - self._tilesize.x * cell[0], rel_pos[1] - self._tilesize.y * cell[1])
    
        if cell_off[0] < IO.TILE_BORDER.x or cell_off[0] > self._tilesize.x - IO.TILE_BORDER.x \
            or cell_off[1] < IO.TILE_BORDER.y or cell_off[1] > self._tilesize.y - IO.TILE_BORDER.y:
            
            return (-1, -1)
        
        return cell

    def change_cell(self, pos : Tuple[int, int], color : pg.Color) -> None:
        self._tiles[pos[1]][pos[0]].color = color