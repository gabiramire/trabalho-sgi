import tkinter as tk

from graphic_system.objects import CURVE, OBJECT3D, SURFACE, POINT, WIREFRAME, BezierPatch, BezierSurface, options_label


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
    create_window3d_controls(menu_frame, system)
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

    btn_wireframe3d = tk.Button(
        menu_frame,
        text="Criar Wireframe 3D",
        command=lambda: create_wireframe3d_dialog(menu_frame, system),
    )

    btn_createcube3d = tk.Button(
        menu_frame,
        text="Criar Cubo 3D",
        command=lambda: create_cube3d_dialog(menu_frame, system),
    )

    btn_surface3d = tk.Button(
        menu_frame,
        text="Superfície Bézier 3D",
        command=lambda: create_surface3d_dialog(menu_frame, system),
    )

    def set_type(*args):
        label = type_var.get()
        system.current_type = next(
            (k for k, v in options_label.items() if v == label), None
        )
        system.current_points = []

        widgets = [
            btn_poly,
            btn_fill,
            btn_curve,
            cont_g0,
            cont_g1,
            cont_g2,
            btn_wireframe3d,
            btn_createcube3d,
            btn_surface3d
        ]
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
        elif system.current_type == OBJECT3D:
            btn_wireframe3d.pack(pady=6, fill=tk.X, after=type_menu)
            btn_createcube3d.pack(pady=6, fill=tk.X, after=type_menu)
            btn_surface3d.pack(pady=6, fill=tk.X, after=btn_wireframe3d)

        update_scrollregion()

    type_var.trace("w", set_type)
    set_type()


def create_cube3d_dialog(menu_frame, system):
    dialog = tk.Toplevel(menu_frame)
    dialog.title("Criar Cubo 3D")

    tk.Label(dialog, text="Nome do objeto:").grid(row=0, column=0, padx=5, pady=5)
    entry_name = tk.Entry(dialog)
    entry_name.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(dialog, text="Ponto inicial (x,y):").grid(row=1, column=0, padx=5, pady=5)
    entry_point = tk.Entry(dialog)
    entry_point.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(dialog, text="Tamanho do cubo:").grid(row=2, column=0, padx=5, pady=5)
    entry_size = tk.Entry(dialog)
    entry_size.grid(row=2, column=1, padx=5, pady=5)

    def create_cube3d():
        name = entry_name.get().strip()
        size = entry_size.get().strip()

        try:
            x, y = map(float, entry_point.get().strip().split(","))
        except ValueError:
            tk.messagebox.showerror(
                "Erro",
                "Ponto inicial inválido. Use o formato x,y com valores numéricos.",
            )
            return

        if not name:
            tk.messagebox.showerror("Erro", "Nome do objeto não pode ser vazio.")
            return

        if not size:
            tk.messagebox.showerror("Erro", "Tamanho do cubo não pode ser vazio.")
            return

        system.create_cube_3d(name, (x, y), float(size))
        dialog.destroy()

    btn_create = tk.Button(dialog, text="Criar", command=create_cube3d)
    btn_create.grid(row=3, column=0, columnspan=2, pady=10)



def create_wireframe3d_dialog(menu_frame, system):
    dialog = tk.Toplevel(menu_frame)
    dialog.title("Criar Wireframe 3D")

    tk.Label(dialog, text="Nome do objeto:").grid(row=0, column=0, padx=5, pady=5)
    entry_name = tk.Entry(dialog)
    entry_name.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(dialog, text="Número de arestas:").grid(row=1, column=0, padx=5, pady=5)
    entry_edges = tk.Entry(dialog)
    entry_edges.grid(row=1, column=1, padx=5, pady=5)

    def create_wireframe3d():
        name = entry_name.get().strip()
        try:
            num_edges = int(entry_edges.get().strip())
            if num_edges <= 0:
                raise ValueError
        except ValueError:
            tk.messagebox.showerror(
                "Erro", "Número de arestas deve ser um inteiro positivo."
            )
            return

        if not name:
            tk.messagebox.showerror("Erro", "Nome do objeto não pode ser vazio.")
            return

        start_wireframe3d(name, num_edges, menu_frame, system)
        dialog.destroy()

    btn_create = tk.Button(dialog, text="Criar", command=create_wireframe3d)
    btn_create.grid(row=2, column=0, columnspan=2, pady=10)


def start_wireframe3d(name, num_edges, menu_frame, system):
    dialog = tk.Toplevel(menu_frame)
    dialog.title("Definir Arestas do Wireframe 3D")
    dialog.transient(menu_frame.winfo_toplevel())
    dialog.grab_set()

    tk.Label(
        dialog,
        text=f"Defina as {num_edges} arestas abaixo (cada vértice no formato x,y,z):",
    ).pack(padx=8, pady=(8, 4), anchor="w")

    # === Área rolável ===
    frame_entries = tk.Frame(dialog)
    frame_entries.pack(fill="both", expand=True, padx=8, pady=4)

    canvas = tk.Canvas(frame_entries, highlightthickness=0, height=360, bg="white")
    scrollbar = tk.Scrollbar(frame_entries, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    scrollable_frame = tk.Frame(canvas, bg="white")
    win_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    # alinha largura do frame interno com o canvas
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # ===== Cabeçalho (AGORA NO MESMO GRID DO CONTEÚDO) =====
    tk.Label(scrollable_frame, text="#", width=4, anchor="center", bg="white").grid(row=0, column=0, padx=2, pady=(0, 6))
    tk.Label(scrollable_frame, text="Vértice 1 (x,y,z)", anchor="w", bg="white").grid(row=0, column=1, padx=2, pady=(0, 6), sticky="w")
    tk.Label(scrollable_frame, text="Vértice 2 (x,y,z)", anchor="w", bg="white").grid(row=0, column=2, padx=2, pady=(0, 6), sticky="w")

    # pesos das colunas p/ expandirem corretamente
    scrollable_frame.grid_columnconfigure(1, weight=1)
    scrollable_frame.grid_columnconfigure(2, weight=1)

    # ===== Entradas: 1 linha por aresta, 2 colunas (v1, v2) =====
    edge_entries = []
    for i in range(num_edges):
        row = i + 1
        tk.Label(scrollable_frame, text=f"{i+1}", width=4, anchor="center", bg="white").grid(
            row=row, column=0, padx=2, pady=2
        )

        e1 = tk.Entry(scrollable_frame)
        e2 = tk.Entry(scrollable_frame)

        # (opcional) exemplos
        # e1.insert(0, "0,0,0"); e2.insert(0, "0,0,0")

        e1.grid(row=row, column=1, padx=2, pady=2, sticky="ew")
        e2.grid(row=row, column=2, padx=2, pady=2, sticky="ew")
        edge_entries.append((e1, e2))

    # foco no primeiro campo
    if edge_entries:
        edge_entries[0][0].focus_set()

    # ===== Botões =====
    btns = tk.Frame(dialog)
    btns.pack(pady=8)

    def submit_points():
        points = []
        for idx, (e1, e2) in enumerate(edge_entries, start=1):
            t1 = e1.get().strip()
            t2 = e2.get().strip()
            try:
                x1, y1, z1 = map(float, t1.split(","))
                x2, y2, z2 = map(float, t2.split(","))
            except Exception:
                tk.messagebox.showerror(
                    "Erro",
                    f"Coordenadas inválidas na aresta {idx}.\nUse o formato x,y,z.",
                    parent=dialog,
                )
                (e1 if t1.count(",") != 2 else e2).focus_set()
                return
            points.extend([(x1, y1, z1), (x2, y2, z2)])

        system.finalize_wireframe3d(name, points)
        dialog.destroy()

    tk.Button(btns, text="Criar Wireframe 3D", command=submit_points).pack()

    # submit com Enter
    dialog.bind("<Return>", lambda _: submit_points())

    # garante scrollregion no início
    dialog.after(50, lambda: canvas.configure(scrollregion=canvas.bbox("all")))


def create_surface3d_dialog(menu_frame, system):
    dialog = tk.Toplevel(menu_frame)
    dialog.title("Superfície Bézier 3D (4x4 por patch)")

    # --- Nome
    tk.Label(dialog, text="Nome do objeto:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    entry_name = tk.Entry(dialog, width=28)
    entry_name.insert(0, "BezierSurface")
    entry_name.grid(row=0, column=1, sticky="we", padx=6, pady=6)

    # --- nu, nv
    tk.Label(dialog, text="Divisões nu × nv:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
    frame_n = tk.Frame(dialog)
    frame_n.grid(row=1, column=1, sticky="w", padx=6, pady=6)
    entry_nu = tk.Entry(frame_n, width=6); entry_nu.insert(0, "12")
    tk.Label(frame_n, text="×").pack(side=tk.LEFT, padx=4)
    entry_nv = tk.Entry(frame_n, width=6); entry_nv.insert(0, "12")
    entry_nu.pack(side=tk.LEFT); entry_nv.pack(side=tk.LEFT)

    # --- Cor
    color_var = tk.StringVar(value=system.default_color)
    def choose_color():
        c = tk.colorchooser.askcolor(title="Cor da superfície")[1]
        if c: color_var.set(c)
    tk.Label(dialog, text="Cor:").grid(row=2, column=0, sticky="w", padx=6, pady=6)
    frame_color = tk.Frame(dialog); frame_color.grid(row=2, column=1, sticky="w", padx=6, pady=6)
    tk.Entry(frame_color, textvariable=color_var, width=14).pack(side=tk.LEFT)
    tk.Button(frame_color, text="Escolher…", command=choose_color).pack(side=tk.LEFT, padx=6)

    # --- Texto dos patches
    tk.Label(dialog, text="Pontos de controle (4x4 por patch; linhas separadas por ';').\n"
                          "Para múltiplos patches, separe por uma linha em branco.").grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(6,2))

    txt = tk.Text(dialog, width=64, height=14)
    txt.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)

    # Exemplo
    example = (
        "(0,0,0),(10,0,0),(20,0,0),(30,0,0);\n"
        "(0,10,0),(10,10,10),(20,10,10),(30,10,0);\n"
        "(0,20,0),(10,20,10),(20,20,10),(30,20,0);\n"
        "(0,30,0),(10,30,0),(20,30,0),(30,30,0)\n"
        "\n"
        # pode colar outro patch abaixo (linha em branco separando)
    )
    txt.insert("1.0", example)

    # layout expandível
    dialog.grid_rowconfigure(4, weight=1)
    dialog.grid_columnconfigure(1, weight=1)

    def on_create():
        name = entry_name.get().strip() or "BezierSurface"
        try:
            nu = max(1, int(entry_nu.get().strip()))
            nv = max(1, int(entry_nv.get().strip()))
        except Exception:
            tk.messagebox.showerror("Erro", "nu e nv devem ser inteiros ≥ 1.", parent=dialog); return

        raw = txt.get("1.0", "end").strip()
        if not raw:
            tk.messagebox.showerror("Erro", "Informe os pontos de controle.", parent=dialog); return

        control_patches = _fallback_parse_multiple_patches(raw)

        if not control_patches:
            tk.messagebox.showerror("Erro", "Nenhum patch 4x4 válido encontrado.", parent=dialog); return

        try:
            patches = [
                BezierPatch(f"{name}_p{i+1}", cp, color=color_var.get(), nu=nu, nv=nv)
                for i, cp in enumerate(control_patches)
            ]
            surf = BezierSurface(name, patches, color=color_var.get())
        except Exception as e:
            tk.messagebox.showerror("Erro", f"Falha ao criar superfície:\n{e}", parent=dialog); return

        system.display.add(surf)
        system.refresh_listbox()
        system.redraw()
        dialog.destroy()

    btns = tk.Frame(dialog); btns.grid(row=5, column=0, columnspan=2, pady=8)
    tk.Button(btns, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=6)
    tk.Button(btns, text="Criar Superfície", command=on_create).pack(side=tk.LEFT, padx=6)
    dialog.bind("<Return>", lambda *_: on_create())


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


def create_window3d_controls(menu_frame, system):
    window3d_frame = tk.LabelFrame(
        menu_frame, text="Window 3D", font=("Arial", 11, "bold"), padx=5, pady=5
    )
    window3d_frame.pack(fill=tk.X, padx=10, pady=8)

    projection_label = tk.Label(
        window3d_frame,
        text=f"Projeção: {'Paralela' if system.camera.projection_mode == 'parallel' else 'Perspectiva'}",
    )
    projection_label.pack(pady=4)
    projection_center = tk.Label(
        window3d_frame,
        text=f"Centro de Projeção: {system.camera.d}",
    )
    projection_center.pack(pady=4)
    system.projection_label = projection_label
    system.projection_center = projection_center

    def update_projection_label():
        system.projection_label.config(
            text=f"Projeção: {'Paralela' if system.camera.projection_mode == 'parallel' else 'Perspectiva'}"
        )
        system.projection_center.config(text=f"Centro de Projeção: {system.camera.d}")

    change_proj_btn = tk.Button(
        window3d_frame,
        text="Alternar Projeção",
        command=lambda: (
            system.camera.toggle_projection(),
            update_projection_label(),
            system.redraw(),
        ),
    )
    change_proj_btn.pack(pady=4, fill=tk.X)

    change_d_frame = tk.Frame(window3d_frame)
    change_d_frame.pack(pady=4, fill=tk.X)
    tk.Label(change_d_frame, text="Centro de Projeção:").pack(side=tk.LEFT)
    btn_decrease_d = tk.Button(
        change_d_frame,
        text="-",
        command=lambda: (
            system.camera.change_d(-10),
            update_projection_label(),
            system.redraw(),
        ),
    )
    btn_decrease_d.pack(side=tk.LEFT, padx=5)
    btn_increase_d = tk.Button(
        change_d_frame,
        text="+",
        command=lambda: (
            system.camera.change_d(10),
            update_projection_label(),
            system.redraw(),
        ),
    )
    btn_increase_d.pack(side=tk.LEFT, padx=5)

    nav_frame = tk.Frame(window3d_frame)
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

    zoom_frame = tk.Frame(window3d_frame)
    zoom_frame.pack(pady=10)

    btn_zoom_in = tk.Button(zoom_frame, text="+", command=lambda: system.zoom(0.9))
    btn_zoom_in.pack(side=tk.LEFT, padx=5)

    btn_zoom_out = tk.Button(zoom_frame, text="-", command=lambda: system.zoom(1.1))
    btn_zoom_out.pack(side=tk.LEFT, padx=5)

    rotate_frame = tk.Frame(window3d_frame)
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

    rotate_3d_frame = tk.Frame(window3d_frame)
    rotate_3d_frame.pack(pady=5, fill=tk.X, padx=5)

    tk.Label(rotate_3d_frame, text="Rotação 3D").grid(row=0, column=0, columnspan=4)
    btn_rotate_3d_up = tk.Button(
        rotate_3d_frame,
        width=4,
        text="▲",
        command=lambda: (system.rotate_3d(pitch_deg=5), system.redraw()),
    )
    btn_rotate_3d_up.grid(row=1, column=1, padx=2, pady=2)
    btn_rotate_3d_left = tk.Button(
        rotate_3d_frame,
        width=4,
        text="◀",
        command=lambda: (system.rotate_3d(yaw_deg=5), system.redraw()),
    )
    btn_rotate_3d_left.grid(row=2, column=0, padx=2, pady=2)
    btn_rotate_3d_right = tk.Button(
        rotate_3d_frame,
        width=4,
        text="▶",
        command=lambda: (system.rotate_3d(yaw_deg=-5), system.redraw()),
    )
    btn_rotate_3d_right.grid(row=2, column=3, padx=2, pady=2)
    btn_rotate_3d_down = tk.Button(
        rotate_3d_frame,
        width=4,
        text="▼",
        command=lambda: (system.rotate_3d(pitch_deg=-5), system.redraw()),
    )
    btn_rotate_3d_down.grid(row=3, column=1, padx=2, pady=2)


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


import re
from graphic_system.point3d import Point3D
_POINT_RE = re.compile(
    r"\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*\)"
)

def _fallback_parse_patch_4x4(text):
    rows = [r.strip() for r in text.strip().split(";") if r.strip()]
    if len(rows) != 4:
        raise ValueError("Esperava 4 linhas separadas por ';'.")
    grid = []
    for r in rows:
        pts = _POINT_RE.findall(r)
        if len(pts) != 4:
            raise ValueError("Cada linha deve ter 4 pontos (x,y,z).")
        grid.append([Point3D(float(x), float(y), float(z)) for (x,y,z) in pts])
    return grid

def _fallback_parse_multiple_patches(text_block):
    chunks = [c for c in re.split(r"\n\s*\n", text_block.strip()) if c.strip()]
    return [_fallback_parse_patch_4x4(chunk) for chunk in chunks]
