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



# Descritor OBJ 
class DescritorOBJ:
    # Objetos 2D: export de pontos, linhas, wireframes e curvas
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
                # exporta como polyline trivial
                idxs = [str(i) for i in range(index_offset, index_offset + npts)]
                lines.append("l " + " ".join(idxs))
                next_offset = index_offset + npts
            else:
                # exporta como free-form bezier: cstype/deg/curv
                # grau = npts-1
                deg = max(1, npts - 1)
                u0, u1 = 0.0, 1.0
                lines.append("cstype bezier")
                lines.append(f"deg {deg}")
                idxs = " ".join(str(i) for i in range(index_offset, index_offset + npts))
                lines.append(f"curv {u0} {u1} {idxs}")
                lines.append("end")
                next_offset = index_offset + npts
        else:
            # objeto desconhecido 2D: apenas verte e não cria elemento
            next_offset = index_offset + len(obj.coordinates)

        return lines, next_offset

    # Objetos 2D: import de pontos, linhas, wireframes e curvas
    @staticmethod
    def import_objects(lines: List[str]) -> List[Object2D]:
        objects: List[Object2D] = []
        vertices2d: List[Tuple[float, float]] = []  # 0-based (armazenamos em lista 0-based)
        current_name: Optional[str] = None

        # estado para curva 2D free-form
        cstype_bezier = False
        pending_curves: List[List[int]] = []  # cada entrada é a lista de índices 1-based

        def flush_curve_2d_blocks():
            nonlocal pending_curves, current_name
            for idxs in pending_curves:
                coords = [vertices2d[i - 1] for i in idxs]
                objects.append(Object2D(current_name or "Curva2D", CURVE, coords))
            pending_curves = []

        def flush_polyline(name: Optional[str], idxs: List[int]):
            coords = [vertices2d[i - 1] for i in idxs]
            obj_type = DescritorOBJ._infer_type(idxs)
            objects.append(Object2D(name or "Objeto2D", obj_type, coords))

        for raw in lines:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            kw = parts[0].lower()

            if kw == "o":
                # novo objeto: limpa curvas pendentes
                flush_curve_2d_blocks()
                current_name = s[2:].strip() or None

            elif kw == "v":
                # pode ser 2D (x,y) ou 3D (x,y,z) – aqui, só coleto se for 2D
                if len(parts) == 3 and _is_float(parts[1]) and _is_float(parts[2]):
                    x, y = float(parts[1]), float(parts[2])
                    vertices2d.append((x, y))
                # se for 3D, ignora na importação 2D

            elif kw == "p":
                flush_curve_2d_blocks()
                idxs = [int(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "l":
                flush_curve_2d_blocks()
                idxs = [int(p) for p in parts[1:]]
                flush_polyline(current_name, idxs)

            elif kw == "cstype":
                # ativa modo curva Bezier 2D
                cstype_bezier = any(p.lower() == "bezier" for p in parts[1:])

            elif kw == "deg":
                if cstype_bezier and len(parts) >= 2:
                    # em curvas 2D, "deg N"
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

    # checa o tipo baseado pela quantidade de índices
    @staticmethod
    def _infer_type(indices: List[int]) -> str:
        if len(indices) == 1:
            return POINT
        elif len(indices) == 2:
            return LINE
        else:
            return WIREFRAME

    # Objetos 3D: importa Wireframes 3D
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

            if kw == "o":
                flush()
                curr_name = s[2:].strip() or "Object3D"

            elif kw == "v" and len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                verts.append(Point3D(x, y, z))

            elif kw == "l":
                idx = list(map(int, parts[1:]))
                for a, b in zip(idx, idx[1:]):
                    curr_edges.append((verts[a], verts[b]))

            elif kw == "f":
                # face -> ciclo de arestas
                idx = [int(p.split("/")[0]) for p in parts[1:]]
                n = len(idx)
                for i in range(n):
                    a, b = idx[i], idx[(i + 1) % n]
                    curr_edges.append((verts[a], verts[b]))

        flush()
        return objects

    # Objetos 3D: importa Superfícies Bézier
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
        cstype_bezier = False
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

            if kw == "o":
                # fecha superfície anterior
                flush_surface()
                current_name = s[2:].strip() or None

            elif kw == "v" and len(parts) >= 4:
                x, y, z = map(float, parts[1:4])
                verts.append(Point3D(x, y, z))

            elif kw == "cstype":
                cstype_bezier = any(p.lower() == "bezier" for p in parts[1:])

            elif kw == "deg":
                # para superfícies esperamos "deg 3 3"
                if len(parts) >= 3:
                    du, dv = int(parts[1]), int(parts[2])

            elif kw == "surf":
                if not cstype_bezier or (du, dv) != (3, 3):
                    raise ValueError("Apenas superfícies Bezier com deg 3 3 são suportadas.")
                if len(parts) < 5 + 16:
                    raise ValueError("Linha 'surf' precisa 4 limites + 16 índices (1-based).")
                # u0, u1, v0, v1 = map(float, parts[1:5])  # não usado
                idxs = list(map(int, parts[5:5 + 16]))
                if any(i <= 0 or i >= len(verts) for i in idxs):
                    raise ValueError("Índice de vértice fora do intervalo.")
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
                cstype_bezier = False
                du = dv = None

        # flush final
        flush_surface()
        return surfaces

    # Objetos 3D: exporta Superfícies Bézier
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

        lines.append("cstype bezier")
        lines.append("deg 3 3")

        # linhas 'surf' – 16 índices por patch, sequenciais
        u0, u1, v0, v1 = 0, 1, 0, 1
        acc = 0
        for _patch in surface.patches:
            idxs = [str(vstart + acc + k) for k in range(1, 16 + 1)]
            acc += 16
            lines.append(f"surf {u0} {u1} {v0} {v1} " + " ".join(idxs))

        lines.append("end")
        next_offset = vstart + vcount
        return lines, next_offset

    # método principal de importação, unindo as 3 lógicas
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

        # Superfícies Bezier (são Object3D, pois BezierSurface herda de Object3D)
        try:
            out.extend(DescritorOBJ.import_bezier_surfaces(lines, color=color_3d))
        except Exception:
            pass

        return out
