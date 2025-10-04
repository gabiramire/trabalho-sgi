import math
from typing import Tuple


class Window3D:
    def __init__(
        self,
        vrp: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        vpn: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        vup: Tuple[float, float, float] = (0.0, 1.0, 0.0),
        view_width: float = 200.0,
        view_height: float = 200.0,
        near: float = -1000.0,
        far: float = 1000.0,
    ):
        self.vrp = list(vrp)
        self.vpn = list(vpn)
        self.vup = list(vup)
        self.view_width = float(view_width)
        self.view_height = float(view_height)
        self.near = near
        self.far = far

        # camera axes (unit)
        self.u = [1.0, 0.0, 0.0]
        self.v = [0.0, 1.0, 0.0]
        self.n = [0.0, 0.0, 1.0]
        self._recompute_uvn()

    @staticmethod
    def _normalize(vec):
        x, y, z = vec
        mag = math.sqrt(x * x + y * y + z * z)
        if mag == 0:
            return [0.0, 0.0, 0.0]
        return [x / mag, y / mag, z / mag]

    @staticmethod
    def _cross(a, b):
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]

    def _recompute_uvn(self):
        n = self._normalize(self.vpn)
        up = self._normalize(self.vup)

        # u = up x n
        u = self._cross(up, n)
        u = self._normalize(u)
        v = self._cross(n, u)
        self.u, self.v, self.n = u, v, n

    # ---------- window navigation operations ----------
    def rotate_camera(
        self, yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0
    ):
        def rotate_vec(vec, axis, angle_deg):
            a = math.radians(angle_deg)
            ux, uy, uz = axis
            cosA = math.cos(a)
            sinA = math.sin(a)
            # Rodrigues rotation
            x, y, z = vec
            rx = (
                (cosA + ux * ux * (1 - cosA)) * x
                + (ux * uy * (1 - cosA) - uz * sinA) * y
                + (ux * uz * (1 - cosA) + uy * sinA) * z
            )
            ry = (
                (uy * ux * (1 - cosA) + uz * sinA) * x
                + (cosA + uy * uy * (1 - cosA)) * y
                + (uy * uz * (1 - cosA) - ux * sinA) * z
            )
            rz = (
                (uz * ux * (1 - cosA) - uy * sinA) * x
                + (uz * uy * (1 - cosA) + ux * sinA) * y
                + (cosA + uz * uz * (1 - cosA)) * z
            )
            return [rx, ry, rz]

        self._recompute_uvn()
        u_axis = self.u
        v_axis = self.v
        n_axis = self.n

        if abs(yaw_deg) > 1e-12:
            self.vpn = rotate_vec(self.vpn, v_axis, yaw_deg)
            self.vup = rotate_vec(self.vup, v_axis, yaw_deg)
        if abs(pitch_deg) > 1e-12:
            self.vpn = rotate_vec(self.vpn, u_axis, pitch_deg)
            self.vup = rotate_vec(self.vup, u_axis, pitch_deg)
        if abs(roll_deg) > 1e-12:
            self.vup = rotate_vec(self.vup, n_axis, roll_deg)

        self._recompute_uvn()
