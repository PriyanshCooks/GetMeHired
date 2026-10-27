import pytest
from backend.agents.job_matcher import extract_experience_requirement

def test_senior_title_disqualified():
    res = extract_experience_requirement("Senior AI Engineer", "We are looking for an experienced developer.")
    assert res["is_disqualified"] is True
    assert "Disqualified" in res["label"]

def test_lead_title_disqualified():
    res = extract_experience_requirement("Tech Lead - Generative AI", "Lead our team in building LLM applications.")
    assert res["is_disqualified"] is True

def test_high_experience_in_body_disqualified():
    res = extract_experience_requirement("AI Engineer", "Candidate must have 5+ years of experience in distributed systems.")
    assert res["is_disqualified"] is True

def test_fresher_qualified():
    res = extract_experience_requirement("Junior AI Engineer", "Open to fresh graduates and engineers with 0-1 years of hands-on experience.")
    assert res["is_disqualified"] is False
    assert res["score_adjustment"] >= 0

def test_target_range_qualified():
    res = extract_experience_requirement("Associate Software Engineer", "Requires 1-2 years of Python experience.")
    assert res["is_disqualified"] is False
