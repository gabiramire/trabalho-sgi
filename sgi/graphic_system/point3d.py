import math


class Point3D:
    def __init__(self, x: float, y: float, z: float):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self):
        return f"Point3D({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def translate(self, tx: float, ty: float, tz: float):
        self.x += tx
        self.y += ty
        self.z += tz

    def scale(
        self,
        sx: float,
        sy: float,
        sz: float,
        cx: float = 0,
        cy: float = 0,
        cz: float = 0,
    ):
        self.x = cx + sx * (self.x - cx)
        self.y = cy + sy * (self.y - cy)
        self.z = cz + sz * (self.z - cz)

    def rotate_x(self, angle_deg: float):
        a = math.radians(angle_deg)
        y_new = self.y * math.cos(a) - self.z * math.sin(a)
        z_new = self.y * math.sin(a) + self.z * math.cos(a)
        self.y, self.z = y_new, z_new

    def rotate_y(self, angle_deg: float):
        a = math.radians(angle_deg)
        x_new = self.x * math.cos(a) + self.z * math.sin(a)
        z_new = -self.x * math.sin(a) + self.z * math.cos(a)
        self.x, self.z = x_new, z_new

    def rotate_z(self, angle_deg: float):
        a = math.radians(angle_deg)
        x_new = self.x * math.cos(a) - self.y * math.sin(a)
        y_new = self.x * math.sin(a) + self.y * math.cos(a)
        self.x, self.y = x_new, y_new
