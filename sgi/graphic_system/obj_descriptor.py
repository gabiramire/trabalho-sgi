from .objects import Object2D, POINT, LINE, WIREFRAME


class DescritorOBJ:
    @staticmethod
    def export_object(obj, index_offset=1):
        lines = []
        lines.append(f"o {obj.name}")

        # exportar vértices
        for x, y in obj.coordinates:
            lines.append(f"v {x:.6f} {y:.6f}")

        # exportar arestas de acordo com tipo
        if obj.obj_type == POINT:
            lines.append(f"p {index_offset}")
            next_offset = index_offset + 1

        elif obj.obj_type == LINE:
            v1 = index_offset
            v2 = index_offset + 1
            lines.append(f"l {v1} {v2}")
            next_offset = index_offset + 2

        elif obj.obj_type == WIREFRAME:
            indices = [
                str(i) for i in range(index_offset, index_offset + len(obj.coordinates))
            ]
            indices.append(str(index_offset))
            lines.append("l " + " ".join(indices))
            next_offset = index_offset + len(obj.coordinates)

        else:
            next_offset = index_offset

        return lines, next_offset

    @staticmethod
    def import_objects(lines):
        objects = []
        vertices = []
        current_name = None
        current_indices = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("o "):
                if current_name and current_indices:
                    coords = [vertices[i - 1] for i in current_indices]
                    obj_type = DescritorOBJ._infer_type(current_indices)
                    objects.append(Object2D(current_name, obj_type, coords))
                    current_indices = []
                current_name = line[2:].strip()

            elif line.startswith("v "):
                parts = line.split()
                x, y = float(parts[1]), float(parts[2])
                vertices.append((x, y))

            elif line.startswith("p "):
                parts = line.split()[1:]
                current_indices = [int(p) for p in parts]
                if current_name:
                    coords = [vertices[i - 1] for i in current_indices]
                    objects.append(Object2D(current_name, POINT, coords))
                current_indices = []

            elif line.startswith("l "):
                parts = line.split()[1:]
                current_indices = [int(p) for p in parts]
                if current_name:
                    coords = [vertices[i - 1] for i in current_indices]
                    obj_type = DescritorOBJ._infer_type(current_indices)
                    objects.append(Object2D(current_name, obj_type, coords))
                current_indices = []

        # salvar último se sobrou
        if current_name and current_indices:
            coords = [vertices[i - 1] for i in current_indices]
            obj_type = DescritorOBJ._infer_type(current_indices)
            objects.append(Object2D(current_name, obj_type, coords))

        return objects

    @staticmethod
    def _infer_type(indices):  # definir o tipo de objeto (ponto, linha, wireframe)
        if len(indices) == 1:
            return POINT
        elif len(indices) == 2:
            return LINE
        else:
            return WIREFRAME
