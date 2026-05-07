import sys
import types
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

fake_pyautogui = types.SimpleNamespace(size=lambda: (1440, 900))
sys.modules.setdefault("pyautogui", fake_pyautogui)

from locators import SmartLocator, VisionLocator


def test_smart_locator_chain_uses_vision_not_florence():
    locator = SmartLocator()

    sources = [locator._source_name(item) for item in locator.locators]

    assert sources == ["accessibility", "ocr", "color", "vision", "fallback", "ai"]
    assert "florence" not in sources


def test_vision_locator_disabled_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    locator = VisionLocator()

    result = locator.find("搜索按钮")

    assert result.success is False
    assert result.source == "vision"
    assert "OPENAI_API_KEY" in result.error


def test_vision_locator_reads_openai_config_from_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example/v1")

    locator = VisionLocator()

    assert locator.api_key == "env-key"
    assert locator.model == "env-model"
    assert locator.base_url == "https://env.example/v1"


def test_vision_locator_reads_openai_config_from_home_env(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".env").write_text(
        "\n".join([
            "OPENAI_API_KEY=file-key",
            "OPENAI_MODEL=file-model",
            "OPENAI_BASE_URL=https://file.example/v1",
        ]),
        encoding="utf-8",
    )

    locator = VisionLocator()

    assert locator.api_key == "file-key"
    assert locator.model == "file-model"
    assert locator.base_url == "https://file.example/v1"


def test_vision_locator_parses_json_bbox():
    locator = VisionLocator(api_key="test-key")
    text = """
    {
      "success": true,
      "x": 100,
      "y": 200,
      "width": 80,
      "height": 40,
      "confidence": 0.88,
      "reasoning": "目标在右上角"
    }
    """

    result = locator._parse_response_text(text)

    assert result.success is True
    assert result.x == 100
    assert result.y == 200
    assert result.width == 80
    assert result.height == 40
    assert result.confidence == 0.88
    assert result.source == "vision"
