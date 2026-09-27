"""Typer CLI application entry point."""

import typer

app = typer.Typer(
    name="musicdl",
    help="MusicDL CLI - Download music from self-hosted NextMusic API",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """MusicDL CLI - Download music from self-hosted NextMusic API."""
    pass
