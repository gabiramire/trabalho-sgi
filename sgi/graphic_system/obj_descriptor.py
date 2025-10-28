# código responsável pela lógica de importar .obj
from typing import List, Tuple, Union, Optional

from .objects import (
    Object2D,
    Object3D,
    BezierPatch,
    BezierSurface,
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

# utilitários de importação/exportação OBJ
def _resolve_index(idx: int, nverts: int) -> int:
    return idx if idx > 0 else (nverts + 1 + idx)

# Splita token 'v/vt/vn' ou similares, retornando apenas o índice de vértice 'v'.
def _split_v_token(tok: str) -> int:
    """
    Em l/f, cada token pode ser 'v', 'v/vt', 'v//vn' ou 'v/vt/vn'.
    Queremos apenas o índice de vértice 'v'.
    """
    return int(tok.split("/")[0])


# Descritor OBJ
class DescritorOBJ:
    
    # 2D: export/import (pontos, linhas, wireframes, curvas)
    @staticmethod
    def export_object(obj: Object2D, index_offset: int = 1) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {obj.name}")

        # vértices 2D -> gravamos como "v x y"
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
            # fecha o ciclo
            if len(indices) >= 2:
                indices.append(str(index_offset))
            lines.append("l " + " ".join(indices))
            next_offset = index_offset + len(obj.coordinates)

        elif obj.obj_type == CURVE:
            # curva Bezier 2D (free-form)
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
            # objeto desconhecido 2D: apenas vértices
            next_offset = index_offset + len(obj.coordinates)

        return lines, next_offset

    @staticmethod
    def import_objects(lines: List[str]) -> List[Object2D]:
        objects: List[Object2D] = []
        vertices2d: List[Tuple[float, float]] = []  # 0-based
        current_name: Optional[str] = None

        # estado para curva 2D free-form
        cstype_bezier = False
        curve_deg = None
        pending_curves: List[List[int]] = []  # cada entrada é a lista de índices 1-based

        def flush_curve_2d_blocks():
            nonlocal pending_curves, current_name
            for idxs in pending_curves:
                # resolve índices relativos em 2D
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
                # novo objeto/grupo: fecha curvas pendentes
                flush_curve_2d_blocks()
                # usa o texto após 'o ' ou 'g ' como nome, se houver
                nm = s[len(kw) + 1 :].strip()
                current_name = nm or current_name

            elif kw == "v":
                # aceita v x y  [z opcional]
                if len(parts) >= 3 and _is_float(parts[1]) and _is_float(parts[2]):
                    x, y = float(parts[1]), float(parts[2])
                    vertices2d.append((x, y))

            elif kw == "vp" and len(parts) >= 3 and _is_float(parts[1]) and _is_float(parts[2]):
                # opcional: tratar vp (param) como (u,v) 2D
                u, v = float(parts[1]), float(parts[2])
                vertices2d.append((u, v))

            elif kw == "p":
                flush_curve_2d_blocks()
                idxs = [int(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "l":
                flush_curve_2d_blocks()
                # l i j k ... (pode ter i//vn, etc.)
                idxs = [_split_v_token(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "cstype":
                # ativa modo curva Bezier 2D
                modes = [p.lower() for p in parts[1:]]
                cstype_bezier = ("bezier" in modes)

            elif kw == "deg":
                if cstype_bezier and len(parts) >= 2:
                    curve_deg = int(parts[1])

            elif kw == "curv":
                if cstype_bezier:
                    # curv u0 u1 i1 i2 ... iM
                    if len(parts) >= 5:
                        idxs = [int(p) for p in parts[3:]]  # ignora u0,u1
                        pending_curves.append(idxs)

            elif kw == "end":
                # encerra bloco cstype
                cstype_bezier = False
                curve_deg = None

        # flush final
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


    # 3D: wireframes (v/l/f)
    @staticmethod
    def import_objects_3d(lines: List[str], color: str = "#000000") -> List[Object3D]:
        objects: List[Object3D] = []
        verts: List[Optional[Point3D]] = [None]  # 1-based
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

    # 3D: Superfícies Bézier e B-spline
    @staticmethod
    def import_bezier_surfaces(
        lines: List[str],
        color: str = "#000000",
        nu: int = 16,
        nv: int = 16,
    ) -> List[BezierSurface]:
        verts: List[Optional[Point3D]] = [None]  # 1-based
        surfaces: List[BezierSurface] = []

        current_name: Optional[str] = None
        cstype_ok = False  # bezier ou bspline aceitos
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
                # fecha superfície anterior
                flush_surface()
                nm = s[len(kw) + 1 :].strip()
                current_name = nm or current_name

            elif kw == "v" and len(parts) >= 4:
                x, y, z = map(float, parts[1:4])
                verts.append(Point3D(x, y, z))

            elif kw == "cstype":
                modes = [p.lower() for p in parts[1:]]
                # aceitamos bezier OU bspline (didático)
                cstype_ok = ("bezier" in modes) or ("bspline" in modes)

            elif kw == "deg":
                if len(parts) >= 3:
                    du, dv = int(parts[1]), int(parts[2])

            elif kw == "surf":
                # suportamos 'surf u0 u1 v0 v1 i1 ... i16'
                if not cstype_ok or (du, dv) != (3, 3):
                    # fora de escopo do curso
                    continue
                if len(parts) < 5 + 16:
                    # sem 16 índices não é patch bicúbico
                    continue

                # lê índices (resolvendo relativos)
                n = len(verts) - 1
                rawidx = parts[5 : 5 + 16]
                idxs = [_resolve_index(int(p), n) for p in rawidx]
                if any(i <= 0 or i > n for i in idxs):
                    continue

                # monta grid 4x4 linha-a-linha
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

        # flush final
        flush_surface()
        return surfaces

    @staticmethod
    def export_bezier_surface(
        surface: BezierSurface,
        index_offset: int = 1,
    ) -> Tuple[List[str], int]:
        lines: List[str] = []
        lines.append(f"o {surface.name}")
        vstart = index_offset

        # escreve todos os vértices dos patches (16 por patch)
        vcount = 0
        for patch in surface.patches:
            for i in range(4):
                for j in range(4):
                    P = patch.control[i][j]
                    lines.append(f"v {P.x:.6f} {P.y:.6f} {P.z:.6f}")
                    vcount += 1

        # por compat: exportamos como 'bezier 3 3'
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

        # Superfícies Bezier (e bspline 3x3 didática)
        try:
            out.extend(DescritorOBJ.import_bezier_surfaces(lines, color=color_3d))
        except Exception:
            pass

        return out
