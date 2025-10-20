# B-Spline cúbica usando Forward Differences
def evaluate_bspline_fd(points, num_samples=50):
    if len(points) < 4:
        return []

    # matriz base da B-Spline cúbica
    M_bs = [
        [-1/6,  3/6, -3/6, 1/6],
        [ 3/6, -6/6,  3/6,   0],
        [-3/6,   0 ,  3/6,   0],
        [ 1/6,  4/6,  1/6,   0],
    ]

    result = []
    delta = 1.0 / num_samples

    for i in range(len(points) - 3):
        px = [points[i+j][0] for j in range(4)]
        py = [points[i+j][1] for j in range(4)]

        # coeficientes polinomiais C = M_bs * P
        Cx = [sum(M_bs[r][c] * px[c] for c in range(4)) for r in range(4)]
        Cy = [sum(M_bs[r][c] * py[c] for c in range(4)) for r in range(4)]

        # valores iniciais de forward differences
        x = Cx[3]
        y = Cy[3]
        dx = (Cx[2] + (Cx[1] + Cx[0] * delta) * delta) * delta
        dy = (Cy[2] + (Cy[1] + Cy[0] * delta) * delta) * delta
        d2x = (2*Cx[1] + 6*Cx[0] * delta) * delta * delta
        d2y = (2*Cy[1] + 6*Cy[0] * delta) * delta * delta
        d3x = 6 * Cx[0] * delta**3
        d3y = 6 * Cy[0] * delta**3

        for _ in range(num_samples):
            result.append((x, y))
            x += dx
            y += dy
            dx += d2x
            dy += d2y
            d2x += d3x
            d2y += d3y

    return result


def parse_points(s):
    # Converte string do formato '(x1,y1),(x2,y2),...' para lista de tuplas
    pts = []
    s = s.strip()
    for part in s.split("),"):
        part = part.strip(" ()")
        if not part:
            continue
        x, y = part.split(",")
        pts.append((float(x), float(y)))
    return pts
