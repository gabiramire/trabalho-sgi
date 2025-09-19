def bezier_curve(points, num_samples=100):
    n = len(points) - 1
    curve = []

    # Algoritmo de De Casteljau
    for t_i in range(num_samples + 1):
        t = t_i / num_samples
        temp = [p for p in points]
        for r in range(1, n + 1):
            for i in range(n - r + 1):
                x = (1 - t) * temp[i][0] + t * temp[i + 1][0]
                y = (1 - t) * temp[i][1] + t * temp[i + 1][1]
                temp[i] = (x, y)
        curve.append(temp[0])
    return curve


def bezier_multisegment(points, num_samples=100):
    if len(points) < 4:
        return bezier_curve(points, num_samples)

    curve = []
    for i in range(0, len(points) - 1, 3):
        segment = points[i : i + 4]
        if len(segment) < 4:
            break
        pts = bezier_curve(segment, num_samples)
        if curve:
            pts = pts[1:]
        curve.extend(pts)
    return curve
