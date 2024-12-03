import pygame as pg
import janus
import enum
from typing import Final, Optional
from application.io.actions import (
    InActions,
    OutActions,
    InfoActions,
    ActionEvent,
    DisplayBoard,
)
from application.io.pg_img import Animation
from threading import Event as th_Event
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict


class ExtraColors(enum.StrEnum):
    MainBg = "MainBg"
    BoardBgReady = "BoardBgReady"
    BoardBgNotReady = "BoardBgNotReady"

    MarkerCenter = "MarkerCenter"
    MarkerAxis = "MarkerAxis"

    Water = "Water"


@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
class PgConfig:
    caption: str
    dest_fps: int
    board_margin: pg.math.Vector2
    board_display_size: pg.math.Vector2
    tile_border: pg.math.Vector2
    blink_duration_ms: int
    color_map: dict[OutActions | ExtraColors, pg.Color]
    up_buttons: set[int]
    down_buttons: set[int]
    left_buttons: set[int]
    right_buttons: set[int]
    select_buttons: set[int]
    confirm_buttons: set[int]
    wait_for_connect_anim: Animation
    disconnected_anim: Animation
    won_anim: Animation
    lost_anim: Animation


PG_CONFIG: Final = PgConfig(
    caption="Battleships PC Client",
    dest_fps=60,
    board_margin=pg.math.Vector2(20, 20),
    board_display_size=pg.math.Vector2(400, 400),
    tile_border=pg.math.Vector2(2, 2),
    blink_duration_ms=500,
    color_map={
        OutActions.UnknownShots: pg.Color("chartreuse4"),
        OutActions.HitShips: pg.Color("red"),
        OutActions.HitShots: pg.Color("red"),
        OutActions.DestroyedShips: pg.Color("red4"),
        OutActions.DestroyedShots: pg.Color("red4"),
        OutActions.MissShips: pg.Color("blueviolet"),
        OutActions.MissShots: pg.Color("blueviolet"),
        ExtraColors.Water: pg.Color("aqua"),
        OutActions.NoShip: pg.Color("aqua"),
        OutActions.Ship: pg.Color("gray20"),
        OutActions.BlinkShips: pg.Color("red"),
        OutActions.AroundDestroyedShips: pg.Color("royalblue"),
        OutActions.AroundDestroyedShots: pg.Color("royalblue"),
        ExtraColors.MainBg: pg.Color("aquamarine"),
        ExtraColors.BoardBgReady: pg.Color("azure4"),
        ExtraColors.BoardBgNotReady: pg.Color("bisque4"),
        ExtraColors.MarkerCenter: pg.Color("springgreen4"),
        ExtraColors.MarkerAxis: pg.Color("springgreen"),
    },
    up_buttons={pg.K_w, pg.K_UP},
    down_buttons={pg.K_s, pg.K_DOWN},
    left_buttons={pg.K_a, pg.K_LEFT},
    right_buttons={pg.K_d, pg.K_RIGHT},
    select_buttons={pg.K_SPACE},
    confirm_buttons={pg.K_f},
    wait_for_connect_anim=Animation("ship.png", 350),
    disconnected_anim=Animation("gnome.png", 500),
    won_anim=Animation("trophy.png", 400),
    lost_anim=Animation("ship_sink.png", 350),
)


class IO:

    def __init__(
        self,
        input_queue: janus.SyncQueue[ActionEvent],
        output_queue: janus.SyncQueue[ActionEvent],
        stop_running: th_Event,
    ):
        self._board_size = -1
        self._in_queue = input_queue
        self._out_queue = output_queue
        self._stop_running = stop_running

        self._shots_pg_board: PgBoard = None
        self._ships_pg_board: PgBoard = None

        self._show_player_board = False
        self._show_opponent_board = False

        self._place_ships = False
        self._shooting = False

        self._ships_marker_pos: tuple[int, int] = (0, 0)
        self._shots_marker_pos: tuple[int, int] = (-1, -1)

        self._ships_internal_marker_pos: tuple[int, int] = (-1, -1)
        self._shots_internal_marker_pos: tuple[int, int] = (-1, -1)

    def set_board_size(self, size: int) -> None:
        self._board_size = size

    def _init_boards(self) -> None:
        self._ships_pg_board.set_size(self._board_size)
        self._shots_pg_board.set_size(self._board_size)

        self._ships_pg_board.set_mode(PgBoard.Mode.NORMAL)

    def _try_put_in_queue(self, event: ActionEvent) -> None:
        try:
            self._in_queue.put_nowait(event)
        except janus.SyncQueueFull:
            print("out queue full!")

    def _blink_event(self, event: ActionEvent) -> None:
        if not event.action in PG_CONFIG.color_map:
            return

        color = PG_CONFIG.color_map[event.action]
        if event.board == DisplayBoard.Shots:
            self._shots_pg_board.blink_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_pg_board.blink_cell(event.tile, color)
        elif event.board == DisplayBoard.ShipsBorder:
            self._ships_pg_board.blink_border(color)
        elif event.board == DisplayBoard.ShotsBorder:
            self._ships_pg_board.blink_border(color)

    def _color_event(self, event: ActionEvent) -> None:
        if not event.action in PG_CONFIG.color_map:
            return

        color = PG_CONFIG.color_map[event.action]

        if event.board == DisplayBoard.Shots:
            self._shots_pg_board.change_cell(event.tile, color)
        elif event.board == DisplayBoard.Ships:
            self._ships_pg_board.change_cell(event.tile, color)
            self._ships_marker_pos = (-1, -1)

    def _handle_pg_marker_keydown(self, event: pg.event.Event) -> bool:
        if event.key in PG_CONFIG.select_buttons:
            if self._shooting:
                self._try_put_in_queue(
                    ActionEvent(
                        InActions.Select, self._shots_marker_pos, DisplayBoard.Shots
                    )
                )
                return True
            elif self._place_ships:
                self._try_put_in_queue(
                    ActionEvent(
                        InActions.Select, self._ships_marker_pos, DisplayBoard.Ships
                    )
                )
                return True

        marker_diff = (0, 0)

        if event.key in PG_CONFIG.up_buttons:
            marker_diff = (0, -1)

        elif event.key in PG_CONFIG.down_buttons:
            marker_diff = (0, 1)

        elif event.key in PG_CONFIG.left_buttons:
            marker_diff = (-1, 0)

        elif event.key in PG_CONFIG.right_buttons:
            marker_diff = (1, 0)

        if marker_diff == (0, 0):
            return False

        if self._shooting:
            new_marker_pos = (
                self._shots_marker_pos[0] + marker_diff[0],
                self._shots_marker_pos[1] + marker_diff[1],
            )
            new_marker_pos = (
                max(0, min(self._board_size - 1, new_marker_pos[0])),
                max(0, min(self._board_size - 1, new_marker_pos[1])),
            )

            if new_marker_pos != self._shots_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, new_marker_pos, DisplayBoard.Shots)
                )

        elif self._place_ships:

            new_marker_pos = (
                self._ships_marker_pos[0] + marker_diff[0],
                self._ships_marker_pos[1] + marker_diff[1],
            )
            new_marker_pos = (
                max(0, min(self._board_size - 1, new_marker_pos[0])),
                max(0, min(self._board_size - 1, new_marker_pos[1])),
            )

            if new_marker_pos != self._ships_marker_pos:
                self._try_put_in_queue(
                    ActionEvent(InActions.Hover, new_marker_pos, DisplayBoard.Ships)
                )

        return True

    def _handle_pg_input_event(self, event: pg.event.Event) -> None:
        if not self._show_player_board:
            return

        if event.type == pg.MOUSEMOTION:
            pos = event.pos
            if self._shooting:
                tile: tuple[int, int] = self._shots_pg_board.get_cell_from_mousecoords(
                    pos
                )
                if tile == (-1, -1):
                    return
                if tile == self._shots_internal_marker_pos:
                    return
                self._shots_internal_marker_pos = tile
                self._try_put_in_queue(ActionEvent(InActions.Hover, tile))
            elif self._place_ships:
                tile: tuple[int, int] = self._ships_pg_board.get_cell_from_mousecoords(
                    pos
                )
                if tile == (-1, -1):
                    return
                if tile == self._ships_internal_marker_pos:
                    return
                self._ships_internal_marker_pos = tile
                self._try_put_in_queue(ActionEvent(InActions.Hover, tile))

        elif event.type == pg.MOUSEBUTTONDOWN:
            pos = event.pos
            if self._shooting:
                tile: tuple[int, int] = self._shots_pg_board.get_cell_from_mousecoords(
                    pos
                )
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(ActionEvent(InActions.Select, tile))
            elif self._place_ships:
                tile: tuple[int, int] = self._ships_pg_board.get_cell_from_mousecoords(
                    pos
                )
                if tile == (-1, -1):
                    return
                self._try_put_in_queue(ActionEvent(InActions.Select, tile))

        elif event.type == pg.KEYDOWN:
            if self._handle_pg_marker_keydown(event):
                return
            if event.key in PG_CONFIG.confirm_buttons:
                self._try_put_in_queue(ActionEvent(InActions.Confirm))

    def _handle_output_event(self, event: ActionEvent) -> None:

        match event.action:
            case InfoActions.PlayerConnected:
                self._show_player_board = True
                self._init_boards()

            case InfoActions.PlayerDisconnected:
                self._show_player_board = False

            case InfoActions.OpponentConnected:
                self._show_opponent_board = True
                self._shots_pg_board.set_mode(PgBoard.Mode.NORMAL)

            case InfoActions.OpponentDisconnected:
                self._show_opponent_board = False
                self._shots_pg_board.set_mode(PgBoard.Mode.DISCONNECTED)

            case InfoActions.OpponentReady:
                self._shots_pg_board.set_ready(True)

            case InfoActions.PlayerWon:
                self._ships_pg_board.set_mode(PgBoard.Mode.WON)

            case InfoActions.OpponentWon:
                self._shots_pg_board.set_mode(PgBoard.Mode.LOST)

            case OutActions.PlaceShips:
                self._place_ships = True

            case OutActions.FinishedPlacing:
                self._place_ships = False
                self._ships_marker_pos = (-1, -1)
                self._ships_pg_board.set_ready(True)

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
        self._shots_pg_board.draw(
            self._shots_marker_pos if self._shooting else (-1, -1)
        )
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
        self._screen = pg.display.set_mode(
            (
                2 * PG_CONFIG.board_margin.x + PG_CONFIG.board_display_size.x,
                4 * PG_CONFIG.board_margin.y + 2 * PG_CONFIG.board_display_size.y,
            )
        )
        self._clock = pg.time.Clock()

        PG_CONFIG.wait_for_connect_anim.load()
        PG_CONFIG.disconnected_anim.load()
        PG_CONFIG.won_anim.load()
        PG_CONFIG.lost_anim.load()

        self._shots_pg_board = PgBoard(self._screen, PG_CONFIG.board_margin)
        self._ships_pg_board = PgBoard(
            self._screen,
            pg.math.Vector2(
                PG_CONFIG.board_margin.x,
                3 * PG_CONFIG.board_margin.y + PG_CONFIG.board_display_size.y,
            ),
        )

        self._game_loop()
        pg.quit()


class PgBoard:
    class Mode(enum.Enum):
        WAIT_FOR_CONNECT = 0
        NORMAL = 1
        DISCONNECTED = 2
        WON = 3
        LOST = 4

    class PgTile:
        def __init__(self, rect: pg.Rect, color: pg.Color):
            self.rect = rect
            self.color = color

    def __init__(self, screen: pg.surface.Surface, pos: pg.math.Vector2):
        self._screen = screen
        self._rect = pg.Rect(
            pos, PG_CONFIG.board_display_size + (PG_CONFIG.tile_border * 2)
        )
        self._size = -1
        self._mode: PgBoard.Mode = PgBoard.Mode.WAIT_FOR_CONNECT
        self._player_ready = False

    def set_size(self, board_size: int) -> None:
        self._size = board_size
        self._tilesize = PG_CONFIG.board_display_size / self._size

        self._blinking_tiles: dict[PgBoard.PgTile, int] = dict()
        self._blinking_border: Optional[tuple[pg.Color, int]] = None

        self._tiles: list[list[PgBoard.PgTile]] = []
        for y in range(self._size):
            row: list[PgBoard.PgTile] = []
            for x in range(self._size):
                rect = pg.Rect(
                    self._rect.topleft
                    + (
                        self._tilesize.elementwise() * pg.math.Vector2(x, y)
                        + (PG_CONFIG.tile_border * 2)
                    ),
                    self._tilesize - (PG_CONFIG.tile_border * 2),
                )
                row.append(PgBoard.PgTile(rect, PG_CONFIG.color_map[ExtraColors.Water]))
            self._tiles.append(row)

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode

    def set_ready(self, ready: bool) -> None:
        self._player_ready = ready

    def _draw_wait_for_connect(self) -> None:
        img = PG_CONFIG.wait_for_connect_anim.get_current_frame()
        img = pg.transform.scale(img, self._rect.size)
        self._screen.blit(img, self._rect)

    def _draw_disconnected(self) -> None:
        img = PG_CONFIG.disconnected_anim.get_current_frame()
        img = pg.transform.scale(img, self._rect.size)
        self._screen.blit(img, self._rect)

    def _draw_won(self) -> None:
        img = PG_CONFIG.won_anim.get_current_frame()
        img = pg.transform.scale(img, self._rect.size)
        self._screen.blit(img, self._rect)

    def _draw_lost(self) -> None:
        img = PG_CONFIG.lost_anim.get_current_frame()
        img = pg.transform.scale(img, self._rect.size)
        self._screen.blit(img, self._rect)

    def _draw_normal(self, marker: tuple[int, int]) -> None:
        if self._blinking_border:
            pg.draw.rect(self._screen, self._blinking_border[0], self._rect)
        elif self._player_ready:
            pg.draw.rect(
                self._screen, PG_CONFIG.color_map[ExtraColors.BoardBgReady], self._rect
            )
        else:
            pg.draw.rect(
                self._screen,
                PG_CONFIG.color_map[ExtraColors.BoardBgNotReady],
                self._rect,
            )
        for y in range(self._size):
            for x in range(self._size):
                pg_tile = self._tiles[y][x]
                draw_color: pg.Color = pg_tile.color
                if marker != (-1, -1):
                    row_match = x == marker[0]
                    col_match = y == marker[1]
                    if row_match and col_match:
                        draw_color = draw_color.lerp(
                            PG_CONFIG.color_map[ExtraColors.MarkerCenter], 0.5
                        )
                    elif row_match or col_match:
                        draw_color = draw_color.lerp(
                            PG_CONFIG.color_map[ExtraColors.MarkerAxis], 0.5
                        )
                pg.draw.rect(self._screen, draw_color, pg_tile.rect)

        current_time = pg.time.get_ticks()
        self._blinking_tiles = {
            pg_tile: time
            for pg_tile, time in self._blinking_tiles.items()
            if current_time - time < PG_CONFIG.blink_duration_ms
        }

        if (
            self._blinking_border
            and current_time - self._blinking_border[1] >= PG_CONFIG.blink_duration_ms
        ):
            self._blinking_border = None

        for pg_tile in self._blinking_tiles:
            pg.draw.rect(self._screen, pg_tile.color, pg_tile.rect)

    def draw(self, marker: tuple[int, int] = (-1, -1)) -> None:
        match self._mode:
            case PgBoard.Mode.WAIT_FOR_CONNECT:
                self._draw_wait_for_connect()
            case PgBoard.Mode.NORMAL:
                self._draw_normal(marker)
            case PgBoard.Mode.DISCONNECTED:
                self._draw_disconnected()
            case PgBoard.Mode.WON:
                self._draw_won()
            case PgBoard.Mode.LOST:
                self._draw_lost()

    def get_cell_from_mousecoords(self, pos: tuple[int, int]) -> tuple[int, int]:
        rel_pos = (pos[0] - self._rect.x, pos[1] - self._rect.y)
        cell = (
            int(rel_pos[0] // self._tilesize.x),
            int(rel_pos[1] // self._tilesize.y),
        )

        if cell[0] < 0 or cell[0] >= self._size or cell[1] < 0 or cell[1] >= self._size:
            return (-1, -1)

        cell_off = (
            rel_pos[0] - self._tilesize.x * cell[0],
            rel_pos[1] - self._tilesize.y * cell[1],
        )

        if (
            cell_off[0] < PG_CONFIG.tile_border.x
            or cell_off[0] > self._tilesize.x - PG_CONFIG.tile_border.x
            or cell_off[1] < PG_CONFIG.tile_border.y
            or cell_off[1] > self._tilesize.y - PG_CONFIG.tile_border.y
        ):

            return (-1, -1)

        return cell

    def change_cell(self, pos: tuple[int, int], color: pg.Color) -> None:
        self._tiles[pos[1]][pos[0]].color = color

    def blink_cell(self, pos: tuple[int, int], color: pg.Color) -> None:
        rect = self._tiles[pos[1]][pos[0]].rect
        tile = PgBoard.PgTile(rect, color)
        current_time = pg.time.get_ticks()
        self._blinking_tiles[tile] = current_time

    def blink_border(self, color: pg.Color) -> None:
        current_time = pg.time.get_ticks()
        self._blinking_border = (color, current_time)
