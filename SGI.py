import tkinter as tk
from typing import List, Tuple
import ast

# Tipos de objeto
POINT = "point"
LINE = "line"
WIREFRAME = "wireframe"  # polígono = wireframe

# =====================
# Display File
# =====================
class Object2D:
    def __init__(self, name: str, obj_type: str, coordinates: List[Tuple[float, float]]):
        self.name = name
        self.obj_type = obj_type
        self.coordinates = coordinates

class DisplayFile:
    def __init__(self):
        self.objects = []

    def add(self, obj: Object2D):
        self.objects.append(obj)

# =====================
# Janela e Viewport
# =====================
class Window:
    def __init__(self, x_min=-100, x_max=100, y_min=-100, y_max=100):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def width(self):
        return self.x_max - self.x_min

    def height(self):
        return self.y_max - self.y_min

    def zoom(self, factor):
        cx = (self.x_max + self.x_min) / 2
        cy = (self.y_max + self.y_min) / 2
        w = self.width() * factor / 2
        h = self.height() * factor / 2
        self.x_min, self.x_max = cx - w, cx + w
        self.y_min, self.y_max = cy - h, cy + h

    def pan(self, dx, dy):
        self.x_min += dx
        self.x_max += dx
        self.y_min += dy
        self.y_max += dy

class Viewport:
    def __init__(self, canvas: tk.Canvas, window: Window):
        self.canvas = canvas
        self.window = window
    
    def world_to_viewport(self, x, y):
        vx = self.canvas.winfo_width()
        vy = self.canvas.winfo_height()

        wx, wy = self.window.width(), self.window.height()
        sx = vx / wx
        sy = vy / wy
        s = min(sx, sy)  # manter proporção

        offset_x = (vx - s * wx) / 2
        offset_y = (vy - s * wy) / 2

        px = (x - self.window.x_min) * s + offset_x
        py = (self.window.y_max - y) * s + offset_y

        return px, py

# =====================
# Sistema Gráfico
# =====================
class GraphicSystem:
    def __init__(self, root):
        self.canvas = tk.Canvas(root, width=600, height=600, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.display = DisplayFile()
        self.window = Window()
        self.viewport = Viewport(self.canvas, self.window)

        self.current_points = []  # pontos coletados via clique
        self.current_type = POINT
        self.object_count = 0

        # redesenhar ao redimensionar
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        # capturar cliques do mouse
        self.canvas.bind("<Button-1>", self.on_click)

        # navegação (pan/zoom)
        root.bind("<Up>", lambda e: self.move(0, 10))
        root.bind("<Down>", lambda e: self.move(0, -10))
        root.bind("<Left>", lambda e: self.move(-10, 0))
        root.bind("<Right>", lambda e: self.move(10, 0))
        root.bind("<plus>", lambda e: self.zoom(0.9))
        root.bind("<minus>", lambda e: self.zoom(1.1))

    def move(self, dx, dy):
        self.window.pan(dx, dy)
        self.redraw()

    def zoom(self, factor):
        self.window.zoom(factor)
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        for obj in self.display.objects:
            coords = [self.viewport.world_to_viewport(x, y) for (x, y) in obj.coordinates]

            if obj.obj_type == POINT:
                x, y = coords[0]
                self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="black")
            elif obj.obj_type == LINE:
                self.canvas.create_line(coords[0], coords[1])
            elif obj.obj_type == WIREFRAME:
                for i in range(len(coords)):
                    x1, y1 = coords[i]
                    x2, y2 = coords[(i + 1) % len(coords)]
                    self.canvas.create_line(x1, y1, x2, y2)

    def on_click(self, event):
        # converter clique para coordenadas do mundo
        vx, vy = event.x, event.y
        w = self.window.width()
        h = self.window.height()
        vx_size = self.canvas.winfo_width()
        vy_size = self.canvas.winfo_height()
        sx = vx_size / w
        sy = vy_size / h
        s = min(sx, sy)

        offset_x = (vx_size - s * w) / 2
        offset_y = (vy_size - s * h) / 2

        xw = (vx - offset_x) / s + self.window.x_min
        yw = self.window.y_max - (vy - offset_y) / s

        self.current_points.append((xw, yw))

        if self.current_type == POINT:
            self.add_object("Ponto", POINT, self.current_points)
            self.current_points = []

        elif self.current_type == LINE and len(self.current_points) == 2:
            self.add_object("Linha", LINE, self.current_points)
            self.current_points = []

        elif self.current_type == WIREFRAME:
            # vai acumulando até clicar no botão "Finalizar Wireframe"
            pass

        self.redraw()

    def add_object(self, name, obj_type, coords):
        self.object_count += 1
        self.display.add(Object2D(f"{name}_{self.object_count}", obj_type, coords))

    def finalize_wireframe(self):
        if len(self.current_points) > 2:
            self.add_object("Wireframe", WIREFRAME, self.current_points)
        self.current_points = []
        self.redraw()

# =====================
# Interface
# =====================
def main():
    root = tk.Tk()
    root.title("Computação Gráfica - Sistema Gráfico Interativo")

    system = GraphicSystem(root)

    frame = tk.Frame(root)
    frame.pack(side=tk.BOTTOM, fill=tk.X)

    type_var = tk.StringVar()
    type_menu = tk.OptionMenu(frame, type_var, POINT, LINE, WIREFRAME)
    type_var.set(POINT)
    type_menu.pack(side=tk.LEFT)

    def set_type(*args):
        system.current_type = type_var.get()
        system.current_points = []

    type_var.trace("w", set_type)

    btn_poly = tk.Button(frame, text="Finalizar Polígono", command=system.finalize_wireframe)
    btn_poly.pack(side=tk.LEFT)

    root.mainloop()

if __name__ == "__main__":
    main()
