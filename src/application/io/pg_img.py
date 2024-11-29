import importlib.resources as pkg_res
from application.io import resources
import pygame as pg

def load_surface(path : str) -> pg.Surface:
    with pkg_res.path(resources, path) as img_path:
        img = pg.image.load(img_path).convert_alpha()
    return img

class Animation():
    def __init__(self, img_path : str, frame_time_ms : int):
        self._img_path = img_path
        self._frame_time = frame_time_ms
    
    def load(self) -> None:
        self._sheet = load_surface(self._img_path)
        self._size = self._sheet.get_size()
        
        self._start_time = pg.time.get_ticks()
        self._frame_rect = pg.Rect(0,0,self._size[0], self._size[0])

        self._frames : list[pg.Rect] = []
        for i in range(self._size[1] // self._size[0]):
            rect = pg.Rect(0, i * self._size[0], self._size[0], self._size[0])
            frame = pg.Surface((self._size[0],self._size[0]), pg.SRCALPHA).convert_alpha()
            frame.blit(self._sheet, (0,0), rect)
            self._frames.append(frame)
    
    def get_current_frame(self) -> pg.Surface:
        time_diff = pg.time.get_ticks() - self._start_time
        frame_i = (time_diff // self._frame_time) % len(self._frames)
        return self._frames[frame_i]

if __name__ == "__main__":
    with pkg_res.path(resources, "gnome.png") as gnome_path:
        print(pg.image.load(gnome_path))