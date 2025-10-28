# bspline_surface.py
import math
from typing import List, Tuple

from .point3d import Point3D

Number = float

# Utilidades 4x4 de matriz
def _mat_mul4(A, B):
    out = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        Ai = A[i]
        for j in range(4):
            s = 0.0
            for k in range(4):
                s += Ai[k] * B[k][j]
            out[i][j] = s
    return out

# A * B * C (tudo 4x4)
def _mat_mul4_chain(A, B, C):
    return _mat_mul4(_mat_mul4(A, B), C)

def _transpose4(A):
    return [[A[0][0], A[1][0], A[2][0], A[3][0]],
            [A[0][1], A[1][1], A[2][1], A[3][1]],
            [A[0][2], A[1][2], A[2][2], A[3][2]],
            [A[0][3], A[1][3], A[2][3], A[3][3]]]


# Base cúbica B-spline e matrizes de FD (E)
def bspline_uniform_cubic_basis() -> List[List[Number]]:
    # Matriz base cúbica B-spline uniforme (Foley & van Dam)
    s = 1.0 / 6.0
    return [
        [-1*s,  3*s, -3*s, 1*s],
        [ 3*s, -6*s,  3*s, 0*s],
        [-3*s,  0*s,  3*s, 0*s],
        [ 1*s,  4*s,  1*s, 0*s],
    ]

def build_Ed(h: Number) -> List[List[Number]]:
    h2 = h*h
    h3 = h*h*h
    return [
        [0.0, 0.0, 0.0, 1.0],   # f0
        [h3,  h2,  h,   0.0],   # delta1
        [6*h3, 2*h2, 0.0, 0.0], # delta2
        [6*h3, 0.0,  0.0, 0.0], # delta3
    ]


# Geometria e coeficientes C
# Extrai Gx, Gy, Gz (4x4) a partir de uma grade 4x4 de Point3D.
def _build_geom_matrices_4x4(ctrl4x4: List[List[Point3D]]):
    Gx = [[0.0]*4 for _ in range(4)]
    Gy = [[0.0]*4 for _ in range(4)]
    Gz = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        row = ctrl4x4[i]
        for j in range(4):
            p = row[j]
            Gx[i][j] = p.x
            Gy[i][j] = p.y
            Gz[i][j] = p.z
    return Gx, Gy, Gz

# Coeficientes em base potência: C = M · G · Mᵀ
def _compute_C_from_G(G: List[List[Number]], M: List[List[Number]]) -> List[List[Number]]:
    Mt = _transpose4(M)
    return _mat_mul4_chain(M, G, Mt)

# Forward differences 
def _advance_rows(DD: List[List[Number]]) -> None:
    for c in range(4):
        DD[0][c] += DD[1][c]
        DD[1][c] += DD[2][c]
        DD[2][c] += DD[3][c]

# Gera n+1 amostras 1D (f, delta1, delta2, delta3) via FD para um polinômio cúbico.
def _fd_curve_samples(n: int, seeds: Tuple[Number, Number, Number, Number]) -> List[Number]:
    f, d1, d2, d3 = seeds
    out = []
    for _ in range(n+1):
        out.append(f)
        # step FD
        f += d1
        d1 += d2
        d2 += d3
    return out

def _fd_patch_grid(ctrl4x4: List[List[Point3D]], nu: int, nv: int) -> List[List[Tuple[Number, Number, Number]]]:
    # base cúbica uniforme
    M = bspline_uniform_cubic_basis()

    # Gx,Gy,Gz e coeficientes Cx,Cy,Cz (base potência)
    Gx, Gy, Gz = _build_geom_matrices_4x4(ctrl4x4)
    Cx = _compute_C_from_G(Gx, M)
    Cy = _compute_C_from_G(Gy, M)
    Cz = _compute_C_from_G(Gz, M)

    # Matrizes Ed para cada direção
    Eds = build_Ed(1.0 / max(1, nu))  # s ~ u
    Edt = build_Ed(1.0 / max(1, nv))  # t ~ v
    EdtT = _transpose4(Edt)

    # Condições iniciais 2D (tabelas DD) para x,y,z
    DDx = _mat_mul4_chain(Eds, Cx, EdtT)
    DDy = _mat_mul4_chain(Eds, Cy, EdtT)
    DDz = _mat_mul4_chain(Eds, Cz, EdtT)

    # --- 1ª família: curvas em t (varre v), avançando por s entre curvas ---
    # Vamos produzir uma grade primária de (nu+1) x (nv+1):
    grid_s_then_t: List[List[Tuple[Number, Number, Number]]] = []

    for _is in range(nu + 1):
        # sementes (f,delta1,delta2,delta3) = 1ª linha de DD em t
        seeds_x = (DDx[0][0], DDx[0][1], DDx[0][2], DDx[0][3])
        seeds_y = (DDy[0][0], DDy[0][1], DDy[0][2], DDy[0][3])
        seeds_z = (DDz[0][0], DDz[0][1], DDz[0][2], DDz[0][3])

        xs = _fd_curve_samples(nv, seeds_x)  # nt = nv
        ys = _fd_curve_samples(nv, seeds_y)
        zs = _fd_curve_samples(nv, seeds_z)

        # uma "linha" da malha (fixo s, variando t)
        row = [(xs[j], ys[j], zs[j]) for j in range(nv + 1)]
        grid_s_then_t.append(row)

        # soma de linhas para preparar a próxima curva (avançar em s)
        _advance_rows(DDx)
        _advance_rows(DDy)
        _advance_rows(DDz)

    # Neste ponto temos (nu+1) linhas, cada uma com (nv+1) pontos.
    grid_v_then_u = _transpose_grid(grid_s_then_t)  # (nv+1) x (nu+1)

    return grid_v_then_u

# Transpôe grade de tamanho (nu+1) x (nv+1) para (nv+1) x (nu+1).
def _transpose_grid(grid_st: List[List[Tuple[Number, Number, Number]]]) -> List[List[Tuple[Number, Number, Number]]]:
    if not grid_st:
        return []
    rows = len(grid_st)
    cols = len(grid_st[0])
    return [[grid_st[i][j] for i in range(rows)] for j in range(cols)]

# Superfície completa (m×n de ctrl)
def subdivide_patches(control: List[List[Point3D]]) -> List[List[List[Point3D]]]:
    # divide uma malha m×n (4..20) de pontos de controle em retalhos 4×4.
    m = len(control)
    if m < 4:
        raise ValueError("A malha B-spline deve ter pelo menos 4 linhas.")
    n = len(control[0])
    if any(len(row) != n for row in control):
        raise ValueError("Todas as linhas devem ter o mesmo comprimento.")
    if n < 4:
        raise ValueError("A malha B-spline deve ter pelo menos 4 colunas.")
    if m > 20 or n > 20:
        raise ValueError("Dimensões devem ser no máximo 20x20 (conforme requisito).")

    patches = []
    for i in range(m - 3):
        for j in range(n - 3):
            patch = [control[i+0][j:j+4],
                     control[i+1][j:j+4],
                     control[i+2][j:j+4],
                     control[i+3][j:j+4]]
            patches.append(patch)
    return patches

# Lista de grades, para cada grade (nv+1) x (nu+1) de pontos (x,y,z) (tuplas)
def generate_bspline_mesh(control: List[List[Point3D]], nu: int = 12, nv: int = 12):
    grids = []
    for patch in subdivide_patches(control):
        grids.append(_fd_patch_grid(patch, nu=nu, nv=nv))
    return grids
