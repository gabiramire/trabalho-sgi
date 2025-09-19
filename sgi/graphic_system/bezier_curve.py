import math


def bezier_curve(points, num_samples=100):
    n = len(points) - 1
    curve = []

    # Aqui nós inicialmente utilizamos o algoritmo de De Casteljau que é recursivo
    # e calcula a mesma coisa, mas não se encaixa  nos termos de Blending Functions
    # for t_i in range(num_samples + 1):
    #     t = t_i / num_samples
    #     temp = [p for p in points]
    #     for r in range(1, n + 1):
    #         for i in range(n - r + 1):
    #             x = (1 - t) * temp[i][0] + t * temp[i + 1][0]
    #             y = (1 - t) * temp[i][1] + t * temp[i + 1][1]
    #             temp[i] = (x, y)
    #     curve.append(temp[0])

    # Agora utilizando Blending Functions e a fórmula dos polinômios de Bernstein
    for t_i in range(num_samples + 1):
        t = t_i / num_samples
        x, y = 0, 0
        for i, (px, py) in enumerate(points):
            binomial = math.comb(n, i)
            bernstein = binomial * ((1 - t) ** (n - i)) * (t**i)
            x += bernstein * px
            y += bernstein * py
        curve.append((x, y))
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
