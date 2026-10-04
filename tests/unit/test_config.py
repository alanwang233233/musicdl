from musicdl_gui.config import ConfigManager


def test_load_default_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    config = manager.load()
    assert config["base_url"] == "https://nextmusic.toubiec.cn"
    assert config["timeout"] == 30.0
    assert config["max_retries"] == 3


def test_save_and_load_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    custom = {
        "base_url": "https://custom.example.com",
        "timeout": 60.0,
        "max_retries": 5,
        "ip": "192.168.1.1",
        "ip_fetch_url": "https://api.ipify.org?format=json",
        "ip_cache_ttl": 3600.0,
        "default_level": "standard",
        "user_agent": None,
        "output_dir": "./music",
        "naming_template": "{singer} - {title}",
    }
    manager.save(custom)
    loaded = manager.load()
    assert loaded["base_url"] == "https://custom.example.com"
    assert loaded["timeout"] == 60.0


def test_validate_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    errors = manager.validate({"timeout": -1})
    assert len(errors) > 0
    assert any("timeout" in e.lower() for e in errors)


def test_get_config_returns_musicdl_config(tmp_path, monkeypatch):
    monkeypatch.setattr("musicdl_gui.config.CONFIG_DIR", tmp_path)
    manager = ConfigManager()
    config = manager.get_config()
    from musicdl import MusicDLConfig
    assert isinstance(config, MusicDLConfig)