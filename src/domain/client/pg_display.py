import pygame as pg
import queue
from enum import Enum
from typing import List, Tuple, Dict
from domain.field import AttackResult
from domain.actions import Actions


class Display:

    class ExtraColors(Enum):
        MAIN_BG = 1
        BOARD_BG = 2
        
        MARKER_CENTER = 3
        MARKER_AXIS = 4

        WATER = 5
        WAVING_MAST = 6
        AROUND_DESTROYED = 7


    def __init__(self, input_queue : queue.Queue, output_queue : queue.Queue):
        self._in_queue = input_queue
        self._out_queue = output_queue
        self._FPS = 60

        self._shots_pg_board : PgBoard = None
        self._ships_pg_board : PgBoard = None

        self._shooting = False

        self._shots_marker_pos = (0, 0)
        self._ships_marker_pos = (-1, -1)

        self._color_map = {
            Actions.HitShips : pg.Color('red4'),
            Actions.HitShots : pg.Color('red4'),

            Actions.DestroyedShips : pg.Color('saddlebrown'),
            Actions.DestroyedShots : pg.Color('saddlebrown'),
            
            Actions.MissShips : pg.Color('blueviolet'),
            Actions.MissShots : pg.Color('blueviolet'),

            Display.ExtraColors.WATER : pg.Color('aqua'),
            Display.ExtraColors.WAVING_MAST : pg.Color('gray20'),

            Display.ExtraColors.AROUND_DESTROYED : pg.Color('royalblue'),

            Display.ExtraColors.MAIN_BG : pg.Color('aquamarine'),
            Display.ExtraColors.BOARD_BG : pg.Color('azure4'),
            Display.ExtraColors.MARKER_CENTER : pg.Color('springgreen4'),
            Display.ExtraColors.MARKER_AXIS : pg.Color('springgreen')
        }
    
    def _handle_pg_event(self, event : pg.event.Event) -> None:
        if event.type == pg.MOUSEMOTION:
            pos=event.pos
            if self._shooting:
                tile : Tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                if tile == self._shots_marker_pos:
                    return
                try:
                    self._in_queue.put_nowait(f"{Actions.HoverShots};{tile}")
                except queue.Full:
                    print("out queue full!")
        
        elif event.type == pg.MOUSEBUTTONDOWN:
            pos=event.pos
            if self._shooting:
                tile : Tuple[int,int] = self._shots_pg_board.get_cell_from_mousecoords(pos)
                if tile == (-1, -1):
                    return
                try:
                    self._in_queue.put_nowait(f"{Actions.SelectShots};{tile}")
                except queue.Full:
                    print("out queue full!")
        
        elif event.type == pg.KEYDOWN:
            new_marker_pos = False

            if event.key == pg.K_w:
                new_marker_pos = (self._shots_marker_pos[0], self._shots_marker_pos[1] - 1)

            elif event.key == pg.K_s:
                new_marker_pos = (self._shots_marker_pos[0], self._shots_marker_pos[1] + 1)

            elif event.key == pg.K_a:
                new_marker_pos = (self._shots_marker_pos[0] - 1, self._shots_marker_pos[1])
                
            elif event.key == pg.K_d:
                new_marker_pos = (self._shots_marker_pos[0] + 1, self._shots_marker_pos[1])

            if new_marker_pos:
                new_marker_pos = (max(0, min(9, new_marker_pos[0])), max(0, min(9, new_marker_pos[1])))
                if new_marker_pos != self._shots_marker_pos:
                    try:
                        self._in_queue.put_nowait(f"{Actions.HoverShots};{(new_marker_pos)}")
                    except queue.Full:
                        print("out queue full!")

    def _handle_external_event(self, event : str) -> None:
        splitted = event.split(';')

        action = Actions[splitted[0]]

        if action == Actions.PlayerTurn:
            self._shooting = True
            return
        
        if action == Actions.OpponentTurn:
            self._shooting = False
            return

        if action == Actions.HoverShots:
            pos : Tuple[int, int] = eval(splitted[1])
            self._shots_marker_pos = pos
            return

        if action == Actions.HoverShips:
            pos : Tuple[int, int] = eval(splitted[1])
            self._ships_marker_pos = pos
            return

        if not action in self._color_map:
            return
        
        pos : Tuple[int, int] = eval(splitted[1])
        color = self._color_map[action]

        if self._shooting:
            self._shots_pg_board.change_cell(pos, color)
        else:
            self._ships_pg_board.change_cell(pos, color)


    def _draw(self) -> None:
        self._shots_pg_board.draw(self._shots_marker_pos if self._shooting else (-1, -1))
        self._ships_pg_board.draw(self._ships_marker_pos if not self._shooting else (-1, -1))
    
    def _game_loop(self) -> None:
        while self.running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                    break
                self._handle_pg_event(event)

            while True:
                try:
                    event = self._out_queue.get_nowait()
                    self._handle_external_event(event)
                except queue.Empty:
                    break

            self._screen.fill(self._color_map[Display.ExtraColors.MAIN_BG])
            self._draw()
            pg.display.flip()
            self._clock.tick(self._FPS)
    
    def run(self) -> None:
        pg.init()

        pg.display.set_caption("Battleships PC Client")
        self._screen : pg.Surface = pg.display.set_mode((440, 860))
        self._clock = pg.time.Clock()

        self._shots_pg_board = PgBoard(self._screen, pg.math.Vector2(20,20), pg.math.Vector2(404,404), self._color_map)
        self._ships_pg_board = PgBoard(self._screen, pg.math.Vector2(20,444), pg.math.Vector2(404,404), self._color_map)

        self.running = True

        self._game_loop()

        pg.quit()


class PgBoard:
    class PgTile:
        def __init__(self, rect : pg.Rect, color : pg.Color):
            self.rect = rect
            self.color = color

    def __init__(self, screen : pg.surface.Surface, pos : pg.math.Vector2, size : pg.math.Vector2, color_map : Dict[AttackResult | Display.ExtraColors, pg.Color], tile_border : pg.math.Vector2 = pg.math.Vector2(2)):
        self._screen = screen
        self._tileborder = tile_border
        self._rect = pg.Rect(pos.x, pos.y, size.x, size.y)
        self._tilesize = (size - 2 * self._tileborder) / 10
        self._color_map = color_map

        self._tiles : List[List[PgBoard.PgTile]] = []
        for y in range(10):
            row : List[PgBoard.PgTile] = []
            for x in range(10):
                rect = pg.Rect(
                    self._rect.x + self._tilesize.x * x + 2 * self._tileborder.x,
                    self._rect.y + self._tilesize.y * y + 2 * self._tileborder.y,
                    self._tilesize.x - 2 * self._tileborder.x,
                    self._tilesize.y - 2 * self._tileborder.y
                    )
                row.append(PgBoard.PgTile(rect, self._color_map[Display.ExtraColors.WATER]))
            self._tiles.append(row)
    
    def draw(self, marker : Tuple[int, int]) -> None:
        pg.draw.rect(self._screen, self._color_map[Display.ExtraColors.BOARD_BG], self._rect)
        for y in range(10):
            for x in range(10):
                pg_tile = self._tiles[y][x]
                draw_color : pg.Color = pg_tile.color
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = draw_color.lerp(self._color_map[Display.ExtraColors.MARKER_CENTER], 0.5)
                    elif row_match or col_match:
                        draw_color = draw_color.lerp(self._color_map[Display.ExtraColors.MARKER_AXIS], 0.5)
                pg.draw.rect(self._screen, draw_color, pg_tile.rect)

    def get_cell_from_mousecoords(self, pos : Tuple[int, int]) -> Tuple[int,int]:
        rel_pos = (pos[0] - self._rect.x, pos[1] - self._rect.y)
        cell = (int(rel_pos[0] // self._tilesize.x), int(rel_pos[1] // self._tilesize.y))

        if cell[0] < 0 or cell[0] > 9 or cell[1] < 0 or cell[1] > 9:
            return (-1,-1)
        
        cell_off = (rel_pos[0] - self._tilesize.x * cell[0], rel_pos[1] - self._tilesize.y * cell[1])
    
        if cell_off[0] < self._tileborder.x or cell_off[0] > self._tilesize.x - self._tileborder.x \
            or cell_off[1] < self._tileborder.y or cell_off[1] > self._tilesize.y - self._tileborder.y:
            
            return (-1, -1)
        
        return cell

    def change_cell(self, pos : Tuple[int, int], color : pg.Color) -> None:
        self._tiles[pos[1]][pos[0]].color = color