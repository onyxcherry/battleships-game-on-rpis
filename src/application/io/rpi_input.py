import janus
import gpiozero as gp
from typing import Tuple
from application.io.actions import InActions, ActionEvent
from threading import Event


class Rpi_Input:
    def __init__(self, input_queue: janus.SyncQueue[ActionEvent], stop_running: Event):
        self._board_size = -1
        self._input_queue = input_queue
        self._stop_running = stop_running
        self._active = False

        ## temp, will be replaced by joystick
        self._up_button = gp.Button(8, bounce_time=0.05)
        self._down_button = gp.Button(7, bounce_time=0.05)
        self._left_button = gp.Button(25, bounce_time=0.05)
        self._right_button = gp.Button(1, bounce_time=0.05)

        self._directions = {
            self._up_button: (0, -1),
            self._down_button: (0, 1),
            self._left_button: (-1, 0),
            self._right_button: (1, 0),
        }
        ##

        self._select_button = gp.Button(27, bounce_time=0.05)
        self._confirm_button = gp.Button(22, bounce_time=0.05)

        self._marker_pos: Tuple[int, int] = (0, 0)

    def set_board_size(self, size: int):
        self._board_size = size
        self._active = True
        print("joooooooo")

    def _marker_button_pressed(self, button) -> None:
        if not self._active:
            return
        direction = self._directions[button]

        self._marker_pos = (
            max(0, min(self._board_size - 1, self._marker_pos[0] + direction[0])),
            max(0, min(self._board_size - 1, self._marker_pos[1] + direction[1])),
        )
        # print(ActionEvent(InActions.Hover,self._marker_pos))

        self._input_queue.put(ActionEvent(InActions.Hover, self._marker_pos))

    def _select_button_pressed(self) -> None:
        if not self._active:
            return
        print(ActionEvent(InActions.Select, self._marker_pos))
        self._input_queue.put(ActionEvent(InActions.Select, self._marker_pos))

    def _confirm_button_pressed(self) -> None:
        if not self._active:
            return
        print(ActionEvent(InActions.Hover, self._marker_pos))
        self._input_queue.put(ActionEvent(InActions.Confirm))

    def run(self):
        self._up_button.when_pressed = self._marker_button_pressed
        self._down_button.when_pressed = self._marker_button_pressed
        self._left_button.when_pressed = self._marker_button_pressed
        self._right_button.when_pressed = self._marker_button_pressed

        self._select_button.when_pressed = self._select_button_pressed
        self._confirm_button.when_pressed = self._confirm_button_pressed

        self._stop_running.wait()
