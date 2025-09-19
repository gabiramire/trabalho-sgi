import tkinter as tk

from graphic_system.core import GraphicSystem
from gui.menu_bar import create_menu_bar
from gui.side_menu import create_side_menu


def main():
    root = tk.Tk()
    root.title("Computação Gráfica - Sistema Gráfico Interativo (Transformações 2D)")

    # Frame principal (Canvas)
    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
    system = GraphicSystem(root, main_frame)

    create_menu_bar(root, system)
    create_side_menu(root, main_frame, system)

    root.mainloop()


if __name__ == "__main__":
    main()
