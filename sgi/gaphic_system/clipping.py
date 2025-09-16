# clipping.py
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

def compute_out_code(x, y, window):
    code = INSIDE
    if x < window.x_min: code |= LEFT
    elif x > window.x_max: code |= RIGHT
    if y < window.y_min: code |= BOTTOM
    elif y > window.y_max: code |= TOP
    return code

# -- Clipping de Pontos --
def clip_point(x, y, window):
    """Retorna (x, y) se o ponto está dentro da window, caso contrário None"""
    if window.x_min <= x <= window.x_max and window.y_min <= y <= window.y_max:
        return (x, y)
    return None

# -- Clipping de Retas --
def cohen_sutherland(x1, y1, x2, y2, window):
    out1 = compute_out_code(x1, y1, window)
    out2 = compute_out_code(x2, y2, window)
    accept = False

    while True:
        if not (out1 | out2):
            accept = True
            break
        elif out1 & out2:
            break
        else:
            out = out1 or out2
            if out & TOP:
                x = x1 + (x2 - x1) * (window.y_max - y1) / (y2 - y1)
                y = window.y_max
            elif out & BOTTOM:
                x = x1 + (x2 - x1) * (window.y_min - y1) / (y2 - y1)
                y = window.y_min
            elif out & RIGHT:
                y = y1 + (y2 - y1) * (window.x_max - x1) / (x2 - x1)
                x = window.x_max
            elif out & LEFT:
                y = y1 + (y2 - y1) * (window.x_min - x1) / (x2 - x1)
                x = window.x_min

            if out == out1:
                x1, y1 = x, y
                out1 = compute_out_code(x1, y1, window)
            else:
                x2, y2 = x, y
                out2 = compute_out_code(x2, y2, window)

    if accept:
        return (x1, y1, x2, y2)
    return None


def liang_barsky(x1, y1, x2, y2, window):
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - window.x_min, window.x_max - x1, y1 - window.y_min, window.y_max - y1]

    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
        else:
            u = qi / pi
            if pi < 0:
                u1 = max(u1, u)
            else:
                u2 = min(u2, u)
    if u1 > u2:
        return None

    return (x1 + u1*dx, y1 + u1*dy, x1 + u2*dx, y1 + u2*dy)


# -- Clipping de Polígonos --
def sutherland_hodgman(polygon, window):
    def inside(p, edge):
        x, y = p
        if edge == "LEFT":   return x >= window.x_min
        if edge == "RIGHT":  return x <= window.x_max
        if edge == "BOTTOM": return y >= window.y_min
        if edge == "TOP":    return y <= window.y_max
        return True

    def intersect(p1, p2, edge):
        x1, y1 = p1
        x2, y2 = p2
        if x1 == x2 and y1 == y2:
            return p1
        # Evitar divisão por zero
        if edge in ("LEFT", "RIGHT"):
            if x2 == x1:
                return (x1, y1)  # segmento vertical; retorno qualquer ponto do segmento
            x = window.x_min if edge == "LEFT" else window.x_max
            y = y1 + (y2 - y1) * (x - x1) / (x2 - x1)  # <<< CORRETO: (x - x1)
            return (x, y)
        else:  # TOP / BOTTOM
            if y2 == y1:
                return (x1, y1)  # horizontal
            y = window.y_min if edge == "BOTTOM" else window.y_max
            x = x1 + (x2 - x1) * (y - y1) / (y2 - y1)  # <<< CORRETO: (y - y1)
            return (x, y)

    output = polygon[:]
    for edge in ["LEFT", "RIGHT", "BOTTOM", "TOP"]:
        input_list = output
        output = []
        if not input_list:
            break
        s = input_list[-1]
        for e in input_list:
            if inside(e, edge):
                if not inside(s, edge):
                    output.append(intersect(s, e, edge))
                output.append(e)
            elif inside(s, edge):
                output.append(intersect(s, e, edge))
            s = e
    return output