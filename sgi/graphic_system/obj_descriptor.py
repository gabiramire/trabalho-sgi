# descritor_obj.py
from typing import List, Tuple, Union, Optional, Dict

from .objects import (
    Object2D,
    Object3D,
    BezierPatch,
    BezierSurface,
    BSplineSurface,   # <-- importante
    POINT,
    LINE,
    WIREFRAME,
    CURVE,
)
from .point3d import Point3D


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def _resolve_index(idx: int, nverts: int) -> int:
    return idx if idx > 0 else (nverts + 1 + idx)


def _split_v_token(tok: str) -> int:
    return int(tok.split("/")[0])


class DescritorOBJ:
    # =========================
    # IMPORT
    # =========================
    @staticmethod
    def import_objects(lines: List[str]) -> List[Object2D]:
        objects: List[Object2D] = []
        vertices2d: List[Tuple[float, float]] = []
        current_name: Optional[str] = None

        cstype_bezier = False
        curve_deg = None
        pending_curves: List[List[int]] = []

        def flush_curve_2d_blocks():
            nonlocal pending_curves, current_name
            for idxs in pending_curves:
                n = len(vertices2d)
                res = [_resolve_index(i, n) for i in idxs]
                coords = [vertices2d[i - 1] for i in res]
                objects.append(Object2D(current_name or "Curva2D", CURVE, coords))
            pending_curves = []

        def flush_polyline(name: Optional[str], idxs: List[int]):
            n = len(vertices2d)
            res = [_resolve_index(i, n) for i in idxs]
            coords = [vertices2d[i - 1] for i in res]
            obj_type = DescritorOBJ._infer_type(res)
            objects.append(Object2D(name or "Objeto2D", obj_type, coords))

        for raw in lines:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            kw = parts[0].lower()

            if kw in ("o", "g"):
                flush_curve_2d_blocks()
                nm = s[len(kw) + 1 :].strip()
                current_name = nm or current_name

            elif kw == "v":
                if len(parts) >= 3 and _is_float(parts[1]) and _is_float(parts[2]):
                    x, y = float(parts[1]), float(parts[2])
                    vertices2d.append((x, y))

            elif kw == "vp" and len(parts) >= 3 and _is_float(parts[1]) and _is_float(parts[2]):
                u, v = float(parts[1]), float(parts[2])
                vertices2d.append((u, v))

            elif kw == "p":
                flush_curve_2d_blocks()
                idxs = [int(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "l":
                flush_curve_2d_blocks()
                idxs = [_split_v_token(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "cstype":
                modes = [p.lower() for p in parts[1:]]
                cstype_bezier = ("bezier" in modes)

            elif kw == "deg":
                if cstype_bezier and len(parts) >= 2:
                    curve_deg = int(parts[1])

            elif kw == "curv":
                if cstype_bezier and len(parts) >= 5:
                    idxs = [int(p) for p in parts[3:]]
                    pending_curves.append(idxs)

            elif kw == "end":
                cstype_bezier = False
                curve_deg = None

        flush_curve_2d_blocks()
        return objects

    @staticmethod
    def _infer_type(indices: List[int]) -> str:
        if len(indices) == 1:
            return POINT
        elif len(indices) == 2:
            return LINE
        else:
            return WIREFRAME

    @staticmethod
    def import_objects_3d(lines: List[str], color: str = "#000000") -> List[Object3D]:
        objects: List[Object3D] = []
        verts: List[Optional[Point3D]] = [None]
        curr_name: Optional[str] = None
        curr_edges: List[Tuple[Point3D, Point3D]] = []

        def flush():
            nonlocal curr_name, curr_edges
            if curr_name and curr_edges:
                objects.append(Object3D(curr_name, curr_edges, color=color))
            curr_name, curr_edges = None, []

        for raw in lines:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            kw = parts[0].lower()

            if kw in ("o", "g"):
                flush()
                nm = s[len(kw) + 1 :].strip()
                curr_name = nm or "Object3D"

            elif kw == "v" and len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                verts.append(Point3D(x, y, z))

            elif kw == "l":
                rawidx = parts[1:]
                n = len(verts) - 1
                idx = [_resolve_index(_split_v_token(p), n) for p in rawidx]
                for a, b in zip(idx, idx[1:]):
                    curr_edges.append((verts[a], verts[b]))

            elif kw == "f":
                rawidx = parts[1:]
                n = len(verts) - 1
                idx = [_resolve_index(_split_v_token(p), n) for p in rawidx]
                m = len(idx)
                for i in range(m):
                    a, b = idx[i], idx[(i + 1) % m]
                    curr_edges.append((verts[a], verts[b]))

        flush()
        return objects

    @staticmethod
    def import_bezier_surfaces(
        lines: List[str],
        color: str = "#000000",
        nu: int = 16,
        nv: int = 16,
    ) -> List[BezierSurface]:
        verts: List[Optional[Point3D]] = [None]
        surfaces: List[BezierSurface] = []
        current_name: Optional[str] = None
        cstype_ok = False
        du = dv = None
        current_patches: List[BezierPatch] = []

        def flush_surface():
            nonlocal current_name, current_patches
            if current_patches:
                name = current_name or "BezierSurface"
                surfaces.append(BezierSurface(name, current_patches, color=color))
                current_patches = []

        for raw in lines:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            kw = parts[0].lower()

            if kw in ("o", "g"):
                flush_surface()
                nm = s[len(kw) + 1 :].strip()
                current_name = nm or current_name

            elif kw == "v" and len(parts) >= 4:
                x, y, z = map(float, parts[1:4])
                verts.append(Point3D(x, y, z))

            elif kw == "cstype":
                modes = [p.lower() for p in parts[1:]]
                cstype_ok = ("bezier" in modes) or ("bspline" in modes)

            elif kw == "deg" and len(parts) >= 3:
                du, dv = int(parts[1]), int(parts[2])

            elif kw == "surf":
                if not cstype_ok or (du, dv) != (3, 3) or len(parts) < 5 + 16:
                    continue
                n = len(verts) - 1
                rawidx = parts[5 : 5 + 16]
                idxs = [_resolve_index(int(p), n) for p in rawidx]
                if any(i <= 0 or i > n for i in idxs):
                    continue

                control = []
                for r in range(4):
                    row = []
                    for c in range(4):
                        row.append(verts[idxs[r * 4 + c]])
                    control.append(row)
                current_patches.append(
                    BezierPatch(
                        f"{(current_name or 'surf')}_p{len(current_patches) + 1}",
                        control,
                        color=color,
                        nu=nu,
                        nv=nv,
                    )
                )

            elif kw == "end":
                cstype_ok = False
                du = dv = None

        flush_surface()
        return surfaces

    # =========================
    # EXPORT
    # =========================

    # 2D
    @staticmethod
    def export_object2d(obj: Object2D, index_offset: int) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {obj.name}")

        for x, y in obj.coordinates:
            lines.append(f"v {x:.6f} {y:.6f}")

        next_offset = index_offset

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
            if len(indices) >= 2:
                indices.append(str(index_offset))
            lines.append("l " + " ".join(indices))
            next_offset = index_offset + len(obj.coordinates)

        elif obj.obj_type == CURVE:
            npts = len(obj.coordinates)
            if npts < 2:
                idxs = [str(i) for i in range(index_offset, index_offset + npts)]
                lines.append("l " + " ".join(idxs))
                next_offset = index_offset + npts
            else:
                deg = max(1, npts - 1)
                u0, u1 = 0.0, 1.0
                lines.append("cstype bezier")
                lines.append(f"deg {deg}")
                idxs = " ".join(str(i) for i in range(index_offset, index_offset + npts))
                lines.append(f"curv {u0} {u1} {idxs}")
                lines.append("end")
                next_offset = index_offset + npts
        else:
            next_offset = index_offset + len(obj.coordinates)

        return lines, next_offset

    # 3D wireframe
    @staticmethod
    def export_object3d(obj: Object3D, index_offset: int) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {obj.name}")

        # indexa vértices únicos
        idx_map: Dict[int, int] = {}
        verts: List[Point3D] = []

        def get_idx(p: Point3D) -> int:
            pid = id(p)
            if pid in idx_map:
                return idx_map[pid]
            nonlocal_index = index_offset + len(verts)
            verts.append(p)
            idx_map[pid] = nonlocal_index
            return idx_map[pid]

        # first pass to collect verts
        for a, b in obj.edges:
            get_idx(a)
            get_idx(b)

        # write verts
        for p in verts:
            lines.append(f"v {p.x:.6f} {p.y:.6f} {p.z:.6f}")

        # write lines
        for a, b in obj.edges:
            ia, ib = get_idx(a), get_idx(b)
            lines.append(f"l {ia} {ib}")

        next_offset = index_offset + len(verts)
        return lines, next_offset

    # Bézier surface (patches 4x4)
    @staticmethod
    def export_bezier_surface(surface: BezierSurface, index_offset: int) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {surface.name}")
        vstart = index_offset

        vcount = 0
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
        for _patch in surface.patches:
            idxs = [str(vstart + acc + k) for k in range(1, 16 + 1)]
            acc += 16
            lines.append(f"surf {u0} {u1} {v0} {v1} " + " ".join(idxs))

        lines.append("end")
        next_offset = vstart + vcount
        return lines, next_offset

    # B-spline surface (didática: blocos 4x4)
    @staticmethod
    def export_bspline_surface(surface: BSplineSurface, index_offset: int) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {surface.name}")

        control = surface.control
        m = len(control)
        n = len(control[0]) if m else 0

        # coletar todos os vértices usados pelos blocos 4x4 em ordem
        # e mapear para índice global (sem repetir)
        used: List[Point3D] = []
        used_map: Dict[int, int] = {}

        def push_vertex(p: Point3D) -> int:
            pid = id(p)
            if pid in used_map:
                return used_map[pid]
            used_map[pid] = index_offset + len(used)
            used.append(p)
            return used_map[pid]

        # varre blocos 4x4 não sobrepostos
        blocks: List[List[int]] = []  # lista de 16 índices (1-based OBJ)
        for r0 in range(0, m - 3, 4):
            for c0 in range(0, n - 3, 4):
                idxs_block: List[int] = []
                for i in range(4):
                    for j in range(4):
                        p = control[r0 + i][c0 + j]
                        idxs_block.append(push_vertex(p))
                blocks.append(idxs_block)

        # escreve vértices
        for p in used:
            lines.append(f"v {p.x:.6f} {p.y:.6f} {p.z:.6f}")

        # escreve cstype/deg/surf para cada bloco
        lines.append("cstype bspline")
        lines.append("deg 3 3")
        u0, u1, v0, v1 = 0, 1, 0, 1
        for idxs_block in blocks:
            # OBJ é 1-based; nossos índices já são baseados em index_offset
            lines.append(
                f"surf {u0} {u1} {v0} {v1} " + " ".join(str(i) for i in idxs_block)
            )
        lines.append("end")

        next_offset = index_offset + len(used)
        return lines, next_offset

    # Cena heterogênea
    @staticmethod
    def export_scene(objs: List[Union[Object2D, Object3D, BezierSurface, BSplineSurface]]) -> List[str]:
        lines: List[str] = []
        idx = 1
        for obj in objs:
            if isinstance(obj, Object2D):
                part, idx = DescritorOBJ.export_object2d(obj, idx)
                lines.extend(part)
            elif isinstance(obj, BezierSurface):
                part, idx = DescritorOBJ.export_bezier_surface(obj, idx)
                lines.extend(part)
            elif isinstance(obj, BSplineSurface):
                part, idx = DescritorOBJ.export_bspline_surface(obj, idx)
                lines.extend(part)
            elif isinstance(obj, Object3D):
                part, idx = DescritorOBJ.export_object3d(obj, idx)
                lines.extend(part)
            else:
                try:
                    part, idx = DescritorOBJ.export_object3d(obj, idx)
                    lines.extend(part)
                except Exception:
                    # ignora tipos desconhecidos
                    pass
        return lines

    # Mestre: função principal
    @staticmethod
    def import_all(lines: List[str], color_3d: str = "#000000") -> List[Union[Object2D, Object3D]]:
        out: List[Union[Object2D, Object3D]] = []

        # 2D
        try:
            out.extend(DescritorOBJ.import_objects(lines))
        except Exception:
            pass

        # 3D wireframe
        try:
            out.extend(DescritorOBJ.import_objects_3d(lines, color=color_3d))
        except Exception:
            pass

        # Superfícies Bezier e Bspline 
        try:
            out.extend(DescritorOBJ.import_bezier_surfaces(lines, color=color_3d))
        except Exception:
            pass

        return out