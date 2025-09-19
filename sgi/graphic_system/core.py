import math
import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, filedialog

from .objects import Object2D, DisplayFile, POINT, LINE, WIREFRAME, options_label
from .transform import (
    apply_transform,
    make_translation,
    make_scale,
    make_rotation,
    centroid,
)
from .obj_descriptor import DescritorOBJ
from .clipping import cohen_sutherland, liang_barsky, sutherland_hodgman


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
        # aplica rotação da janela (como você já fazia)
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

        # variáveis para UI
        self.clip_var = tk.StringVar(value="CS")
        self.fill_var = tk.BooleanVar(value=False)

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

    def update_coords_label(self, obj: Object2D = None):
        if not hasattr(self, "coords_label") or self.coords_label is None:
            return
        if obj is None:
            self.coords_label.config(text="(nenhum objeto selecionado)")
            return
        coords_str = " ".join([f"({x:.2f},{y:.2f})" for x, y in obj.coordinates])
        self.coords_label.config(text=f"{obj.name}: {coords_str}")

    def redraw(self):
        self.canvas.delete("all")
        self.viewport.draw_frame(color="red")
        for obj in self.display.objects:
            coords = [
                self.viewport.world_to_viewport(x, y) for (x, y) in obj.coordinates
            ]

            if obj.obj_type == POINT:
                if not coords:
                    continue
                if self.clip_point(obj.coordinates[0][0], obj.coordinates[0][1]):
                    x, y = coords[0]
                    self.canvas.create_oval(
                        x - 3, y - 3, x + 3, y + 3, fill=obj.color, outline=obj.color
                    )

            elif obj.obj_type == LINE:
                if len(obj.coordinates) >= 2:
                    clipped = self.clip_line(obj.coordinates[0], obj.coordinates[1])
                    if clipped:
                        x1, y1, x2, y2 = clipped
                        c1 = self.viewport.world_to_viewport(x1, y1)
                        c2 = self.viewport.world_to_viewport(x2, y2)
                        self.canvas.create_line(c1, c2, fill=obj.color)

            elif obj.obj_type == WIREFRAME:
                if len(obj.coordinates) >= 3:
                    clipped_poly = self.clip_polygon(obj.coordinates)
                    if clipped_poly:
                        pv = [
                            self.viewport.world_to_viewport(x, y)
                            for (x, y) in clipped_poly
                        ]
                        if getattr(obj, "filled", False):
                            flat = []
                            for x, y in pv:
                                flat.extend([x, y])
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

        # Desenhar pontos temporários para linhas e wireframes em construção
        if self.current_type in [WIREFRAME, LINE] and self.current_points:
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
    def add_object(self, name, obj_type, coords, color="#000000", **kwargs):
        self.object_count += 1
        obj = Object2D(
            f"{name}_{self.object_count}",
            obj_type,
            coords.copy(),
            color=color,
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

    def scale_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
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
            cx, cy = centroid(obj.coordinates)
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
            cx, cy = centroid(obj.coordinates)
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

    def _rotate_point(self, x, y, angle_deg, cx, cy):
        ang = math.radians(angle_deg)
        cosA, sinA = math.cos(ang), math.sin(ang)
        xr = (x - cx) * cosA - (y - cy) * sinA + cx
        yr = (x - cx) * sinA + (y - cy) * cosA + cy
        return xr, yr

    def _inv_rotate_point(self, x, y, angle_deg, cx, cy):
        # inversa: ângulo negativo
        return self._rotate_point(x, y, -angle_deg, cx, cy)

    def _window_center(self):
        cx = (self.window.x_min + self.window.x_max) / 2.0
        cy = (self.window.y_min + self.window.y_max) / 2.0
        return cx, cy

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
