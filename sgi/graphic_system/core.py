import math
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

from .bezier_curve import bezier_curve, bezier_multisegment
from .bspline_fd import evaluate_bspline_fd
from .clipping import cohen_sutherland, liang_barsky, sutherland_hodgman, clip_point
from .obj_descriptor import DescritorOBJ
from .objects import (
    CURVE,
    LINE,
    POINT,
    WIREFRAME,
    DisplayFile,
    Object2D,
    Object3D,
    options_label,
)
from .point3d import Point3D
from .transform import (
    apply_transform,
    make_rotation,
    make_scale,
    make_translation,
)
from .window3d import Window3D


class Window:
    def __init__(self, x_min=-100, x_max=100, y_min=-100, y_max=100):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.rotation_angle = 0.0

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

    def rotate(self, angle_deg):
        self.rotation_angle = (self.rotation_angle + angle_deg) % 360


class Viewport:
    def __init__(self, canvas: tk.Canvas, window: Window):
        self.canvas = canvas
        self.window = window
        # retângulo fixo da viewport (margens): (10,10) até (largura-40, altura-30)
        self.px0 = 10
        self.py0 = 10
        self.px1 = 0  # será calculado
        self.py1 = 0  # será calculado

    def update_rect(self):
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)

        # retângulo FIXO da viewport (margens em px)
        self.px1 = max(w - 40, self.px0 + 1)
        self.py1 = max(h - 30, self.py0 + 1)

        # >>> CASAR ASPECTO DA WINDOW COM A VIEWPORT INTERNA <<<
        vx = max(self.px1 - self.px0, 1)
        vy = max(self.py1 - self.py0, 1)
        target_aspect = vx / vy

        wx = self.window.width()
        wy = self.window.height()
        if wx <= 0 or wy <= 0:
            return

        win_aspect = wx / wy
        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0

        if abs(win_aspect - target_aspect) < 1e-9:
            return  # já está ok

        if win_aspect > target_aspect:
            # window está "mais larga" do que a viewport -> aumentar altura (wy)
            new_wy = wx / target_aspect
            dh = (new_wy - wy) / 2.0
            self.window.y_min = cy - (wy / 2.0) - dh
            self.window.y_max = cy + (wy / 2.0) + dh
        else:
            # window está "mais alta" -> aumentar largura (wx)
            new_wx = wy * target_aspect
            dw = (new_wx - wx) / 2.0
            self.window.x_min = cx - (wx / 2.0) - dw
            self.window.x_max = cx + (wx / 2.0) + dw

    def _scale_and_offsets(self):
        vx = max(self.px1 - self.px0, 1)
        vy = max(self.py1 - self.py0, 1)
        wx = self.window.width()
        wy = self.window.height()
        sx = vx / wx
        sy = vy / wy
        s = min(sx, sy)
        offset_x = self.px0 + (vx - s * wx) / 2
        offset_y = self.py0 + (vy - s * wy) / 2
        return s, offset_x, offset_y

    def world_to_viewport(self, x, y):
        # aplica rotação da janela 
        cx = (self.window.x_min + self.window.x_max) / 2
        cy = (self.window.y_min + self.window.y_max) / 2
        ang = math.radians(self.window.rotation_angle)
        cosA, sinA = math.cos(ang), math.sin(ang)
        x_rel, y_rel = x - cx, y - cy
        xw = x_rel * cosA - y_rel * sinA + cx
        yw = x_rel * sinA + y_rel * cosA + cy

        s, ox, oy = self._scale_and_offsets()
        px = (xw - self.window.x_min) * s + ox
        py = (self.window.y_max - yw) * s + oy
        return px, py

    def viewport_to_world(self, px, py):
        s, ox, oy = self._scale_and_offsets()
        xw = (px - ox) / s + self.window.x_min
        yw = self.window.y_max - (py - oy) / s

        # desfaz a rotação
        cx = (self.window.x_min + self.window.x_max) / 2
        cy = (self.window.y_min + self.window.y_max) / 2
        ang = -math.radians(self.window.rotation_angle)
        cosA, sinA = math.cos(ang), math.sin(ang)
        x_rel, y_rel = xw - cx, yw - cy
        x = x_rel * cosA - y_rel * sinA + cx
        y = x_rel * sinA + y_rel * cosA + cy
        return x, y

    # linha para visualizar o clipping
    def draw_frame(self, color="red"):
        self.canvas.create_rectangle(
            self.px0, self.py0, self.px1, self.py1, outline=color, width=2
        )


class GraphicSystem:
    def __init__(self, root, canvas_parent):
        self.canvas = tk.Canvas(canvas_parent, width=800, height=600, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.display = DisplayFile()
        self.window = Window()
        self.viewport = Viewport(self.canvas, self.window)
        self.canvas.update_idletasks()  # mede o tamanho real do canvas
        self.viewport.update_rect()  # calcula (px0,py0)-(px1,py1)
        self.canvas.after(0, lambda: (self.viewport.update_rect(), self.redraw()))

        self.current_points = []  # pontos coletados via clique
        self.current_type = POINT
        self.object_count = 0
        self.default_color = "#000000"

        self.clipping_mode = "CS"  # ou "LB"
        self.curve_mode = "G0"  # ou "G1"

        # variáveis para UI
        self.clip_var = tk.StringVar(value="CS")
        self.fill_var = tk.BooleanVar(value=False)
        self.curve_mode_var = tk.StringVar(value="G0")

        # redesenhar ao redimensionar
        self.canvas.bind(
            "<Configure>", lambda e: (self.viewport.update_rect(), self.redraw())
        )
        # capturar cliques do mouse
        self.canvas.bind("<Button-1>", self.on_click)

        # navegação (pan/zoom)
        root.bind("<Up>", lambda e: self.move(0, 10))
        root.bind("<Down>", lambda e: self.move(0, -10))
        root.bind("<Left>", lambda e: self.move(-10, 0))
        root.bind("<Right>", lambda e: self.move(10, 0))
        root.bind("<plus>", lambda e: self.zoom(0.9))
        root.bind("<minus>", lambda e: self.zoom(1.1))

        # para integração com lista de objetos (será setado externamente)
        self.objects_listbox = None

        # zoom com scroll do mouse
        self.bind_mouse_scroll()

        # movimentar mundo com o botão direito do mouse
        self.bind_mouse_pan()

        self.camera = Window3D(vrp=(0, 0, 0), vpn=(0, 0, 1), vup=(0, 1, 0))

    def rotate_3d(
        self, yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0
    ):
        self.camera.rotate_camera(yaw_deg, pitch_deg, roll_deg)

    def create_cube_3d(self, name, initial_point, size):
        xw, yw = initial_point

        z = 0

        half = size / 2.0
        p = [
            Point3D(xw - half, yw - half, z - half),
            Point3D(xw + half, yw - half, z - half),
            Point3D(xw + half, yw + half, z - half),
            Point3D(xw - half, yw + half, z - half),
            Point3D(xw - half, yw - half, z + half),
            Point3D(xw + half, yw - half, z + half),
            Point3D(xw + half, yw + half, z + half),
            Point3D(xw - half, yw + half, z + half),
        ]

        edges = [
            (p[0], p[1]),
            (p[1], p[2]),
            (p[2], p[3]),
            (p[3], p[0]),
            (p[4], p[5]),
            (p[5], p[6]),
            (p[6], p[7]),
            (p[7], p[4]),
            (p[0], p[4]),
            (p[1], p[5]),
            (p[2], p[6]),
            (p[3], p[7]),
        ]

        cube = Object3D(name, edges, color=self.default_color)
        self.display.add(cube)
        self.redraw()
        self.refresh_listbox()

    def set_objects_listbox(self, listbox: tk.Listbox):
        self.objects_listbox = listbox
        self.refresh_listbox()
        self.objects_listbox.bind("<<ListboxSelect>>", self.on_object_selected)

    def on_object_selected(self, event):
        obj = self.get_selected_object()
        self.update_coords_label(obj)

    def refresh_listbox(self):
        if self.objects_listbox is None:
            return
        self.objects_listbox.delete(0, tk.END)
        for obj in self.display.objects:
            self.objects_listbox.insert(tk.END, obj.name)

    def set_clipping_mode(self, mode):
        self.clipping_mode = mode

    def set_curve_mode(self, mode):
        self.curve_mode = mode
        self.redraw()

    def clip_point(self, x, y):
        x_min, y_min, x_max, y_max = (
            self.window.x_min,
            self.window.y_min,
            self.window.x_max,
            self.window.y_max,
        )
        return x_min <= x <= x_max and y_min <= y <= y_max

    def clip_line(self, p1, p2):
        if self.clipping_mode == "CS":
            return cohen_sutherland(p1[0], p1[1], p2[0], p2[1], self.window)
        else:
            return liang_barsky(p1[0], p1[1], p2[0], p2[1], self.window)

    def clip_polygon(self, points):
        return sutherland_hodgman(points, self.window)

    def move(self, dx, dy):
        self.window.pan(dx, dy)
        self.redraw()

    def bind_mouse_pan(self):
        self.canvas.bind("<ButtonPress-3>", self.on_right_button_press)
        self.canvas.bind("<B3-Motion>", self.on_right_button_drag)

    def on_right_button_press(self, event):
        self.last_pan_x = event.x
        self.last_pan_y = event.y

    def on_right_button_drag(self, event):
        dx = event.x - self.last_pan_x
        dy = event.y - self.last_pan_y

        self.last_pan_x = event.x
        self.last_pan_y = event.y

        self.move(-dx, dy)

    def zoom(self, factor):
        self.window.zoom(factor)
        self.viewport.update_rect()
        self.redraw()

    def bind_mouse_scroll(self):
        # Windows e macOS
        self.canvas.bind("<MouseWheel>", self.on_mouse_scroll)
        # Linux
        self.canvas.bind("<Button-4>", lambda e: self.zoom(0.9))
        self.canvas.bind("<Button-5>", lambda e: self.zoom(1.1))

    def on_mouse_scroll(self, event):
        if event.delta > 0:
            self.zoom(0.9)
        else:
            self.zoom(1.1)

    def update_coords_label(self, obj: None):
        if not hasattr(self, "coords_label") or self.coords_label is None:
            return
        if obj is None:
            self.coords_label.config(text="(nenhum objeto selecionado)")
            return
        if isinstance(obj, Object3D):
            self.coords_label.config(text=f"{obj.name}: (objeto 3D)")
            return

        max_coords = 7
        coords_list = obj.coordinates[:max_coords]
        coords_str = " ".join([f"({x:.2f},{y:.2f})" for x, y in coords_list])
        if len(obj.coordinates) > max_coords:
            coords_str += " ..."
        self.coords_label.config(text=f"{obj.name}: {coords_str}")

    def redraw(self):
        self.canvas.delete("all")
        self.viewport.draw_frame(color="red")

        for obj in self.display.objects:
            # Objetos 3D
            if isinstance(obj, Object3D):
                projected_edges = obj.project(self.camera)
                for (x1, y1), (x2, y2) in projected_edges:
                    # clipping 2D para objetos 3D
                    self._draw_clipped_world_segment(x1, y1, x2, y2, obj.color)
                    # px1, py1 = self.viewport.world_to_viewport(x1, y1)
                    # px2, py2 = self.viewport.world_to_viewport(x2, y2)
                    # self.canvas.create_line(px1, py1, px2, py2, fill=obj.color)
                continue

            # Objetos 2D
            coords = [
                self.viewport.world_to_viewport(x, y) for (x, y) in obj.coordinates
            ]

            # PONTO
            if obj.obj_type == POINT:
                if obj.coordinates:
                    px, py = obj.coordinates[0]
                    inside = self._clip_point_world(px, py)
                    if inside:
                        x, y = self.viewport.world_to_viewport(px, py)
                        self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=obj.color, outline=obj.color)


            # RETA
            elif obj.obj_type == LINE:
                if len(obj.coordinates) >= 2:
                    x1, y1 = obj.coordinates[0]
                    x2, y2 = obj.coordinates[1]
                    self._draw_clipped_world_segment(x1, y1, x2, y2, obj.color)

            # POLÍGONO
            elif obj.obj_type == WIREFRAME:
                if len(obj.coordinates) >= 3:
                    clipped_poly = self._clip_polygon_world(obj.coordinates)
                    # pode acontecer de virar segmentinho/degenerado após clip
                    if clipped_poly and len(clipped_poly) >= 2:
                        pv = [self.viewport.world_to_viewport(x, y) for (x, y) in clipped_poly]
                        if getattr(obj, "filled", False) and len(pv) >= 3:
                            flat = [v for p in pv for v in p]
                            self.canvas.create_polygon(
                                *flat,
                                outline=obj.color,
                                fill=(obj.fill_color or obj.color),
                            )
                        else:
                            for i in range(len(pv)):
                                x1, y1 = pv[i]
                                x2, y2 = pv[(i + 1) % len(pv)]
                                self.canvas.create_line(x1, y1, x2, y2, fill=obj.color)

            elif obj.obj_type == CURVE:
                if len(obj.coordinates) >= 2:
                    mode = getattr(obj, "curve_mode", "G0")
                    if mode == "G0":
                        curve_pts = bezier_multisegment(
                            obj.coordinates, num_samples=200
                        )
                    elif mode == "G1":
                        curve_pts = bezier_curve(obj.coordinates, num_samples=200)
                    elif mode == "BS":
                        curve_pts = evaluate_bspline_fd(obj.coordinates, num_samples=50)
                    else:
                        curve_pts = []

                    for i in range(len(curve_pts) - 1):
                        x1, y1 = curve_pts[i]
                        x2, y2 = curve_pts[i + 1]
                        self._draw_clipped_world_segment(x1, y1, x2, y2, obj.color)

        # Desenhar pontos temporários para linhas e wireframes em construção
        if self.current_type in [WIREFRAME, LINE, CURVE] and self.current_points:
            p_coords = [
                self.viewport.world_to_viewport(x, y) for (x, y) in self.current_points
            ]

            for px, py in p_coords:
                self.canvas.create_oval(
                    px - 3, py - 3, px + 3, py + 3, outline="red", fill="red"
                )

            # Linhas de prévia entre os pontos já clicados para wireframes
            if len(p_coords) >= 2 and self.current_type == WIREFRAME:
                for i in range(len(p_coords) - 1):
                    x1, y1 = p_coords[i]
                    x2, y2 = p_coords[i + 1]
                    self.canvas.create_line(x1, y1, x2, y2, dash=(3, 3))

            # Prévia para curva de bézier ou B-Spline
            elif self.current_type == CURVE:
                if len(p_coords) >= 2:
                    for i in range(len(p_coords) - 1):
                        x1, y1 = p_coords[i]
                        x2, y2 = p_coords[i + 1]
                        self.canvas.create_line(
                            x1, y1, x2, y2, dash=(2, 4), fill="gray"
                        )

                if len(self.current_points) >= 3:
                    mode = getattr(self, "curve_mode", "G0")
                    if mode == "G0":
                        curve_pts = bezier_multisegment(
                            self.current_points, num_samples=100
                        )
                    elif mode == "G1":
                        curve_pts = bezier_curve(self.current_points, num_samples=100)
                    elif mode == "BS":
                        curve_pts = evaluate_bspline_fd(
                            self.current_points, num_samples=50
                        )
                    else:
                        curve_pts = []
                    v_coords = [
                        self.viewport.world_to_viewport(x, y) for (x, y) in curve_pts
                    ]
                    for i in range(len(v_coords) - 1):
                        x1, y1 = v_coords[i]
                        x2, y2 = v_coords[i + 1]
                        self.canvas.create_line(x1, y1, x2, y2, fill="blue")

    def on_click(self, event):
        # converter clique para coordenadas do mundo
        xw, yw = self.viewport.viewport_to_world(event.x, event.y)
        self.current_points.append((xw, yw))

        if self.current_type == POINT:
            self.add_object(
                options_label[POINT], POINT, self.current_points, self.default_color
            )
            self.current_points = []
        elif self.current_type == LINE and len(self.current_points) == 2:
            self.add_object(
                options_label[LINE], LINE, self.current_points, self.default_color
            )
            self.current_points = []

        self.redraw()

    # kwargs para não quebrar chamadas existentes
    def add_object(
        self, name, obj_type, coords, color="#000000", curve_mode="G0", **kwargs
    ):
        self.object_count += 1
        obj = Object2D(
            f"{name}_{self.object_count}",
            obj_type,
            coords.copy(),
            color=color,
            curve_mode=curve_mode,
            **kwargs,
        )
        self.display.add(obj)
        self.refresh_listbox()
        self.redraw()

    def finalize_wireframe(self):
        if len(self.current_points) > 2:
            filled = False
            fill_color = None
            try:
                filled = bool(self.fill_var.get())
            except Exception:
                pass  # se a UI ainda não fornece, mantém False
            if filled:
                fill_color = self.default_color  # ou outra cor de preenchimento

            self.add_object(
                options_label[WIREFRAME],
                WIREFRAME,
                self.current_points,
                color=self.default_color,
                filled=filled,
                fill_color=fill_color,
            )
        self.current_points = []
        self.redraw()

    def finalize_curve(self):
        if self.curve_mode == "BS" and len(self.current_points) < 4:
            messagebox.showerror(
                "Erro", "Curvas B-Spline precisam de pelo menos 4 pontos de controle."
            )
            self.current_points = []
            return
        if len(self.current_points) >= 2:
            self.add_object(
                options_label[CURVE],
                CURVE,
                self.current_points,
                self.default_color,
                curve_mode=self.curve_mode,
            )
        self.current_points = []
        self.redraw()

    def finalize_wireframe3d(self, name, points: list[tuple[float, float, float]]):
        if len(points) % 2 != 0:
            tk.messagebox.showerror(
                "Erro", "Número de pontos inválido. Cada aresta precisa de 2 pontos."
            )
            return

        edges = []
        for i in range(0, len(points), 2):
            p1 = Point3D(*points[i])
            p2 = Point3D(*points[i + 1])
            edges.append((p1, p2))

        self.object_count += 1
        obj3d = Object3D(f"{name}_{self.object_count}", edges, color=self.default_color)
        self.display.add(obj3d)
        self.refresh_listbox()
        self.redraw()

    # =====================
    # Operações sobre objeto selecionado
    # =====================
    def get_selected_object(self):
        if self.objects_listbox is None:
            return None
        sel = self.objects_listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx < 0 or idx >= len(self.display.objects):
            return None
        return self.display.objects[idx]

    def translate_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return

        if isinstance(obj, Object3D):
            self.translate_3d_selected(obj)
            self.redraw()
            self.refresh_listbox()
            return

        tx = simpledialog.askfloat("Translação", "tx:", parent=self.objects_listbox)
        if tx is None:
            return
        ty = simpledialog.askfloat("Translação", "ty:", parent=self.objects_listbox)
        if ty is None:
            return
        M = make_translation(tx, ty)
        apply_transform(M, obj)
        self.redraw()
        self.refresh_listbox()
        self.update_coords_label(obj)

    def translate_3d_selected(self, obj):
        tx = simpledialog.askfloat("Translação 3D", "tx:", parent=self.objects_listbox)
        if tx is None:
            return
        ty = simpledialog.askfloat("Translação 3D", "ty:", parent=self.objects_listbox)
        if ty is None:
            return
        tz = simpledialog.askfloat("Translação 3D", "tz:", parent=self.objects_listbox)
        if tz is None:
            return
        
        for p in obj._unique_points():     # evita transformar um vértice repetido
            p.translate(tx, ty, tz)

        self.redraw()
        self.refresh_listbox()

    def scale_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return

        if isinstance(obj, Object3D):
            self.scale_3d_selected(obj)
            self.redraw()
            self.refresh_listbox()
            return

        sx = simpledialog.askfloat("Escalonamento", "sx:", parent=self.objects_listbox)
        if sx is None:
            return

        sy_str = simpledialog.askstring(
            "Escalonamento",
            "sy (deixe vazio para usar sx):",
            parent=self.objects_listbox,
        )
        if sy_str is None:
            return
        elif sy_str.strip() == "":
            sy = None
        else:
            try:
                sy = float(sy_str)
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido para sy.")
                return

        if sy is None:
            sy = sx
        # centro: por padrão centro do objeto (escalonamento "natural")
        center_choice = messagebox.askyesno(
            "Centro",
            "Usar centro do objeto como centro do escalonamento?\n(Yes = centro do objeto, No = escolher ponto arbitrário)",
        )
        if center_choice:
            cx, cy = obj.centroid()
        else:
            cx = simpledialog.askfloat(
                "Centro arbitrário", "cx:", parent=self.objects_listbox
            )
            if cx is None:
                return
            cy = simpledialog.askfloat(
                "Centro arbitrário", "cy:", parent=self.objects_listbox
            )
            if cy is None:
                return
        M = make_scale(sx, sy, cx, cy)
        apply_transform(M, obj)
        self.redraw()
        self.refresh_listbox()
        self.update_coords_label(obj)

    def scale_3d_selected(self, obj):
        sx = simpledialog.askfloat(
            "Escalonamento 3D", "sx:", parent=self.objects_listbox
        )
        if sx is None:
            return

        sy_str = simpledialog.askstring(
            "Escalonamento 3D",
            "sy (deixe vazio para usar sx):",
            parent=self.objects_listbox,
        )
        if sy_str is None:
            return
        elif sy_str.strip() == "":
            sy = None
        else:
            try:
                sy = float(sy_str)
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido para sy.")
                return

        sz_str = simpledialog.askstring(
            "Escalonamento 3D",
            "sz (deixe vazio para usar sx):",
            parent=self.objects_listbox,
        )
        if sz_str is None:
            return
        elif sz_str.strip() == "":
            sz = None
        else:
            try:
                sz = float(sz_str)
            except ValueError:
                messagebox.showerror("Erro", "Valor inválido para sz.")
                return

        if sy is None:
            sy = sx
        if sz is None:
            sz = sx

        # centro: por padrão centro do objeto (escalonamento "natural")
        center_choice = messagebox.askyesno(
            "Centro",
            "Usar centro do objeto como centro do escalonamento?\n(Yes = centro do objeto, No = escolher ponto arbitrário)",
        )
        if center_choice:
            cx, cy, cz = obj.centroid()
        else:
            cx = simpledialog.askfloat(
                "Centro arbitrário", "cx:", parent=self.objects_listbox
            )
            if cx is None:
                return
            cy = simpledialog.askfloat(
                "Centro arbitrário", "cy:", parent=self.objects_listbox
            )
            if cy is None:
                return
            cz = simpledialog.askfloat(
                "Centro arbitrário", "cz:", parent=self.objects_listbox
            )
            if cz is None:
                return

        for p in obj._unique_points():     # evita escalonar vértice repetido
            p.scale(sx, sy, sz, cx, cy, cz)

        self.redraw()
        self.refresh_listbox()

    def choose_rotation_center(self, parent):
        result = {"choice": None}

        popup = tk.Toplevel(parent)
        popup.title("Centro de rotação")
        popup.grab_set()

        label = tk.Label(popup, text="Escolha o centro de rotação:")
        label.pack(padx=10, pady=10)

        def set_choice(choice):
            result["choice"] = choice
            popup.destroy()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Mundo", width=12, command=lambda: set_choice("mundo")
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame, text="Objeto", width=12, command=lambda: set_choice("objeto")
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame,
            text="Arbitrário",
            width=12,
            command=lambda: set_choice("arbitrario"),
        ).pack(side=tk.LEFT, padx=5)

        popup.wait_window()
        return result["choice"]

    def rotate_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return
        
        # Se Objeto 3D
        if isinstance(obj, Object3D):
            self.rotate_3d_selected(obj)
            return
        
        # Se Objeto 2D
        ang = simpledialog.askfloat(
            "Rotação",
            "Ângulo em graus (positivo: anti-horário):",
            parent=self.objects_listbox,
        )
        if ang is None:
            return
        
        # escolher centro: mundo, objeto, arbitrário
        choice = self.choose_rotation_center(self.objects_listbox)
        if choice is None:
            return
        choice = choice.strip().lower()

        if choice == "mundo":
            cx, cy = 0.0, 0.0
        elif choice == "objeto":
            cx, cy = obj.centroid()
        elif choice == "arbitrario":
            cx = simpledialog.askfloat(
                "Centro arbitrário", "cx:", parent=self.objects_listbox
            )
            if cx is None:
                return
            cy = simpledialog.askfloat(
                "Centro arbitrário", "cy:", parent=self.objects_listbox
            )
            if cy is None:
                return
        else:
            messagebox.showerror(
                "Erro", "Opção inválida. Use 'mundo', 'objeto' ou 'arbitrario'."
            )
            return
        
        M = make_rotation(ang, cx, cy)
        apply_transform(M, obj)
        self.redraw()
        self.refresh_listbox()
        self.update_coords_label(obj)

    def rotate_3d_selected(self, obj: Object3D):
        cfg = self._show_rotate3d_dialog(self.objects_listbox)
        if not cfg or not cfg.get("ok"):
            return

        ref = cfg["reference"]         # "world" | "object" | "arbitrary"
        axis = cfg["axis"]             # "x" | "y" | "z" | "arbitrary"
        ang  = cfg["angle"]
        center = cfg["center"]         # tuple ou None
        direction = cfg["direction"]   # tuple ou None

        # requer suporte no Object3D (rotate_about / rotate_axis)
        obj.rotate_about(reference=ref, axis=axis, angle_deg=ang,
                        center=center, direction=direction)

        self.redraw()
        self.refresh_listbox()

    def _show_rotate3d_dialog(self, parent):
        d = tk.Toplevel(parent)
        d.title("Rotacionar 3D")
        d.transient(parent.winfo_toplevel())
        d.grab_set()

        # ====== Referencial ======
        tk.Label(d, text="Referencial:").grid(row=0, column=0, sticky="w", padx=6, pady=(8,4))
        ref_var = tk.StringVar(value="world")
        ref_opts = [("Mundo", "world"), ("Objeto", "object"), ("Arbitrário", "arbitrary")]
        for i, (label, val) in enumerate(ref_opts, start=1):
            tk.Radiobutton(d, text=label, variable=ref_var, value=val).grid(row=0, column=i, sticky="w", padx=4, pady=(8,4))

        # ====== Eixo ======
        tk.Label(d, text="Eixo:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        axis_var = tk.StringVar(value="z")
        axis_opts = [("X", "x"), ("Y", "y"), ("Z", "z"), ("Arbitrário", "arbitrary")]
        for i, (label, val) in enumerate(axis_opts, start=1):
            tk.Radiobutton(d, text=label, variable=axis_var, value=val).grid(row=1, column=i, sticky="w", padx=4, pady=4)

        # ====== Ângulo ======
        tk.Label(d, text="Ângulo (graus):").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        entry_angle = tk.Entry(d, width=10)
        entry_angle.insert(0, "15")
        entry_angle.grid(row=2, column=1, sticky="w")

        # ====== Centro (só se referencial = arbitrário) ======
        center_row = 3
        lbl_center = tk.Label(d, text="Centro (x,y,z):")
        entry_center = tk.Entry(d, width=24)
        entry_center.insert(0, "0,0,0")

        # ====== Direção (só se eixo = arbitrário) ======
        dir_row = 4
        lbl_dir = tk.Label(d, text="Direção (dx,dy,dz):")
        entry_dir = tk.Entry(d, width=24)
        entry_dir.insert(0, "0,0,1")

        # ====== Botões ======
        btns = tk.Frame(d)
        btns.grid(row=5, column=0, columnspan=4, pady=8)
        result = {"ok": False, "reference": None, "axis": None, "angle": 0.0, "center": None, "direction": None}

        # ---- utilidades de layout dinâmico ----
        def show_center(show: bool):
            if show:
                lbl_center.grid(row=center_row, column=0, sticky="w", padx=6, pady=4)
                entry_center.grid(row=center_row, column=1, columnspan=3, sticky="w")
            else:
                lbl_center.grid_remove()
                entry_center.grid_remove()

        def show_direction(show: bool):
            if show:
                lbl_dir.grid(row=dir_row, column=0, sticky="w", padx=6, pady=4)
                entry_dir.grid(row=dir_row, column=1, columnspan=3, sticky="w")
            else:
                lbl_dir.grid_remove()
                entry_dir.grid_remove()

        def update_visibility(*_):
            show_center(ref_var.get() == "arbitrary")
            show_direction(axis_var.get() == "arbitrary")

        ref_var.trace_add("write", update_visibility)
        axis_var.trace_add("write", update_visibility)
        update_visibility()  # estado inicial

        def accept():
            # ângulo
            try:
                angle = float(entry_angle.get().strip())
            except Exception:
                messagebox.showerror("Erro", "Ângulo inválido.", parent=d)
                entry_angle.focus_set()
                return

            ref = ref_var.get()
            axis = axis_var.get()
            center = None
            direction = None

            # centro só quando referencial é arbitrário
            if ref == "arbitrary":
                try:
                    cx, cy, cz = map(float, entry_center.get().strip().split(","))
                    center = (cx, cy, cz)
                except Exception:
                    messagebox.showerror("Erro", "Centro inválido. Use x,y,z.", parent=d)
                    entry_center.focus_set()
                    return

            # direção só quando eixo é arbitrário
            if axis == "arbitrary":
                try:
                    dx, dy, dz = map(float, entry_dir.get().strip().split(","))
                    direction = (dx, dy, dz)
                except Exception:
                    messagebox.showerror("Erro", "Direção inválida. Use dx,dy,dz.", parent=d)
                    entry_dir.focus_set()
                    return

            result.update(ok=True, reference=ref, axis=axis, angle=angle, center=center, direction=direction)
            d.destroy()

        def cancel():
            d.destroy()

        tk.Button(btns, text="Cancelar", command=cancel).pack(side="left", padx=6)
        tk.Button(btns, text="Rotacionar", command=accept).pack(side="right", padx=6)

        # atalhos convenientes
        d.bind("<Return>", lambda *_: accept())
        d.bind("<Escape>", lambda *_: cancel())

        d.wait_window()
        return result

    def _window_center_3d(self):
        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0
        cz = 0.0
        return cx, cy, cz

    def set_default_color(self):
        c = colorchooser.askcolor(title="Escolher cor padrão")[1]
        if c:
            self.default_color = c

    def change_selected_color(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return
        c = colorchooser.askcolor(title=f"Cor para {obj.name}")[1]
        if not c:
            return
        obj.color = c

        if not isinstance(obj, Object3D):
            # se for polígono e estiver preenchido, atualiza também a cor de preenchimento
            if obj.obj_type == WIREFRAME and getattr(obj, "filled", False):
                obj.fill_color = c  # usa a mesma cor escolhida

        self.redraw()

    def delete_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return
        confirm = messagebox.askyesno("Confirmar", f"Remover {obj.name}?")
        if confirm:
            self.display.remove(obj)
            self.refresh_listbox()
            self.redraw()

    def save_as_obj(self, filename=None):
        if filename is None:
            filename = filedialog.asksaveasfilename(
                defaultextension=".obj",
                filetypes=[("Wavefront OBJ", "*.obj")],
                title="Salvar mundo como .obj",
            )
            if not filename:
                return

        lines = []
        offset = 1
        for obj in self.display.objects:
            obj_lines, offset = DescritorOBJ.export_object(obj, offset)
            lines.extend(obj_lines)

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def load_from_obj(self, filename=None):
        if filename is None:
            filename = filedialog.askopenfilename(
                defaultextension=".obj",
                filetypes=[("Wavefront OBJ", "*.obj")],
                title="Abrir mundo .obj",
            )
            if not filename:
                return

        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        objects = DescritorOBJ.import_objects(lines)

        for obj in objects:
            self.display.add(obj)

        self.refresh_listbox()
        self.redraw()

    # ---- Helpers para clipping correto com janela possivelmente rotacionada ----
    def _rotate_point(self, x, y, ang_deg, cx, cy):
        import math
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        xr, yr = x - cx, y - cy
        return (xr * ca - yr * sa + cx, xr * sa + yr * ca + cy)

    # Clipping para pontos 
    def _clip_point_world(self, x, y):
        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0
        ang = self.window.rotation_angle
        if abs(ang) > 1e-9:
            xr, yr = self._rotate_point(x, y, +ang, cx, cy)  # mesmo sentido
            res = clip_point(xr, yr, self.window)
            if res is None:
                return None
            wx, wy = self._rotate_point(res[0], res[1], -ang, cx, cy)
            return (wx, wy)
        else:
            res = clip_point(x, y, self.window)
        return (x, y) if res is not None else None


    # Clipping para retas respeitando as coordenadas de mundo e rotação de janela
    def _clip_line_world(self, p1, p2):
        # Centro da window (para rotacionar em torno dele)
        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0
        ang = self.window.rotation_angle

        # Des-rotaciona os pontos para alinhar com os eixos da janela
        if abs(ang) > 1e-9:
            q1 = self._rotate_point(p1[0], p1[1], +ang, cx, cy)
            q2 = self._rotate_point(p2[0], p2[1], +ang, cx, cy)
            # cria uma "cópia" rasa da janela (mesmos limites)
            class _TmpW: pass
            w = _TmpW()
            w.x_min, w.x_max = self.window.x_min, self.window.x_max
            w.y_min, w.y_max = self.window.y_min, self.window.y_max

            if self.clipping_mode == "CS":
                clipped = cohen_sutherland(q1[0], q1[1], q2[0], q2[1], w)
            else:
                clipped = liang_barsky(q1[0], q1[1], q2[0], q2[1], w)

            if not clipped:
                return None

            x1c, y1c, x2c, y2c = clipped
            # re-rotaciona de volta para o mundo
            r1 = self._rotate_point(x1c, y1c, -ang, cx, cy)
            r2 = self._rotate_point(x2c, y2c, -ang, cx, cy)
            return (r1[0], r1[1], r2[0], r2[1])
        else:
            # janela não-rotacionada: clipping direto
            if self.clipping_mode == "CS":
                return cohen_sutherland(p1[0], p1[1], p2[0], p2[1], self.window)
            else:
                return liang_barsky(p1[0], p1[1], p2[0], p2[1], self.window)
            
    # Clipping para polígonos/wireframes respeitando as coordenadas de mundo e rotação de janela
    def _clip_polygon_world(self, points):
        if not points:
            return []

        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0
        ang = self.window.rotation_angle

        # Se houver rotação: leva pro espaço alinhado à janela
        if abs(ang) > 1e-9:
            pts_local = [self._rotate_point(x, y, +ang, cx, cy) for (x, y) in points]

            class _TmpW: pass
            w = _TmpW()
            w.x_min, w.x_max = self.window.x_min, self.window.x_max
            w.y_min, w.y_max = self.window.y_min, self.window.y_max

            clipped_local = sutherland_hodgman(pts_local, w)
            if not clipped_local:
                return []

            # Volta pro mundo rotacionando de novo
            return [self._rotate_point(x, y, -ang, cx, cy) for (x, y) in clipped_local]

        # Sem rotação: pode usar a window direto
        return sutherland_hodgman(points, self.window) or []


    def _draw_clipped_world_segment(self, x1, y1, x2, y2, color):
        clipped = self._clip_line_world((x1, y1), (x2, y2))
        if not clipped:
            return
        cx1, cy1, cx2, cy2 = clipped
        v1 = self.viewport.world_to_viewport(cx1, cy1)
        v2 = self.viewport.world_to_viewport(cx2, cy2)
        self.canvas.create_line(v1, v2, fill=color)
    
