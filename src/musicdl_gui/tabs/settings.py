"""Settings tab."""


import flet as ft

from musicdl.config import IP_FETCH_URLS
from musicdl_gui.config import DEFAULT_CONFIG, ConfigManager
from musicdl_gui.snack import show_snack

# 内置公网 IP 获取 API 的显示名(全部参与并发竞速,首个合法值胜出)
_IP_API_LABELS = {
    "https://api.ipify.org?format=json": "ipify (JSON)",
    "https://4.ident.me": "ident.me (IPv4)",
    "https://checkip.amazonaws.com": "checkip.amazonaws.com (IPv4)",
    "https://ipv4.icanhazip.com": "icanhazip (IPv4)",
}
IP_FETCH_APIS = [(url, _IP_API_LABELS.get(url, url)) for url in IP_FETCH_URLS]


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
        saved_ip_api = self._config.get("ip_fetch_url")
        if saved_ip_api not in {url for url, _label in IP_FETCH_APIS}:
            saved_ip_api = DEFAULT_CONFIG["ip_fetch_url"]
        self.ip_api_dropdown = ft.Dropdown(
            label="Public IP API",
            options=[ft.dropdown.Option(url, label) for url, label in IP_FETCH_APIS],
            value=saved_ip_api,
            width=320,
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

        self.controls = [
            ft.Text("API Settings", size=18, weight=ft.FontWeight.BOLD),
            self.base_url_input,
            self.ip_input,
            self.ip_api_dropdown,
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
                controls=[self.save_button, self.reset_button],
            ),
        ]

    async def _show_snack(self, message: str) -> None:
        show_snack(self.page, message)

    async def _on_save(self, e):
        try:
            timeout = float(self.timeout_input.value)
            max_retries = int(self.retries_input.value)
        except ValueError:
            await self._show_snack("Timeout / Max Retries 必须是有效数字")
            return
        # 与 DEFAULT_CONFIG 合并,避免把表单之外的键(naming_template 等)从 config.json 中抹掉
        config = {
            **DEFAULT_CONFIG,
            "base_url": self.base_url_input.value,
            "ip": self.ip_input.value or None,
            "ip_fetch_url": self.ip_api_dropdown.value,
            "timeout": timeout,
            "max_retries": max_retries,
            "output_dir": self.output_dir_input.value,
            "default_level": self.quality_dropdown.value,
        }
        errors = self._config_mgr.validate(config)
        if errors:
            await self._show_snack(f"Validation errors: {', '.join(errors)}")
            return
        self._config_mgr.save(config)
        await self._show_snack("Settings saved")

    async def _on_reset(self, e):
        defaults = DEFAULT_CONFIG.copy()
        self._config_mgr.save(defaults)
        # 刷新表单控件,界面立即反映默认值
        self.base_url_input.value = defaults.get("base_url", "")
        self.ip_input.value = defaults.get("ip") or ""
        self.ip_api_dropdown.value = defaults.get("ip_fetch_url", DEFAULT_CONFIG["ip_fetch_url"])
        self.timeout_input.value = str(defaults.get("timeout", 30.0))
        self.retries_input.value = str(defaults.get("max_retries", 3))
        self.output_dir_input.value = defaults.get("output_dir", "./music")
        self.quality_dropdown.value = defaults.get("default_level", "standard")
        self.update()
        await self._show_snack("Settings reset to defaults")