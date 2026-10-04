"""``flet build`` 打包入口。

flet 要求入口文件位于应用目录根部且名为 main.py(模块名默认取 stem),
因此引导文件固定放在 src/main.py;真正实现保持在 musicdl_gui 包内,
整个 src/ 目录(musicdl / musicdl_cli / musicdl_gui)会随之打入应用包。
"""

import flet as ft

from musicdl_gui.main import main

ft.run(main)
