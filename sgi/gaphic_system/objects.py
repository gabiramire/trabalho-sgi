from typing import List, Tuple


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