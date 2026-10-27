import pytest
from unittest.mock import patch
from backend.agents.outreach_generator import generate_outreach_messages

def test_generate_outreach_messages_fallback():
    mock_job = {
        "title": "Agentic AI Engineer",
        "company": "NeuralScale",
        "job_url": "https://example.com/job/123",
        "is_hidden_startup": False
    }
    mock_contact = {
        "name": "Sarah Chen",
        "role": "CTO & Co-Founder",
        "contact_type": "Founder / CEO"
    }
    mock_profile = {
        "full_name": "Alex Mercer",
        "headline": "AI Systems Engineer | LangGraph • FastAPI",
        "skills": ["Python", "LangGraph", "FastAPI", "Docker"],
        "education": "B.Tech Computer Science",
        "linkedin_url": "https://linkedin.com/in/alex",
        "github_url": "https://github.com/alex",
        "phone": "+1 555-0199"
    }

    # Test fallback path (simulating LLM offline/timeout)
    with patch("backend.agents.outreach_generator.ollama_client.generate", return_value=""), \
         patch("backend.agents.outreach_generator.ollama_client.generate_json", return_value={}):
        outreach = generate_outreach_messages(mock_job, mock_contact, mock_profile)
        assert isinstance(outreach, dict)
        assert "connection_note" in outreach
        assert "referral_request" in outreach
        assert "cold_email_subject" in outreach
        assert "cold_email_body" in outreach

        # Fallback note should be strictly under LinkedIn 300 char limit
        assert len(outreach["connection_note"]) <= 300
        assert "Alex Mercer" in outreach["cold_email_body"]
        assert "NeuralScale" in outreach["connection_note"]
