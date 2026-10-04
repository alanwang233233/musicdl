"""musicdl-cli — Typer application entry point."""

import typer

from musicdl_cli.commands.download import app as download_app

app = typer.Typer(
    name="musicdl",
    help="musicdl — NextMusic API 命令行工具",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(download_app, name="download")


@app.callback()
def main() -> None:
    """musicdl CLI — 下载歌单和单曲。"""


if __name__ == "__main__":
    # PyInstaller 打包与 `python -m musicdl_cli.main` 的直接运行入口
    app()
