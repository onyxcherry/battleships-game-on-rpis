import queue
from threading import Event

try:   # distinguish pc and rpi by presence of pygame
    from . import pg_io
    print("Pygame IO")
    ON_PC = True

except ImportError:
    from . import led_display
    from . import rpi_input
    from threading import Thread
    print("RPI IO")
    ON_PC = False


class IO:
    def __init__(self, input_queue : queue.Queue, output_queue : queue.Queue, stop_running : Event):
        if ON_PC:
            self._io = pg_io.IO(input_queue, output_queue, stop_running)
        else:
            self._display = led_display.Display(output_queue, stop_running)
            self._input = rpi_input.Rpi_Input(input_queue, stop_running)

        self._stop_runing = stop_running
    
    def run(self):
        if ON_PC:
            self._io.run()
        else:
            input_t = Thread(target=self._input.run)
            input_t.start()
            self._display.run()
            input_t.join()
        print(" IO thread finished")
    
    def clear(self):
        if not ON_PC:
            self._display.clear()
