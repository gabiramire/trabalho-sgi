import tkinter as tk

from graphic_system.objects import CURVE, POINT, WIREFRAME, options_label


def create_side_menu(root, main_frame, system):
    # Menu lateral (Frame) com as opções
    side_frame = tk.Frame(root)
    side_frame.pack(side=tk.LEFT, fill=tk.Y)

    # Canvas para permitir o scroll
    canvas = tk.Canvas(side_frame, width=240)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5, padx=5)

    # Scrollbar vertical
    scrollbar = tk.Scrollbar(side_frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Configurar o canvas para usar a scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # Frame interno (onde ficam os botões e menus de verdade)
    menu_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=menu_frame, anchor="nw")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux_up(event):
        canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(event):
        canvas.yview_scroll(1, "units")

    menu_frame.bind(
        "<Enter>",
        lambda e: (
            menu_frame.bind_all("<MouseWheel>", _on_mousewheel),
            menu_frame.bind_all("<Button-4>", _on_mousewheel_linux_up),
            menu_frame.bind_all("<Button-5>", _on_mousewheel_linux_down),
        ),
    )

    menu_frame.bind(
        "<Leave>",
        lambda e: (
            menu_frame.unbind_all("<MouseWheel>"),
            menu_frame.unbind_all("<Button-4>"),
            menu_frame.unbind_all("<Button-5>"),
        ),
    )

    # Label do menu de opções
    tk.Label(menu_frame, text="Menu de Opções", font=("Arial", 14, "bold")).pack(pady=6)

    create_object_choice(menu_frame, system, canvas)
    create_default_color(menu_frame, system)
    list_objects_listbox(menu_frame, system)
    create_transform_frame(menu_frame, system, main_frame)
    create_window_controls(menu_frame, system)
    create_clipping_controls(menu_frame, system)

    # Atalhos úteis
    help_label = tk.Label(
        menu_frame,
        text="Uso rápido:\n- Clique para criar pontos/linhas\n- Finalizar wireframe para polígonos\n- Selecione objeto na lista para transformar",
        wraplength=200,
        justify="left",
    )
    help_label.pack(padx=5, pady=10)


def create_object_choice(menu_frame, system, canvas):
    # Função para atualizar a área de rolagem sempre que mudar algo
    def update_scrollregion():
        menu_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    # Menu de seleção do tipo de objeto
    type_var = tk.StringVar(value=options_label[POINT])
    type_menu = tk.OptionMenu(menu_frame, type_var, *options_label.values())
    type_menu.pack(pady=3, fill=tk.X)

    # Botão para finalizar o wireframe
    btn_poly = tk.Button(
        menu_frame, text="Finalizar Wireframe", command=system.finalize_wireframe
    )

    # Lógica de preenchimento de polígonos
    btn_fill = tk.Checkbutton(
        menu_frame,
        text="Preencher Polígono",
        variable=system.fill_var,
    )

    btn_curve = tk.Button(
        menu_frame, text="Finalizar Curva", command=system.finalize_curve
    )

    cont_g0 = tk.Radiobutton(
        menu_frame,
        text="Multi-segmentada G(0)",
        variable=system.curve_mode_var,
        value="G0",
        command=lambda: system.set_curve_mode(system.curve_mode_var.get()),
    )

    cont_g1 = tk.Radiobutton(
        menu_frame,
        text="Contínua G(1)",
        variable=system.curve_mode_var,
        value="G1",
        command=lambda: system.set_curve_mode(system.curve_mode_var.get()),
    )

    cont_g2 = tk.Radiobutton(
        menu_frame,
        text="B-Splines",
        variable=system.curve_mode_var,
        value="BS",
        command=lambda: system.set_curve_mode(system.curve_mode_var.get()),
    )

    def set_type(*args):
        label = type_var.get()
        system.current_type = next(
            (k for k, v in options_label.items() if v == label), None
        )
        system.current_points = []

        widgets = [btn_poly, btn_fill, btn_curve, cont_g0, cont_g1, cont_g2]
        for widget in widgets:
            widget.pack_forget()

        if system.current_type == WIREFRAME:
            btn_poly.pack(pady=6, fill=tk.X, after=type_menu)
            btn_fill.pack(anchor="w", after=btn_poly)
        elif system.current_type == CURVE:
            btn_curve.pack(pady=6, fill=tk.X, after=type_menu)
            cont_g0.pack(anchor="w", after=btn_curve)
            cont_g1.pack(anchor="w", after=cont_g0)
            cont_g2.pack(anchor="w", after=cont_g1)

        update_scrollregion()

    type_var.trace("w", set_type)
    set_type()


def create_default_color(menu_frame, system):
    # Cor padrão para novos objetos
    color_frame = tk.Frame(menu_frame)
    color_frame.pack(pady=6, fill=tk.X, padx=5)
    tk.Label(color_frame, text="Cor padrão do objeto:").pack(side=tk.LEFT)
    btn_color = tk.Button(
        color_frame, text="Escolher", command=system.set_default_color
    )
    btn_color.pack(side=tk.RIGHT)


def list_objects_listbox(menu_frame, system):
    # Lista de objetos
    tk.Label(menu_frame, text="Objetos:", font=("Arial", 11, "bold")).pack(pady=(10, 0))
    listbox = tk.Listbox(menu_frame, width=28, height=12)
    listbox.pack(padx=5, pady=4)
    system.set_objects_listbox(listbox)


def create_transform_frame(menu_frame, system, main_frame):
    # Botões de transformação
    tf_frame = tk.LabelFrame(
        menu_frame, text="Transformações", font=("Arial", 11, "bold"), padx=5, pady=5
    )
    tf_frame.pack(fill=tk.X, padx=5, pady=6)

    btn_translate = tk.Button(
        tf_frame, text="Transladar", command=system.translate_selected
    )
    btn_translate.pack(fill=tk.X, pady=2)

    btn_scale = tk.Button(tf_frame, text="Escalonar", command=system.scale_selected)
    btn_scale.pack(fill=tk.X, pady=2)

    btn_rotate = tk.Button(tf_frame, text="Rotacionar", command=system.rotate_selected)
    btn_rotate.pack(fill=tk.X, pady=2)

    btn_change_color = tk.Button(
        tf_frame, text="Mudar cor do objeto", command=system.change_selected_color
    )
    btn_change_color.pack(fill=tk.X, pady=2)

    btn_delete = tk.Button(
        tf_frame, text="Excluir objeto", command=system.delete_selected
    )
    btn_delete.pack(fill=tk.X, pady=2)

    # Frame inferior direito para exibir coordenadas
    coords_frame = tk.Frame(main_frame)
    coords_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    tk.Label(coords_frame, text="Coordenadas do objeto selecionado:").pack(
        anchor="w", padx=5
    )
    coords_label = tk.Label(
        coords_frame, text="(nenhum objeto selecionado)", anchor="w", justify="left"
    )
    coords_label.pack(anchor="w", padx=5)
    system.coords_label = coords_label


def create_window_controls(menu_frame, system):
    # Sub-menu (LabelFrame) com opções de movimentação e zoom da window contido no menu lateral
    window_frame = tk.LabelFrame(
        menu_frame, text="Window", font=("Arial", 11, "bold"), padx=5, pady=5
    )
    window_frame.pack(fill=tk.X, padx=10, pady=8)

    nav_frame = tk.Frame(window_frame)
    nav_frame.pack(pady=5)

    btn_up = tk.Button(nav_frame, text="▲", width=4, command=lambda: system.move(0, 10))
    btn_up.grid(row=0, column=1, padx=2, pady=2)

    btn_left = tk.Button(
        nav_frame, text="◀", width=4, command=lambda: system.move(-10, 0)
    )
    btn_left.grid(row=1, column=0, padx=2, pady=2)

    btn_right = tk.Button(
        nav_frame, text="▶", width=4, command=lambda: system.move(10, 0)
    )
    btn_right.grid(row=1, column=2, padx=2, pady=2)

    btn_down = tk.Button(
        nav_frame, text="▼", width=4, command=lambda: system.move(0, -10)
    )
    btn_down.grid(row=2, column=1, padx=2, pady=2)

    zoom_frame = tk.Frame(window_frame)
    zoom_frame.pack(pady=10)

    btn_zoom_in = tk.Button(zoom_frame, text="+", command=lambda: system.zoom(0.9))
    btn_zoom_in.pack(side=tk.LEFT, padx=5)

    btn_zoom_out = tk.Button(zoom_frame, text="-", command=lambda: system.zoom(1.1))
    btn_zoom_out.pack(side=tk.LEFT, padx=5)

    rotate_frame = tk.Frame(window_frame)
    rotate_frame.pack(pady=5, fill=tk.X)

    tk.Label(rotate_frame, text="Rotação (5°):").pack(side=tk.LEFT)
    btn_rotate_left = tk.Button(
        rotate_frame,
        text="⟲",
        command=lambda: (system.window.rotate(5), system.redraw()),
    )
    btn_rotate_left.pack(side=tk.LEFT, padx=2)
    btn_rotate_right = tk.Button(
        rotate_frame,
        text="⟳",
        command=lambda: (system.window.rotate(-5), system.redraw()),
    )
    btn_rotate_right.pack(side=tk.LEFT, padx=2)


# Seleção do algoritmo de clipping
def create_clipping_controls(menu_frame, system):
    clipping_frame = tk.LabelFrame(
        menu_frame, text="Clipping", font=("Arial", 11, "bold"), padx=5, pady=5
    )
    clipping_frame.pack(fill=tk.X, padx=5, pady=6)

    tk.Label(clipping_frame, text="Clipping de Retas:").pack(anchor="w")

    tk.Radiobutton(
        clipping_frame,
        text="Cohen-Sutherland",
        variable=system.clip_var,
        value="CS",
        command=lambda: system.set_clipping_mode(system.clip_var.get()),
    ).pack(anchor="w")

    tk.Radiobutton(
        clipping_frame,
        text="Liang-Barsky",
        variable=system.clip_var,
        value="LB",
        command=lambda: system.set_clipping_mode(system.clip_var.get()),
    ).pack(anchor="w")
