import math
from typing import List, Tuple

from .objects import Object2D, Object3D


def mat_mult(A, B):
    # Multiplica duas matrizes 3x3 A*B
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)
    ]


def apply_transform(matrix, obj: Object2D):
    # Aplica matrix (3x3) a todas as coordenadas do objeto, alterando-o in-place.
    new_coords = []
    for x, y in obj.coordinates:
        vx = matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * 1
        vy = matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * 1
        vz = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * 1
        if vz != 0:
            new_coords.append((vx / vz, vy / vz))
        else:
            new_coords.append((vx, vy))
    obj.coordinates = new_coords


def make_translation(tx, ty):
    return [[1, 0, tx], [0, 1, ty], [0, 0, 1]]


def make_scale(sx, sy, cx=0, cy=0):
    # translate(-c) * scale * translate(c)
    t1 = make_translation(-cx, -cy)
    s = [[sx, 0, 0], [0, sy, 0], [0, 0, 1]]
    t2 = make_translation(cx, cy)
    return mat_mult(t2, mat_mult(s, t1))


def make_rotation(angle_deg, cx=0, cy=0):
    a = math.radians(angle_deg)
    cosA = math.cos(a)
    sinA = math.sin(a)
    r = [[cosA, -sinA, 0], [sinA, cosA, 0], [0, 0, 1]]
    t1 = make_translation(-cx, -cy)
    t2 = make_translation(cx, cy)
    return mat_mult(t2, mat_mult(r, t1))
