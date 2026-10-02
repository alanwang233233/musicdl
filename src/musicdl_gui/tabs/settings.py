"""Settings tab."""

import flet as ft
from pathlib import Path

from musicdl_gui.config import ConfigManager


class SettingsTab(ft.Column):
    def __init__(self, config_mgr: ConfigManager):
        super().__init__(expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
        self._config_mgr = config_mgr
        self._config = config_mgr.load()

        self.base_url_input = ft.TextField(
            label="API Base URL",
            value=self._config.get("base_url", ""),
            expand=True,
        )
        self.ip_input = ft.TextField(
            label="IP (optional)",
            value=self._config.get("ip") or "",
            hint_text="Leave empty for auto-detect",
            expand=True,
        )
        self.timeout_input = ft.TextField(
            label="Timeout (seconds)",
            value=str(self._config.get("timeout", 30.0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
        )
        self.retries_input = ft.TextField(
            label="Max Retries",
            value=str(self._config.get("max_retries", 3)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150,
        )
        self.output_dir_input = ft.TextField(
            label="Output Directory",
            value=self._config.get("output_dir", "./music"),
            expand=True,
        )
        self.quality_dropdown = ft.Dropdown(
            label="Default Quality",
            options=[
                ft.dropdown.Option("standard", "Standard"),
                ft.dropdown.Option("hires", "Hi-Res"),
                ft.dropdown.Option("lossless", "Lossless"),
            ],
            value=self._config.get("default_level", "standard"),
            width=150,
        )
        self.save_button = ft.FilledButton(
            content=ft.Text("Save"),
            icon=ft.Icons.SAVE,
            on_click=self._on_save,
        )
        self.reset_button = ft.OutlinedButton(
            content=ft.Text("Reset to Defaults"),
            icon=ft.Icons.RESTORE,
            on_click=self._on_reset,
        )
        self.test_button = ft.OutlinedButton(
            content=ft.Text("Test Connection"),
            icon=ft.Icons.CHECK,
            on_click=self._on_test,
        )

        self.controls = [
            ft.Text("API Settings", size=18, weight=ft.FontWeight.BOLD),
            self.base_url_input,
            self.ip_input,
            ft.Row(
                spacing=8,
                controls=[self.timeout_input, self.retries_input],
            ),
            ft.Divider(),
            ft.Text("Download Settings", size=18, weight=ft.FontWeight.BOLD),
            self.output_dir_input,
            self.quality_dropdown,
            ft.Divider(),
            ft.Row(
                spacing=8,
                controls=[self.save_button, self.reset_button, self.test_button],
            ),
        ]

    def _on_save(self, e):
        config = {
            "base_url": self.base_url_input.value,
            "ip": self.ip_input.value or None,
            "timeout": float(self.timeout_input.value),
            "max_retries": int(self.retries_input.value),
            "output_dir": self.output_dir_input.value,
            "default_level": self.quality_dropdown.value,
        }
        errors = self._config_mgr.validate(config)
        if errors:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Validation errors: {', '.join(errors)}"))
            )
            return
        self._config_mgr.save(config)
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Settings saved"))
        )

    def _on_reset(self, e):
        self._config_mgr.save(self._config_mgr.DEFAULT_CONFIG.copy())
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Settings reset to defaults"))
        )

    async def _on_test(self, e):
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Testing connection..."))
        )