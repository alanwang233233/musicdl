"""Shared SnackBar helper.

每次调用都新建一个 SnackBar 并移除上一个:复用同一实例时,客户端自动
关闭后 Python 侧 open 仍为 True,再次 open=True 不会产生差异补丁,
SnackBar 将永远不再显示。
"""

from __future__ import annotations

import weakref

import flet as ft

_snacks: weakref.WeakKeyDictionary[ft.Page, ft.SnackBar] = weakref.WeakKeyDictionary()


def show_snack(page: ft.Page, message: str) -> None:
    old = _snacks.pop(page, None)
    if old is not None:
        old.open = False
        try:
            page.overlay.remove(old)
        except ValueError:
            pass
    snack = ft.SnackBar(content=ft.Text(message), open=True)
    page.overlay.append(snack)
    _snacks[page] = snack
    page.update()
