import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox, filedialog
from typing import List, Tuple
import math

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
# Display File / Objetos
# =====================
class Object2D:
    def __init__(self, name: str, obj_type: str, coordinates: List[Tuple[float, float]], color: str = "#000000"):
        self.name = name
        self.obj_type = obj_type
        self.coordinates = coordinates  # lista de tuples (x,y)
        self.color = color  # cor de contorno (RGBf hex)

class DisplayFile:
    def __init__(self):
        self.objects: List[Object2D] = []

    def add(self, obj: Object2D):
        self.objects.append(obj)

    def remove(self, obj: Object2D):
        self.objects.remove(obj)

# =====================
# Janela e Viewport
# =====================
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
    
    def world_to_viewport(self, x, y):
        vx = self.canvas.winfo_width()
        vy = self.canvas.winfo_height()

        cx = (self.window.x_min + self.window.x_max) / 2
        cy = (self.window.y_min + self.window.y_max) / 2
        ang = math.radians(self.window.rotation_angle)
        cosA, sinA = math.cos(ang), math.sin(ang)

        x_rel, y_rel = x - cx, y - cy
        x_rot = x_rel * cosA - y_rel * sinA
        y_rot = x_rel * sinA + y_rel * cosA
        x, y = x_rot + cx, y_rot + cy

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
# Matrizes e transformações homogêneas (3x3)
# =====================
def mat_mult(A, B):
    """Multiplica duas matrizes 3x3 A*B"""
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]

def apply_transform(matrix, obj: Object2D):
    """Aplica matrix (3x3) a todas as coordenadas do objeto, alterando-o in-place."""
    new_coords = []
    for (x, y) in obj.coordinates:
        vx = matrix[0][0]*x + matrix[0][1]*y + matrix[0][2]*1
        vy = matrix[1][0]*x + matrix[1][1]*y + matrix[1][2]*1
        vz = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]*1
        if vz != 0:
            new_coords.append((vx/vz, vy/vz))
        else:
            new_coords.append((vx, vy))
    obj.coordinates = new_coords

def make_translation(tx, ty):
    return [
        [1, 0, tx],
        [0, 1, ty],
        [0, 0, 1]
    ]

def make_scale(sx, sy, cx=0, cy=0):
    # translate(-c) * scale * translate(c)
    t1 = make_translation(-cx, -cy)
    s = [
        [sx, 0, 0],
        [0, sy, 0],
        [0, 0, 1]
    ]
    t2 = make_translation(cx, cy)
    return mat_mult(t2, mat_mult(s, t1))

def make_rotation(angle_deg, cx=0, cy=0):
    a = math.radians(angle_deg)
    cosA = math.cos(a)
    sinA = math.sin(a)
    r = [
        [cosA, -sinA, 0],
        [sinA, cosA, 0],
        [0, 0, 1]
    ]
    t1 = make_translation(-cx, -cy)
    t2 = make_translation(cx, cy)
    return mat_mult(t2, mat_mult(r, t1))

def centroid(coords: List[Tuple[float,float]]):
    if not coords:
        return 0.0, 0.0
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return sum(xs)/len(xs), sum(ys)/len(ys)

# =====================
# Sistema Gráfico
# =====================
class GraphicSystem:
    def __init__(self, root, canvas_parent):
        self.canvas = tk.Canvas(canvas_parent, width=800, height=600, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.display = DisplayFile()
        self.window = Window()
        self.viewport = Viewport(self.canvas, self.window)

        self.current_points = []  # pontos coletados via clique
        self.current_type = POINT
        self.object_count = 0
        self.default_color = "#000000"

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
        for obj in self.display.objects:
            coords = [self.viewport.world_to_viewport(x, y) for (x, y) in obj.coordinates]

            if obj.obj_type == POINT:
                if not coords:
                    continue
                x, y = coords[0]
                self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=obj.color, outline=obj.color)
            elif obj.obj_type == LINE:
                if len(coords) >= 2:
                    self.canvas.create_line(coords[0], coords[1], fill=obj.color)
            elif obj.obj_type == WIREFRAME:
                if len(coords) >= 2:
                    for i in range(len(coords)):
                        x1, y1 = coords[i]
                        x2, y2 = coords[(i + 1) % len(coords)]
                        self.canvas.create_line(x1, y1, x2, y2, fill=obj.color)

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

        cx = (self.window.x_min + self.window.x_max) / 2
        cy = (self.window.y_min + self.window.y_max) / 2
        ang = math.radians(self.window.rotation_angle)
        cosA, sinA = math.cos(ang), math.sin(ang)

        x_rel, y_rel = xw - cx, yw - cy
        x_rot = x_rel * cosA + y_rel * sinA
        y_rot = -x_rel * sinA + y_rel * cosA
        xw, yw = x_rot + cx, y_rot + cy

        self.current_points.append((xw, yw))

        if self.current_type == POINT:
            self.add_object(options_label[POINT], POINT, self.current_points, self.default_color)
            self.current_points = []

        elif self.current_type == LINE and len(self.current_points) == 2:
            self.add_object(options_label[LINE], LINE, self.current_points, self.default_color)
            self.current_points = []

        self.redraw()

    def add_object(self, name, obj_type, coords, color="#000000"):
        self.object_count += 1
        obj = Object2D(f"{name}_{self.object_count}", obj_type, coords.copy(), color=color)
        self.display.add(obj)
        self.refresh_listbox()
        self.redraw()

    def finalize_wireframe(self):
        if len(self.current_points) > 2:
            self.add_object(options_label[WIREFRAME], WIREFRAME, self.current_points, color=self.default_color)
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

        sy_str = simpledialog.askstring("Escalonamento", "sy (deixe vazio para usar sx):", parent=self.objects_listbox)
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
            "Centro", "Usar centro do objeto como centro do escalonamento?\n(Yes = centro do objeto, No = escolher ponto arbitrário)"
        )
        if center_choice:
            cx, cy = centroid(obj.coordinates)
        else:
            cx = simpledialog.askfloat("Centro arbitrário", "cx:", parent=self.objects_listbox)
            if cx is None:
                return
            cy = simpledialog.askfloat("Centro arbitrário", "cy:", parent=self.objects_listbox)
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

        tk.Button(btn_frame, text="Mundo", width=12, command=lambda: set_choice("mundo")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Objeto", width=12, command=lambda: set_choice("objeto")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Arbitrário", width=12, command=lambda: set_choice("arbitrario")).pack(side=tk.LEFT, padx=5)

        popup.wait_window()
        return result["choice"]

    def rotate_selected(self):
        obj = self.get_selected_object()
        if obj is None:
            messagebox.showinfo("Aviso", "Selecione um objeto na lista.")
            return
        ang = simpledialog.askfloat("Rotação", "Ângulo em graus (positivo: anti-horário):", parent=self.objects_listbox)
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
            cx = simpledialog.askfloat("Centro arbitrário", "cx:", parent=self.objects_listbox)
            if cx is None:
                return
            cy = simpledialog.askfloat("Centro arbitrário", "cy:", parent=self.objects_listbox)
            if cy is None:
                return
        else:
            messagebox.showerror("Erro", "Opção inválida. Use 'mundo', 'objeto' ou 'arbitrario'.")
            return
        M = make_rotation(ang, cx, cy)
        apply_transform(M, obj)
        self.redraw()
        self.refresh_listbox()
        self.update_coords_label(obj)

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
        if c:
            obj.color = c
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
                title="Salvar mundo como .obj"
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
                title="Abrir mundo .obj"
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


class DescritorOBJ:
    @staticmethod
    def export_object(obj, index_offset=1):
        lines = []
        lines.append(f"o {obj.name}")

        # exportar vértices
        for (x, y) in obj.coordinates:
            lines.append(f"v {x:.6f} {y:.6f}")

        # exportar arestas de acordo com tipo
        if obj.obj_type == POINT:
            lines.append(f"p {index_offset}")
            next_offset = index_offset + 1

        elif obj.obj_type == LINE:
            v1 = index_offset
            v2 = index_offset + 1
            lines.append(f"l {v1} {v2}")
            next_offset = index_offset + 2

        elif obj.obj_type == WIREFRAME:
            indices = [str(i) for i in range(index_offset, index_offset + len(obj.coordinates))]
            indices.append(str(index_offset))
            lines.append("l " + " ".join(indices))
            next_offset = index_offset + len(obj.coordinates)

        else:
            next_offset = index_offset

        return lines, next_offset

    @staticmethod
    def import_objects(lines):
        objects = []
        vertices = []
        current_name = None
        current_indices = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("o "):
                if current_name and current_indices:
                    coords = [vertices[i - 1] for i in current_indices]
                    obj_type = DescritorOBJ._infer_type(current_indices)
                    objects.append(Object2D(current_name, obj_type, coords))
                    current_indices = []
                current_name = line[2:].strip()

            elif line.startswith("v "):
                parts = line.split()
                x, y = float(parts[1]), float(parts[2])
                vertices.append((x, y))

            elif line.startswith("p "):
                parts = line.split()[1:]
                current_indices = [int(p) for p in parts]
                if current_name:
                    coords = [vertices[i - 1] for i in current_indices]
                    objects.append(Object2D(current_name, POINT, coords))
                current_indices = []

            elif line.startswith("l "):
                parts = line.split()[1:]
                current_indices = [int(p) for p in parts]
                if current_name:
                    coords = [vertices[i - 1] for i in current_indices]
                    obj_type = DescritorOBJ._infer_type(current_indices)
                    objects.append(Object2D(current_name, obj_type, coords))
                current_indices = []

        # salvar último se sobrou
        if current_name and current_indices:
            coords = [vertices[i - 1] for i in current_indices]
            obj_type = DescritorOBJ._infer_type(current_indices)
            objects.append(Object2D(current_name, obj_type, coords))

        return objects
    
    @staticmethod
    def _infer_type(indices): # definir o tipo de objeto (ponto, linha, wireframe)
        if len(indices) == 1:
            return POINT
        elif len(indices) == 2:
            return LINE
        else:
            return WIREFRAME


# =====================
# Interface
# =====================
def create_side_menu(root):
    # Menu lateral (Frame) com as opções
    side_frame = tk.Frame(root)
    side_frame.pack(side=tk.LEFT, fill=tk.Y)

    # Canvas para permitir o scroll
    canvas = tk.Canvas(side_frame, width=240)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=5)

    # Scrollbar vertical
    scrollbar = tk.Scrollbar(side_frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Configurar o canvas para usar a scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Frame interno (onde ficam os botões e menus de verdade)
    menu_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=menu_frame, anchor="nw")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(event, direction):
        canvas.yview_scroll(direction, "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel) 
    canvas.bind_all("<Button-4>", lambda e: _on_mousewheel_linux(e, -1))
    canvas.bind_all("<Button-5>", lambda e: _on_mousewheel_linux(e, 1))

    return menu_frame

def main():
    root = tk.Tk()
    root.title("Computação Gráfica - Sistema Gráfico Interativo (Transformações 2D)")

    menu_frame = create_side_menu(root)

    # Frame principal (Canvas)
    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    system = GraphicSystem(root, main_frame)

    menubar = tk.Menu(root)
    root.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Arquivo", menu=file_menu)

    file_menu.add_command(label="Abrir .obj", command=system.load_from_obj)
    file_menu.add_command(label="Salvar como .obj", command=system.save_as_obj)
    file_menu.add_command(label="Sair", command=root.quit)

    # Label do menu de opções
    tk.Label(
        menu_frame, text="Menu de Opções", font=("Arial", 14, "bold")
    ).pack(pady=6)

    # Menu de seleção do tipo de objeto
    type_var = tk.StringVar(value=options_label[POINT])
    type_menu = tk.OptionMenu(menu_frame, type_var, *options_label.values())
    type_menu.pack(pady=3, fill=tk.X)

    def set_type(*args):
        label = type_var.get()
        for key, val in options_label.items():
            if val == label:
                system.current_type = key
                break
        system.current_points = []

    type_var.trace("w", set_type)

    # Botão para finalizar o wireframe
    btn_poly = tk.Button(menu_frame, text="Finalizar Wireframe", command=system.finalize_wireframe)
    btn_poly.pack(pady=6, fill=tk.X)

    # Cor padrão para novos objetos
    color_frame = tk.Frame(menu_frame)
    color_frame.pack(pady=6, fill=tk.X, padx=5)
    tk.Label(color_frame, text="Cor padrão (contorno):").pack(side=tk.LEFT)
    btn_color = tk.Button(color_frame, text="Escolher", command=system.set_default_color)
    btn_color.pack(side=tk.RIGHT)

    # Lista de objetos
    tk.Label(menu_frame, text="Objetos:", font=("Arial", 11, "bold")).pack(pady=(10,0))
    listbox = tk.Listbox(menu_frame, width=28, height=12)
    listbox.pack(padx=5, pady=4)
    system.set_objects_listbox(listbox)

    # Botões de transformação
    tf_frame = tk.LabelFrame(menu_frame, text="Transformações", padx=5, pady=5)
    tf_frame.pack(fill=tk.X, padx=5, pady=6)

    btn_translate = tk.Button(tf_frame, text="Transladar", command=system.translate_selected)
    btn_translate.pack(fill=tk.X, pady=2)

    btn_scale = tk.Button(tf_frame, text="Escalonar", command=system.scale_selected)
    btn_scale.pack(fill=tk.X, pady=2)

    btn_rotate = tk.Button(tf_frame, text="Rotacionar", command=system.rotate_selected)
    btn_rotate.pack(fill=tk.X, pady=2)

    btn_change_color = tk.Button(tf_frame, text="Mudar cor do objeto", command=system.change_selected_color)
    btn_change_color.pack(fill=tk.X, pady=2)

    btn_delete = tk.Button(tf_frame, text="Excluir objeto", command=system.delete_selected)
    btn_delete.pack(fill=tk.X, pady=2)

    # Frame inferior direito para exibir coordenadas
    coords_frame = tk.Frame(main_frame)
    coords_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    tk.Label(coords_frame, text="Coordenadas do objeto selecionado:").pack(anchor="w", padx=5)
    coords_label = tk.Label(coords_frame, text="(nenhum objeto selecionado)", anchor="w", justify="left")
    coords_label.pack(anchor="w", padx=5)
    system.coords_label = coords_label


    # Sub-menu (LabelFrame) com opções de movimentação e zoom da window contido no menu lateral
    window_frame = tk.LabelFrame(
        menu_frame, text="Window", font=("Arial", 11, "bold"), labelanchor="n", padx=5, pady=5
    )
    window_frame.pack(fill=tk.X, padx=10, pady=8)

    nav_frame = tk.Frame(window_frame)
    nav_frame.pack(pady=5)

    btn_up = tk.Button(nav_frame, text="▲", width=4, command=lambda: system.move(0, 10))
    btn_up.grid(row=0, column=1, padx=2, pady=2)

    btn_left = tk.Button(nav_frame, text="◀", width=4, command=lambda: system.move(-10, 0))
    btn_left.grid(row=1, column=0, padx=2, pady=2)

    btn_right = tk.Button(nav_frame, text="▶", width=4, command=lambda: system.move(10, 0))
    btn_right.grid(row=1, column=2, padx=2, pady=2)

    btn_down = tk.Button(nav_frame, text="▼", width=4, command=lambda: system.move(0, -10))
    btn_down.grid(row=2, column=1, padx=2, pady=2)

    zoom_frame = tk.Frame(window_frame)
    zoom_frame.pack(pady=10)

    btn_zoom_in = tk.Button(zoom_frame, text="+", command=lambda: system.zoom(0.9))
    btn_zoom_in.pack(side=tk.LEFT, padx=5)

    btn_zoom_out = tk.Button(zoom_frame, text="-", command=lambda: system.zoom(1.1))
    btn_zoom_out.pack(side=tk.LEFT, padx=5)

    rotate_frame = tk.Frame(window_frame)
    rotate_frame.pack(pady=5, fill=tk.X)

    tk.Label(rotate_frame, text="Rotação (5°):").pack(side=tk.LEFT)
    btn_rotate_left = tk.Button(rotate_frame, text="⟲", command=lambda: (system.window.rotate(5), system.redraw()))
    btn_rotate_left.pack(side=tk.LEFT, padx=2)
    btn_rotate_right = tk.Button(rotate_frame, text="⟳", command=lambda: (system.window.rotate(-5), system.redraw()))
    btn_rotate_right.pack(side=tk.LEFT, padx=2)

    # Atalhos úteis
    help_label = tk.Label(menu_frame, text="Uso rápido:\n- Clique para criar pontos/linhas\n- Finalizar wireframe para polígonos\n- Selecione objeto na lista para transformar", wraplength=200, justify="left")
    help_label.pack(padx=5, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
