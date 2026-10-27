import pytest
from backend.config import load_settings, get_profiles, get_active_profile_id, set_active_profile_id

def test_load_settings_structure():
    settings = load_settings()
    assert isinstance(settings, dict)
    assert "stage" in settings
    assert "target_roles" in settings
    assert "target_locations" in settings
    assert "scheduler" in settings
    assert "notifications" in settings
    assert "profiles" in settings

def test_active_profile():
    active_id = get_active_profile_id()
    assert active_id is not None
    profiles = get_profiles()
    assert active_id in profiles

def test_stage_resolution():
    settings = load_settings()
    stage = settings.get("stage", {})
    assert "title" in stage
    assert "description" in stage
    assert "button_text" in stage
    # Ensure templates are resolved
    assert "{name}" not in stage["title"]
    assert "{salary}" not in stage["title"]
