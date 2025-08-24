import tkinter as tk
from typing import List, Tuple
import ast

# Tipos de objeto
POINT = "point"
LINE = "line"
WIREFRAME = "wireframe"  # polígono = wireframe

options_label = {
    POINT: "Ponto",
    LINE: "Linha",
    WIREFRAME: "Wireframe"
}

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
    def __init__(self, root, canvas_parent):
        self.canvas = tk.Canvas(canvas_parent, width=600, height=600, bg='white')
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
        
        # Desenhar pontos temporários para linhas e wireframes em construção
        if self.current_type in [WIREFRAME, LINE] and self.current_points:
            p_coords = [self.viewport.world_to_viewport(x, y) for (x, y) in self.current_points]

            for (px, py) in p_coords:
                self.canvas.create_oval(px-3, py-3, px+3, py+3, outline="red", fill="red")

            # Linhas de prévia entre os pontos já clicados para wireframes
            if len(p_coords) >= 2 and self.current_type == WIREFRAME:
                for i in range(len(p_coords) - 1):
                    x1, y1 = p_coords[i]
                    x2, y2 = p_coords[i + 1]
                    self.canvas.create_line(x1, y1, x2, y2, dash=(3, 3))

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
            self.add_object(options_label[POINT], POINT, self.current_points)
            self.current_points = []

        elif self.current_type == LINE and len(self.current_points) == 2:
            self.add_object(options_label[LINE], LINE, self.current_points)
            self.current_points = []

        self.redraw()

    def add_object(self, name, obj_type, coords):
        self.object_count += 1
        self.display.add(Object2D(f"{name}_{self.object_count}", obj_type, coords))

    def finalize_wireframe(self):
        if len(self.current_points) > 2:
            self.add_object(options_label[WIREFRAME], WIREFRAME, self.current_points)
        self.current_points = []
        self.redraw()

# =====================
# Interface
# =====================
def main():
    root = tk.Tk()
    root.title("Computação Gráfica - Sistema Gráfico Interativo")

    # Menu lateral (Frame) com as opções
    side_frame = tk.Frame(root, width=200)
    side_frame.pack(side=tk.LEFT, padx=4, fill=tk.Y)

    # Frame principal (Canvas)
    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    system = GraphicSystem(root, main_frame)

    # Label do menu de opções
    tk.Label(
        side_frame, text="Menu de Opções", font=("Arial", 14, "bold")
    ).pack(pady=10)

    # Menu de seleção do tipo de objeto
    type_var = tk.StringVar(value=options_label[POINT])
    type_menu = tk.OptionMenu(side_frame, type_var, *options_label.values())
    type_menu.pack(pady=5, fill=tk.X)

    def set_type(*args):
        label = type_var.get()
        for key, val in options_label.items():
            if val == label:
                system.current_type = key
                break
        system.current_points = []

    type_var.trace("w", set_type)

    # Botão para finalizar o wireframe
    btn_poly = tk.Button(side_frame, text="Finalizar Wireframe", command=system.finalize_wireframe)
    btn_poly.pack(pady=10, fill=tk.X)

    # Sub-menu (LabelFrame) com opções de movimentação e zoom da window contido no menu lateral
    window_frame = tk.LabelFrame(
        side_frame, text="Window", font=("Arial", 11, "bold"), labelanchor="n", padx=5, pady=5
    )
    window_frame.pack(fill=tk.X, padx=10, pady=10)

    nav_frame = tk.Frame(window_frame)
    nav_frame.pack(pady=5)

    btn_up = tk.Button(nav_frame, text="⭡", width=4, command=lambda: system.move(0, 10))
    btn_up.grid(row=0, column=1, padx=2, pady=2)

    btn_left = tk.Button(nav_frame, text="⭠", width=4, command=lambda: system.move(-10, 0))
    btn_left.grid(row=1, column=0, padx=2, pady=2)

    btn_right = tk.Button(nav_frame, text="⭢", width=4, command=lambda: system.move(10, 0))
    btn_right.grid(row=1, column=2, padx=2, pady=2)

    btn_down = tk.Button(nav_frame, text="⭣", width=4, command=lambda: system.move(0, -10))
    btn_down.grid(row=2, column=1, padx=2, pady=2)

    zoom_frame = tk.Frame(window_frame)
    zoom_frame.pack(pady=10)

    btn_zoom_in = tk.Button(zoom_frame, text="+", command=lambda: system.zoom(0.9))
    btn_zoom_in.pack(side=tk.LEFT, padx=5)

    btn_zoom_out = tk.Button(zoom_frame, text="-", command=lambda: system.zoom(1.1))
    btn_zoom_out.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()
