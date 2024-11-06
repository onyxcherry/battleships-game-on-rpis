import janus
import gpiozero as gp
from typing import Tuple
from application.io.actions import InActions
from threading import Event

class Rpi_Input:
    def __init__(self, board_size : int, input_queue : janus.SyncQueue[str], stop_running : Event):
        self._board_size = board_size
        self._input_queue = input_queue
        self._stop_running = stop_running

        ## temp, will be replaced by joystick
        self._up_button = gp.Button(1)
        self._down_button = gp.Button(7)
        self._left_button = gp.Button(8)
        self._right_button = gp.Button(25)

        self._directions = {
            self._up_button :    ( 0,-1),
            self._down_button :  ( 0, 1),
            self._left_button :  (-1, 0),
            self._right_button : ( 1, 0)
        }
        ##

        self._place_ships = False

        self._marker_pos : Tuple[int, int] = (0, 0)

    def _marker_button_pressed(self, button) -> None:
        direction = self._directions[button]

        self._shots_marker_pos = (
            max(0,min(self._board_size, self._shots_marker_pos[0] + direction[0])),
            max(0,min(self._board_size, self._shots_marker_pos[1] + direction[1])),
        )

        self._input_queue.put(f"{InActions.HoverShots};{self._shots_marker_pos}")

    def run(self):
        self._up_button.when_pressed = self._marker_button_pressed
        self._down_button.when_pressed = self._marker_button_pressed
        self._left_button.when_pressed = self._marker_button_pressed
        self._right_button.when_pressed = self._marker_button_pressed

        self._stop_running.wait()