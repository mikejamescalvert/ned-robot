import pytest

from ned.config import Config, ConfigError, read_env_file

GOOD = {
    "ANTHROPIC_API_KEY": "a",
    "DEEPGRAM_API_KEY": "d",
    "CARTESIA_API_KEY": "c",
}


def test_from_env_reads_required_and_defaults():
    cfg = Config.from_env(GOOD)
    assert cfg.body == "office"
    assert cfg.model == "claude-sonnet-5"
    assert cfg.effort == "low"
    assert cfg.thinking == "adaptive"
    assert cfg.sample_rate_in == 16000
    assert cfg.audio_device_match == "Array"
    assert cfg.wake_threshold == 0.5
    assert cfg.wake_consecutive_frames == 2
    assert cfg.wake_vad_threshold == 0.5
    assert cfg.wake_verifier_path.name == "hey_ned_verifier.pkl"


def test_missing_secret_is_an_error():
    env = dict(GOOD)
    del env["CARTESIA_API_KEY"]
    with pytest.raises(ConfigError, match="CARTESIA_API_KEY"):
        Config.from_env(env)


def test_bad_number_is_an_error():
    with pytest.raises(ConfigError, match="NED_WAKE_THRESHOLD"):
        Config.from_env({**GOOD, "NED_WAKE_THRESHOLD": "high"})


def test_body_and_overrides():
    cfg = Config.from_env(
        {
            **GOOD,
            "NED_BODY": "downstairs",
            "NED_FOLLOW_UP_SECS": "3",
            "NED_MODEL": "claude-opus-5",
            "NED_THINKING": "disabled",
        }
    )
    assert cfg.body == "downstairs"
    assert cfg.follow_up_secs == 3.0
    assert cfg.model == "claude-opus-5"
    assert cfg.thinking == "disabled"


def test_system_prompt_is_stable_and_names_the_body():
    cfg = Config.from_env({**GOOD, "NED_BODY": "office"})
    a = cfg.system_prompt()
    b = cfg.system_prompt()
    assert a == b, "system prompt must be byte-stable for prompt caching"
    assert "office" in a
    assert "{{body}}" not in a


def test_read_env_file_parses_systemd_style(tmp_path):
    f = tmp_path / "env"
    f.write_text(
        "# comment\n"
        "NED_BODY=office\n"
        'ANTHROPIC_API_KEY="quoted value"\n'
        "export CARTESIA_API_KEY='single'\n"
        "\n"
        "NOT_A_PAIR\n"
        "NED_WAKE_THRESHOLD = 0.35\n"
    )
    assert read_env_file(f) == {
        "NED_BODY": "office",
        "ANTHROPIC_API_KEY": "quoted value",
        "CARTESIA_API_KEY": "single",
        "NED_WAKE_THRESHOLD": "0.35",
    }


def test_read_env_file_missing_is_empty(tmp_path):
    assert read_env_file(tmp_path / "nope") == {}


def test_from_env_falls_back_to_env_file(tmp_path, monkeypatch):
    f = tmp_path / "env"
    f.write_text("ANTHROPIC_API_KEY=a\nDEEPGRAM_API_KEY=d\nCARTESIA_API_KEY=c\nNED_BODY=file\n")
    for k in ("ANTHROPIC_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("NED_ENV_FILE", str(f))
    monkeypatch.setenv("NED_BODY", "shell")  # the shell wins over the file
    cfg = Config.from_env()
    assert cfg.anthropic_api_key == "a"
    assert cfg.body == "shell"
