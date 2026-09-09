import pytest

from ned.config import Config, ConfigError

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
