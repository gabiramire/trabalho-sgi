import math
from typing import List, Tuple, Union

from .point3d import Point3D

# Tipos de objeto
POINT = "point"
LINE = "line"
WIREFRAME = "wireframe"  # polígono = wireframe
CURVE = "curve"
OBJECT3D = "object3d"

options_label = {
    POINT: "Ponto",
    LINE: "Linha",
    WIREFRAME: "Wireframe",
    CURVE: "Curva",
    OBJECT3D: "Objeto 3D",
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


class Object3D:
    def __init__(
        self, name: str, edges: List[Tuple[Point3D, Point3D]], color: str = "#000000"
    ):
        self.name = name
        self.edges = edges  # list of (Point3D, Point3D)
        self.color = color

    def __repr__(self):
        return f"Object3D({self.name}, edges={len(self.edges)})"

    def translate(self, tx: float, ty: float, tz: float):
        for p1, p2 in self.edges:
            p1.translate(tx, ty, tz)
            p2.translate(tx, ty, tz)

    def scale(
        self,
        sx: float,
        sy: float,
        sz: float,
        cx: float = 0,
        cy: float = 0,
        cz: float = 0,
    ):
        for p1, p2 in self.edges:
            p1.scale(sx, sy, sz, cx, cy, cz)
            p2.scale(sx, sy, sz, cx, cy, cz)

    def rotate_x(self, angle_deg: float):
        for p1, p2 in self.edges:
            p1.rotate_x(angle_deg)
            p2.rotate_x(angle_deg)

    def rotate_y(self, angle_deg: float):
        for p1, p2 in self.edges:
            p1.rotate_y(angle_deg)
            p2.rotate_y(angle_deg)

    def rotate_z(self, angle_deg: float):
        for p1, p2 in self.edges:
            p1.rotate_z(angle_deg)
            p2.rotate_z(angle_deg)

    def rotate_axis(self, p1: Point3D, p2: Point3D, angle_deg: float):
        ux, uy, uz = (p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
        length = math.sqrt(ux**2 + uy**2 + uz**2)
        if length == 0:
            return
        ux, uy, uz = ux / length, uy / length, uz / length

        angle = math.radians(angle_deg)
        cosA = math.cos(angle)
        sinA = math.sin(angle)

        # R = [[
        #     1, 0, 0, 0,
        #     0, math.cos(angle), math.sin(angle), 0,
        #     0, -math.sin(angle), math.cos(angle), 0,
        #     0, 0, 0, 1
        # ],
        # [
        #     math.cos(angle), 0, -math.sin(angle), 0,
        #     0, 1, 0, 0,
        #     math.sin(angle), 0, math.cos(angle), 0,
        #     0, 0, 0, 1
        # ],
        # [
        #     math.cos(angle), math.sin(angle), 0, 0,
        #     -math.sin(angle), math.cos(angle), 0, 0,
        #     0, 0, 1, 0,
        #     0, 0, 0, 1
        # ]]

        # Rodrigues rotation formula
        R = [
            [
                cosA + ux**2 * (1 - cosA),
                ux * uy * (1 - cosA) - uz * sinA,
                ux * uz * (1 - cosA) + uy * sinA,
            ],
            [
                uy * ux * (1 - cosA) + uz * sinA,
                cosA + uy**2 * (1 - cosA),
                uy * uz * (1 - cosA) - ux * sinA,
            ],
            [
                uz * ux * (1 - cosA) - uy * sinA,
                uz * uy * (1 - cosA) + ux * sinA,
                cosA + uz**2 * (1 - cosA),
            ],
        ]

        for edge in self.edges:
            for point in edge:
                x, y, z = point.x - p1.x, point.y - p1.y, point.z - p1.z
                xr = R[0][0] * x + R[0][1] * y + R[0][2] * z
                yr = R[1][0] * x + R[1][1] * y + R[1][2] * z
                zr = R[2][0] * x + R[2][1] * y + R[2][2] * z
                point.x, point.y, point.z = xr + p1.x, yr + p1.y, zr + p1.z

    def rotate(self, angle_deg: float, cx: float = 0, cy: float = 0, cz: float = 0):
        self.translate(-cx, -cy, -cz)
        self.rotate_z(angle_deg)
        self.rotate_y(angle_deg)
        self.rotate_x(angle_deg)
        self.translate(cx, cy, cz)

    def project(self, camera) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        vrp = camera.vrp
        vpn = camera.vpn
        vup = camera.vup

        n_len = math.sqrt(vpn[0] ** 2 + vpn[1] ** 2 + vpn[2] ** 2)
        n = [vpn[0] / n_len, vpn[1] / n_len, vpn[2] / n_len]

        cross = [
            vup[1] * n[2] - vup[2] * n[1],
            vup[2] * n[0] - vup[0] * n[2],
            vup[0] * n[1] - vup[1] * n[0],
        ]
        u_len = math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
        u = [cross[0] / u_len, cross[1] / u_len, cross[2] / u_len]

        v = [
            n[1] * u[2] - n[2] * u[1],
            n[2] * u[0] - n[0] * u[2],
            n[0] * u[1] - n[1] * u[0],
        ]

        view_orient = [
            [u[0], u[1], u[2], 0],
            [v[0], v[1], v[2], 0],
            [n[0], n[1], n[2], 0],
            [0, 0, 0, 1],
        ]

        t = [
            [1, 0, 0, -vrp[0]],
            [0, 1, 0, -vrp[1]],
            [0, 0, 1, -vrp[2]],
            [0, 0, 0, 1],
        ]

        view_matrix = [[0] * 4 for _ in range(4)]
        for i in range(4):
            for j in range(4):
                view_matrix[i][j] = sum(view_orient[i][k] * t[k][j] for k in range(4))

        projected_edges = []
        for p1, p2 in self.edges:
            p1v = self._apply_matrix(p1, view_matrix)
            p2v = self._apply_matrix(p2, view_matrix)
            projected_edges.append(((p1v[0], p1v[1]), (p2v[0], p2v[1])))

        return projected_edges

    def _apply_matrix(self, point: Point3D, matrix):
        vec = [point.x, point.y, point.z, 1]
        res = [sum(matrix[i][j] * vec[j] for j in range(4)) for i in range(4)]
        return res[:3]


class DisplayFile:
    def __init__(self):
        self.objects: List[Union[Object2D, Object3D]] = []

    def add(self, obj: Union[Object2D, Object3D]):
        self.objects.append(obj)

    def remove(self, obj: Union[Object2D, Object3D]):
        self.objects.remove(obj)
