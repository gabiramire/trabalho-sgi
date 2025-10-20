import math
from .point3d import Point3D

# Polinômios de Bernstein de grau 3
def _bern3(t):
    u = 1.0 - t
    return [
        u*u*u,                  # B0
        3 * t * u * u,          # B1
        3 * t * t * u,          # B2
        t*t*t                   # B3
    ]

# lista 4x4 de Point3D, retorna Point3D na superfície S(u,v)
def bicubic_bezier(control_4x4, u, v):
    Bu = _bern3(u)
    Bv = _bern3(v)

    x = y = z = 0.0
    for i in range(4):
        for j in range(4):
            b = Bu[i] * Bv[j]
            p = control_4x4[i][j]
            x += b * p.x
            y += b * p.y
            z += b * p.z
    return Point3D(x, y, z)

# gera uma grade de Point3D sobre o patch, retorna uma lista de listas: grid[i][j] = Point3D em (u_i, v_j)
def generate_surface_grid(control_4x4, nu=10, nv=10):
    grid = []
    for iu in range(nu + 1):
        u = iu / float(nu)
        row = []
        for jv in range(nv + 1):
            v = jv / float(nv)
            row.append(bicubic_bezier(control_4x4, u, v))
        grid.append(row)
    return grid
