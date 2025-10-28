# descritor_obj.py
from __future__ import annotations
from typing import List, Tuple, Union, Optional, Dict

from .objects import (
    Object2D,
    Object3D,
    BezierPatch,
    BezierSurface,
    BSplineSurface,
    POINT,
    LINE,
    WIREFRAME,
    CURVE,
)
from .point3d import Point3D


# -------------------------
# Helpers
# -------------------------
def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def _split_v_token(tok: str) -> int:
    """Extrai índice do token OBJ (ex.: '12/8/7' -> 12)."""
    return int(tok.split("/")[0])


def _resolve_index(idx: int, nverts: int) -> int:
    """Converte índices negativos OBJ para [1..n] (retorna 0 se inválido)."""
    if nverts <= 0:
        return 0
    return idx if idx > 0 else (nverts + 1 + idx)


def _infer_type(indices: List[int]) -> str:
    if len(indices) == 1:
        return POINT
    elif len(indices) == 2:
        return LINE
    else:
        return WIREFRAME


# -------------------------
# IMPORT 2D
# -------------------------
def import_2d(lines: List[str]) -> List[Object2D]:
    """
    Lê 2D a partir de:
      - v x y   (exatamente 2 coords)  OU  vp u v
      - p / l / curv (Bezier 2D)
    Duas passadas: (1) vertices; (2) primitivas.
    """
    objects: List[Object2D] = []
    v2d: List[Tuple[float, float]] = []
    current_name: Optional[str] = None

    # 1ª passada: vertices 2D
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        kw = parts[0].lower()

        if kw in ("o", "g"):
            nm = s[len(kw) + 1 :].strip()
            current_name = nm or current_name

        elif kw == "v":
            # exatamente 2 coords => 2D
            if len(parts) == 3 and _is_float(parts[1]) and _is_float(parts[2]):
                x, y = float(parts[1]), float(parts[2])
                v2d.append((x, y))

        elif kw == "vp" and len(parts) >= 3 and _is_float(parts[1]) and _is_float(parts[2]):
            u, v = float(parts[1]), float(parts[2])
            v2d.append((u, v))

    n = len(v2d)
    if n == 0:
        return objects  # nada 2D neste arquivo

    # buffers para 2ª passada
    pending_points: List[Tuple[Optional[str], List[int]]] = []
    pending_lines: List[Tuple[Optional[str], List[int]]] = []
    pending_curves: List[List[int]] = []
    in_bezier = False
    curve_deg: Optional[int] = None
    last_name: Optional[str] = None

    # 2ª passada: primitivas
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        kw = parts[0].lower()

        if kw in ("o", "g"):
            nm = s[len(kw) + 1 :].strip()
            last_name = nm or last_name

        elif kw == "p":
            idxs: List[int] = []
            for t in parts[1:]:
                try:
                    idxs.append(int(t.split("/")[0]))
                except Exception:
                    pass
            pending_points.append((last_name, idxs))

        elif kw == "l":
            idxs: List[int] = []
            for t in parts[1:]:
                try:
                    idxs.append(_split_v_token(t))
                except Exception:
                    pass
            pending_lines.append((last_name, idxs))

        elif kw == "cstype":
            modes = [p.lower() for p in parts[1:]]
            in_bezier = ("bezier" in modes)

        elif kw == "deg":
            if in_bezier and len(parts) >= 2:
                try:
                    curve_deg = int(parts[1])
                except Exception:
                    curve_deg = None

        elif kw == "curv":
            if in_bezier and len(parts) >= 5:
                try:
                    idxs = [int(p) for p in parts[3:]]
                    pending_curves.append(idxs)
                except Exception:
                    pass

        elif kw == "end":
            in_bezier = False
            curve_deg = None

    def _resolve_all(idxs: List[int]) -> Optional[List[int]]:
        if not idxs:
            return None
        out = []
        for i in idxs:
            ii = _resolve_index(i, n)
            if ii < 1 or ii > n:
                return None
            out.append(ii)
        return out

    # materializa POINTS
    for nm, idxs in pending_points:
        res = _resolve_all(idxs)
        if not res:
            continue
        for ii in res:
            x, y = v2d[ii - 1]
            objects.append(Object2D(nm or "Ponto2D", POINT, [(x, y)]))

    # materializa LINES/WIREFRAMES
    for nm, idxs in pending_lines:
        res = _resolve_all(idxs)
        if not res:
            continue
        coords = [v2d[i - 1] for i in res]
        obj_type = _infer_type(res)
        objects.append(Object2D(nm or "Objeto2D", obj_type, coords))

    # materializa CURVES (Bezier 2D)
    for idxs in pending_curves:
        res = _resolve_all(idxs)
        if not res:
            continue
        coords = [v2d[i - 1] for i in res]
        objects.append(Object2D(last_name or "Curva2D", CURVE, coords))

    return objects


# -------------------------
# IMPORT 3D (wireframe e faces)
# -------------------------
def import_3d(lines: List[str], color: str = "#000000") -> List[Object3D]:
    """
    Lê 3D a partir de:
      - v x y z
      - l / f (com vt/vn opcionais nos tokens)
    Duas passadas: (1) vertices; (2) arestas.
    """
    objects: List[Object3D] = []
    verts: List[Optional[Point3D]] = [None]

    # 1ª passada: VERTICES 3D (só v com >=3 coords)
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if parts[0].lower() == "v" and len(parts) >= 4 and all(_is_float(x) for x in parts[1:4]):
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            verts.append(Point3D(x, y, z))

    n = len(verts) - 1
    if n == 0:
        return objects  # nada 3D

    # 2ª passada: grupos e arestas
    curr_name: Optional[str] = None
    pending_edges: List[Tuple[int, int]] = []

    def _flush():
        nonlocal curr_name, pending_edges
        if pending_edges:
            name = curr_name or "Object3D"
            edges_pts: List[Tuple[Point3D, Point3D]] = []
            for a, b in pending_edges:
                if 1 <= a <= n and 1 <= b <= n:
                    edges_pts.append((verts[a], verts[b]))  # type: ignore[index]
            if edges_pts:
                objects.append(Object3D(name, edges_pts, color=color))
        curr_name, pending_edges = None, []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        kw = parts[0].lower()

        if kw in ("o", "g"):
            _flush()
            nm = s[len(kw) + 1 :].strip()
            curr_name = nm or curr_name

        elif kw == "l":
            idx: List[int] = []
            for t in parts[1:]:
                try:
                    idx.append(_resolve_index(_split_v_token(t), n))
                except Exception:
                    pass
            for a, b in zip(idx, idx[1:]):
                pending_edges.append((a, b))

        elif kw == "f":
            idx: List[int] = []
            for t in parts[1:]:
                try:
                    idx.append(_resolve_index(_split_v_token(t), n))
                except Exception:
                    pass
            m = len(idx)
            for i in range(m):
                a, b = idx[i], idx[(i + 1) % m]
                pending_edges.append((a, b))

    _flush()
    return objects


# -------------------------
# IMPORT Bezier (patches 4x4) e BSpline (didático)
# -------------------------
def import_bezier_surfaces(
    lines: List[str], color: str = "#000000", nu: int = 16, nv: int = 16
) -> List[BezierSurface]:
    verts: List[Optional[Point3D]] = [None]
    surfaces: List[BezierSurface] = []
    current_name: Optional[str] = None
    in_bezier = False
    du = dv = None
    pending_patches: List[BezierPatch] = []

    # coletar todos os vértices 3D
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if p[0].lower() == "v" and len(p) >= 4 and all(_is_float(x) for x in p[1:4]):
            x, y, z = map(float, p[1:4])
            verts.append(Point3D(x, y, z))

    n = len(verts) - 1
    if n == 0:
        return surfaces

    def _flush_surface():
        nonlocal pending_patches, current_name
        if pending_patches:
            surfaces.append(BezierSurface(current_name or "BezierSurface", pending_patches, color=color))
            pending_patches = []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        kw = parts[0].lower()

        if kw in ("o", "g"):
            _flush_surface()
            nm = s[len(kw) + 1 :].strip()
            current_name = nm or current_name

        elif kw == "cstype":
            modes = [p.lower() for p in parts[1:]]
            in_bezier = ("bezier" in modes)

        elif kw == "deg" and len(parts) >= 3:
            try:
                du, dv = int(parts[1]), int(parts[2])
            except Exception:
                du = dv = None

        elif kw == "surf":
            if not in_bezier or (du, dv) != (3, 3) or len(parts) < 5 + 16:
                continue
            rawidx = parts[5 : 5 + 16]
            idxs = [_resolve_index(int(tok), n) for tok in rawidx]
            if any(i < 1 or i > n for i in idxs):
                continue

            idxs = [_resolve_index(int(tok), n) for tok in rawidx]

            # montar 4x4
            control: List[List[Point3D]] = []
            it = iter(idxs)
            for _ in range(4):
                row = [verts[next(it)] for __ in range(4)]  # type: ignore[index]
                control.append(row)

            pending_patches.append(
                BezierPatch(
                    f"{(current_name or 'surf')}_p{len(pending_patches)+1}",
                    control,
                    color=color,
                    nu=nu,
                    nv=nv,
                )
            )

        elif kw == "end":
            in_bezier = False
            du = dv = None

    _flush_surface()
    return surfaces


def import_bspline_surfaces(lines: List[str], color: str = "#000000") -> List[BSplineSurface]:
    verts: List[Optional[Point3D]] = [None]
    out: List[BSplineSurface] = []
    current_name: Optional[str] = None
    is_bspline = False
    du = dv = None
    pending_blocks: List[List[Point3D]] = []

    # coletar vértices
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if p[0].lower() == "v" and len(p) >= 4 and all(_is_float(x) for x in p[1:4]):
            x, y, z = map(float, p[1:4])
            verts.append(Point3D(x, y, z))

    n = len(verts) - 1
    if n == 0:
        return out

    def _flush():
        nonlocal pending_blocks, current_name
        for k, block in enumerate(pending_blocks, start=1):
            # reempacota 16 pontos em grade 4x4
            it = iter(block)
            ctrl: List[List[Point3D]] = [[next(it) for _ in range(4)] for __ in range(4)]
            out.append(BSplineSurface(f"{(current_name or 'BSplineSurface')}_b{k}", ctrl, color=color))
        pending_blocks = []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        kw = parts[0].lower()

        if kw in ("o", "g"):
            _flush()
            nm = s[len(kw) + 1 :].strip()
            current_name = nm or current_name

        elif kw == "cstype":
            modes = [p.lower() for p in parts[1:]]
            is_bspline = ("bspline" in modes)

        elif kw == "deg" and len(parts) >= 3:
            try:
                du, dv = int(parts[1]), int(parts[2])
            except Exception:
                du = dv = None

        elif kw == "surf":
            if not is_bspline or (du, dv) != (3, 3) or len(parts) < 5 + 16:
                continue
            rawidx = parts[5 : 5 + 16]
            idxs = [_resolve_index(int(tok), n) for tok in rawidx]
            if any(i < 1 or i > n for i in idxs):
                continue
            pts = [verts[i] for i in idxs]  # type: ignore[index]
            pending_blocks.append(pts)

        elif kw == "end":
            is_bspline = False
            du = dv = None

    _flush()
    return out


# -------------------------
# EXPORT
# -------------------------
def export_object2d(obj: Object2D, index_offset: int) -> Tuple[List[str], int]:
    lines: List[str] = [f"o {obj.name}"]
    for x, y in obj.coordinates:
        lines.append(f"v {x:.6f} {y:.6f}")
    next_idx = index_offset

    if obj.obj_type == POINT:
        lines.append(f"p {index_offset}")
        next_idx = index_offset + 1

    elif obj.obj_type == LINE:
        v1, v2 = index_offset, index_offset + 1
        lines.append(f"l {v1} {v2}")
        next_idx = index_offset + 2

    elif obj.obj_type == WIREFRAME:
        ids = [str(i) for i in range(index_offset, index_offset + len(obj.coordinates))]
        if len(ids) >= 2:
            ids.append(str(index_offset))  # fecha
        lines.append("l " + " ".join(ids))
        next_idx = index_offset + len(obj.coordinates)

    elif obj.obj_type == CURVE:
        npts = len(obj.coordinates)
        if npts < 2:
            next_idx = index_offset + npts
        else:
            deg = max(1, min(3, npts - 1))
            u0, u1 = 0.0, 1.0
            lines.append("cstype bezier")
            lines.append(f"deg {deg}")
            ids = " ".join(str(i) for i in range(index_offset, index_offset + npts))
            lines.append(f"curv {u0} {u1} {ids}")
            lines.append("end")
            next_idx = index_offset + npts

    else:
        next_idx = index_offset + len(obj.coordinates)

    return lines, next_idx


def export_object3d(obj: Object3D, index_offset: int) -> Tuple[List[str], int]:
    lines: List[str] = [f"o {obj.name}"]

    # indexação estável de vértices únicos
    idx_map: Dict[int, int] = {}
    verts: List[Point3D] = []

    def _id_for(p: Point3D) -> int:
        pid = id(p)
        if pid in idx_map:
            return idx_map[pid]
        nonlocal_index = index_offset + len(verts)
        verts.append(p)
        idx_map[pid] = nonlocal_index
        return nonlocal_index

    for a, b in obj.edges:
        _id_for(a)
        _id_for(b)

    for p in verts:
        lines.append(f"v {p.x:.6f} {p.y:.6f} {p.z:.6f}")

    for a, b in obj.edges:
        ia, ib = _id_for(a), _id_for(b)
        lines.append(f"l {ia} {ib}")

    return lines, index_offset + len(verts)


def export_bezier_surface(surface: BezierSurface, index_offset: int) -> Tuple[List[str], int]:
    lines: List[str] = [f"o {surface.name}"]
    vstart = index_offset
    vcount = 0

    # escreve todos os 16*n patches
    for patch in surface.patches:
        for i in range(4):
            for j in range(4):
                P = patch.control[i][j]
                lines.append(f"v {P.x:.6f} {P.y:.6f} {P.z:.6f}")
                vcount += 1

    lines.append("cstype bezier")
    lines.append("deg 3 3")
    u0, u1, v0, v1 = 0, 1, 0, 1
    acc = 0
    for _ in surface.patches:
        idxs = [str(vstart + acc + k) for k in range(0, 16)]
        acc += 16
        lines.append(f"surf {u0} {u1} {v0} {v1} " + " ".join(idxs))
    lines.append("end")

    return lines, vstart + vcount


def export_bspline_surface(surface: BSplineSurface, index_offset: int) -> Tuple[List[str], int]:
    lines: List[str] = [f"o {surface.name}"]
    control = surface.control
    m = len(control)
    n = len(control[0]) if m else 0

    used: List[Point3D] = []
    used_map: Dict[int, int] = {}

    def push(p: Point3D) -> int:
        pid = id(p)
        if pid in used_map:
            return used_map[pid]
        used_map[pid] = index_offset + len(used)
        used.append(p)
        return used_map[pid]

    # blocos 4x4 (não sobrepostos)
    blocks: List[List[int]] = []
    for r0 in range(0, m - 3, 4):
        for c0 in range(0, n - 3, 4):
            idxs: List[int] = []
            for i in range(4):
                for j in range(4):
                    idxs.append(push(control[r0 + i][c0 + j]))
            blocks.append(idxs)

    for p in used:
        lines.append(f"v {p.x:.6f} {p.y:.6f} {p.z:.6f}")

    lines.append("cstype bspline")
    lines.append("deg 3 3")
    u0, u1, v0, v1 = 0, 1, 0, 1
    for idxs in blocks:
        lines.append(f"surf {u0} {u1} {v0} {v1} " + " ".join(str(i) for i in idxs))
    lines.append("end")

    return lines, index_offset + len(used)


# -------------------------
# EXPORT cena heterogênea
# -------------------------
def export_scene(objs: List[Union[Object2D, Object3D, BezierSurface, BSplineSurface]]) -> List[str]:
    lines: List[str] = []
    idx = 1
    for obj in objs:
        if isinstance(obj, Object2D):
            part, idx = export_object2d(obj, idx)
            lines.extend(part)
        elif isinstance(obj, BezierSurface):
            part, idx = export_bezier_surface(obj, idx)
            lines.extend(part)
        elif isinstance(obj, BSplineSurface):
            part, idx = export_bspline_surface(obj, idx)
            lines.extend(part)
        elif isinstance(obj, Object3D):
            part, idx = export_object3d(obj, idx)
            lines.extend(part)
        else:
            # tenta 3D por último (não deve cair aqui se os tipos forem os da sua base)
            try:
                part, idx = export_object3d(obj, idx)
                lines.extend(part)
            except Exception:
                pass
    return lines


# -------------------------
# Mestre: import_all
# -------------------------
def import_all(lines: List[str], color_3d: str = "#000000") -> List[Union[Object2D, Object3D]]:
    """
    Importa heterogêneo de forma segura:
      - Sempre tenta 2D e 3D, mas cada um só cria algo se houver vértices próprios.
      - Superfícies só se houver blocos 'surf' válidos.
    """
    out: List[Union[Object2D, Object3D]] = []

    # pré-scan: detecta se há blocos de superfície válidos
    in_bezier = False
    in_bspline = False
    bezier_has_surf = False
    bspline_has_surf = False
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        kw = p[0].lower()
        if kw == "cstype":
            modes = [x.lower() for x in p[1:]]
            in_bezier = ("bezier" in modes)
            in_bspline = ("bspline" in modes)
        elif kw == "deg":
            # validação final é feita dentro do import de superfícies
            pass
        elif kw == "surf":
            if in_bezier and len(p) >= 5 + 16:
                bezier_has_surf = True
            if in_bspline and len(p) >= 5 + 16:
                bspline_has_surf = True
        elif kw == "end":
            in_bezier = False
            in_bspline = False

    # 2D e 3D
    try:
        out.extend(import_2d(lines))
    except Exception:
        pass

    try:
        out.extend(import_3d(lines, color=color_3d))
    except Exception:
        pass

    # superfícies (condicionais)
    if bezier_has_surf:
        try:
            out.extend(import_bezier_surfaces(lines, color=color_3d))
        except Exception:
            pass

    if bspline_has_surf:
        try:
            out.extend(import_bspline_surfaces(lines, color=color_3d))
        except Exception:
            pass

    return out


# Compat API (classe envoltório, se você preferir DescritorOBJ.*)
class DescritorOBJ:
    import_all = staticmethod(import_all)
    import_objects = staticmethod(import_2d)
    import_objects_3d = staticmethod(import_3d)
    import_bezier_surfaces = staticmethod(import_bezier_surfaces)
    import_bspline_surfaces = staticmethod(import_bspline_surfaces)
    export_object2d = staticmethod(export_object2d)
    export_object3d = staticmethod(export_object3d)
    export_bezier_surface = staticmethod(export_bezier_surface)
    export_bspline_surface = staticmethod(export_bspline_surface)
    export_scene = staticmethod(export_scene)
