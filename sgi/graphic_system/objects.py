from typing import List, Tuple

# Tipos de objeto
POINT = "point"
LINE = "line"
WIREFRAME = "wireframe"  # polígono = wireframe
CURVE = "curve"

options_label = {
    POINT: "Ponto",
    LINE: "Linha",
    WIREFRAME: "Wireframe",
    CURVE: "Curva Bézier",
}


# =====================
# Display File / Objetos
# =====================
class Object2D:
    def __init__(
        self,
        name: str,
        obj_type: str,
        coordinates: List[Tuple[float, float]],
        color: str = "#000000",
        fill_color: str = "#FFFFFF",
        filled: bool = False,
        curve_mode: str = "G0",
    ):
        self.name = name
        self.obj_type = obj_type
        self.coordinates = coordinates  # lista de tuples (x,y)
        self.color = color  # cor de contorno (RGBf hex)
        self.fill_color = fill_color  # cor de preenchimento (apenas para wireframes)
        self.filled = filled  # se o objeto é preenchido (apenas para wireframes)
        self.curve_mode = curve_mode  # modo da curva (apenas para curvas)


class DisplayFile:
    def __init__(self):
        self.objects: List[Object2D] = []

    def add(self, obj: Object2D):
        self.objects.append(obj)

    def remove(self, obj: Object2D):
        self.objects.remove(obj)
