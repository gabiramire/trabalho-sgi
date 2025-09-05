import tkinter as tk


def create_menu_bar(root, system):
  menubar = tk.Menu(root)
  root.config(menu=menubar)

  file_menu = tk.Menu(menubar, tearoff=0)
  menubar.add_cascade(label="Arquivo", menu=file_menu)

  file_menu.add_command(label="Abrir .obj", command=system.load_from_obj)
  file_menu.add_command(label="Salvar como .obj", command=system.save_as_obj)
  file_menu.add_command(label="Sair", command=root.quit)