"""Input helpers shared by the ID input fields."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def extract_id(raw: str) -> str:
    """从用户输入中提取 ID。

    支持两种输入:直接输入数字 ID,或粘贴形如
    ``https://music.xxx.com/xxx?id=2249180720&xxx=xxx`` 的链接(取查询参数
    ``id``)。无法解析出 ``id`` 参数时原样返回,交给后续的数字校验报错。
    """
    value = (raw or "").strip()
    if not value or ("?" not in value and "/" not in value):
        return value
    try:
        params = parse_qs(urlparse(value).query)
    except ValueError:
        return value
    ids = params.get("id")
    if ids and ids[0].strip():
        return ids[0].strip()
    return value
