import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  Search,
  Users,
  UserCheck,
  Send,
  Sparkles,
  ExternalLink,
  Copy,
  Check,
  Smartphone,
  Mail,
  Sliders,
  RefreshCw,
  FileText,
  Upload,
  ChevronRight,
  TrendingUp,
  MapPin,
  DollarSign,
  Building,
  Target,
  ArrowRight,
  ShieldCheck,
  MessageSquare,
  AlertCircle,
  Clock,
  Play,
  Layers,
  Link,
  Cpu,
  Calendar,
  CheckCircle,
  BellRing,
  Trash2
} from 'lucide-react';

export default function App() {
  const [activeProfileId, setActiveProfileId] = useState('');
  const [profiles, setProfiles] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobContacts, setJobContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(false);

  // CRM State
  const [applications, setApplications] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [dueFollowups, setDueFollowups] = useState([]);

  // Outreach Generator State
  const [selectedContact, setSelectedContact] = useState(null);
  const [outreachTone, setOutreachTone] = useState('founder');
  const [generatedMessages, setGeneratedMessages] = useState(null);
  const [generatingOutreach, setGeneratingOutreach] = useState(false);
  const [activeMessageType, setActiveMessageType] = useState('connection_note');
  const [copiedKey, setCopiedKey] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [minScore, setMinScore] = useState(0);

  // Health, Pipeline & Settings
  const [health, setHealth] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState(null);
  const [settings, setSettings] = useState(null);
  const [profile, setProfile] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [testNotifStatus, setTestNotifStatus] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [queueCount, setQueueCount] = useState(0);

  // Toast Notification
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4500);
  };

  // Fetch initial data
  useEffect(() => {
    fetchHealth();
    fetchPipelineStatus();
    fetchSettings();
    fetchProfiles();

    // Auto-refresh jobs, CRM, and pipeline status every 15 seconds
    const interval = setInterval(() => {
      fetchPipelineStatus();
      fetchJobs(false);
      fetchCrmData();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await fetch('/api/profiles');
      if (res.ok) {
        const d = await res.json();
        const profileList = d.profiles || [];
        setProfiles(profileList);
        const activeId = d.active_profile_id || (profileList[0]?.id || 'default');
        setActiveProfileId(activeId);
        fetchProfile(activeId);
        fetchJobs(true, activeId);
        fetchCrmData(activeId);
      }
    } catch (e) {
      console.error('Fetch profiles failed', e);
    }
  };

  const handleSwitchProfile = async (targetId) => {
    try {
      setActiveProfileId(targetId);
      const res = await fetch('/api/profiles/active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: targetId })
      });
      if (res.ok) {
        const matched = profiles.find(p => p.id === targetId);
        const candidateName = matched?.full_name || targetId;
        showToast(`Switched active profile to ${candidateName}`);
        fetchJobs(true, targetId);
        fetchProfile(targetId);
        fetchCrmData(targetId);
      }
    } catch (e) {
      showToast('Error switching profile.');
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) setHealth(await res.json());
    } catch (e) {
      console.error('Health check failed', e);
    }
  };

  const fetchPipelineStatus = async () => {
    try {
      const res = await fetch('/api/pipeline/status');
      if (res.ok) setPipelineStatus(await res.json());
    } catch (e) {
      console.error('Fetch pipeline status failed', e);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) setSettings(await res.json());
    } catch (e) {
      console.error('Fetch settings failed', e);
    }
  };

  const fetchProfile = async (pid = null) => {
    const targetPid = pid || activeProfileId;
    try {
      const res = await fetch(`/api/profile?profile_id=${targetPid}`);
      if (res.ok) setProfile(await res.json());
    } catch (e) {
      console.error('Fetch profile failed', e);
    }
  };

  const fetchJobs = async (showLoading = true, pid = null) => {
    if (showLoading) setLoadingJobs(true);
    const targetPid = pid || activeProfileId;
    try {
      const res = await fetch(`/api/jobs?view=enriched&profile_id=${targetPid}`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
        if (data.queue_count !== undefined) {
          setQueueCount(data.queue_count);
        }
      }
    } catch (e) {
      console.error('Fetch jobs failed', e);
    } finally {
      if (showLoading) setLoadingJobs(false);
    }
  };

  const fetchCrmData = async (pid = null) => {
    const targetPid = pid || activeProfileId;
    try {
      const [appRes, convRes, dueRes] = await Promise.all([
        fetch(`/api/crm/applications?profile_id=${targetPid}`),
        fetch(`/api/crm/conversations?profile_id=${targetPid}`),
        fetch(`/api/crm/followups-due?profile_id=${targetPid}`)
      ]);
      if (appRes.ok) {
        const d = await appRes.json();
        setApplications(d.applications || []);
      }
      if (convRes.ok) {
        const d = await convRes.json();
        setConversations(d.conversations || []);
      }
      if (dueRes.ok) {
        const d = await dueRes.json();
        setDueFollowups(d.followups_due || []);
      }
    } catch (e) {
      console.error('Error fetching CRM data', e);
    }
  };

  const triggerFullPipeline = async () => {
    setPipelineRunning(true);
    showToast('🚀 Scanning AI Startups (Gurugram, Pune, Surat, Remote), matching LangGraph/MCP fit, and identifying Founders...');
    try {
      const res = await fetch('/api/pipeline/run', { method: 'POST' });
      if (res.ok) {
        showToast('Autonomous pipeline running! Live jobs & founder leads will appear shortly.');
        setTimeout(() => {
          fetchJobs();
          fetchPipelineStatus();
          setPipelineRunning(false);
        }, 5000);
      }
    } catch (e) {
      showToast('Error triggering pipeline.');
      setPipelineRunning(false);
    }
  };

  const handleCleanDatabase = async () => {
    if (!window.confirm("Are you sure you want to clean all data and start completely fresh? This will remove all tracked jobs, contacts, outreach drafts, and CRM items.")) {
      return;
    }
    try {
      const res = await fetch('/api/database/clean', { method: 'POST' });
      if (res.ok) {
        setPipelineRunning(false);
        setQueueCount(0);
        setJobs([]);
        setApplications([]);
        setConversations([]);
        setDueFollowups([]);
        setSelectedJob(null);
        showToast('🧹 Database cleaned and running agent stopped! Ready to re-trigger.');
        fetchPipelineStatus();
      }
    } catch (e) {
      showToast('Error cleaning database.');
    }
  };

  const selectJobForDeepDive = async (job) => {
    setSelectedJob(job);
    setLoadingContacts(true);
    setGeneratedMessages(null);
    try {
      const res = await fetch(`/api/jobs/${job.id}`);
      if (res.ok) {
        const data = await res.json();
        setJobContacts(data.contacts || []);
        if (data.contacts && data.contacts.length > 0) {
          setSelectedContact(data.contacts[0]);
        }
        if (data.outreach_history && data.outreach_history.length > 0) {
          try {
            const parsed = JSON.parse(data.outreach_history[0].content);
            setGeneratedMessages(parsed);
          } catch (e) {}
        }
      }
    } catch (e) {
      console.error('Failed to load job details', e);
    } finally {
      setLoadingContacts(false);
    }
  };

  const handleGenerateOutreach = async (contact = selectedContact, tone = outreachTone) => {
    if (!selectedJob) return;
    setGeneratingOutreach(true);
    try {
      const res = await fetch(`/api/jobs/${selectedJob.id}/outreach`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contact_id: contact ? contact.id : null,
          tone: tone
        })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedMessages(data.messages);
        showToast('Generated tailored pitch with local AI!');
      }
    } catch (e) {
      showToast('Error generating message.');
    } finally {
      setGeneratingOutreach(false);
    }
  };

  const logToCrmTracker = async (contact, message, followUpNote) => {
    if (!selectedJob || !contact) return;
    try {
      const res = await fetch('/api/crm/quick-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: selectedJob.company,
          role: selectedJob.title,
          job_url: selectedJob.job_url,
          person_name: contact.role,
          person_role: contact.contact_type,
          profile_url: contact.linkedin_search_url,
          message_sent: message || '',
          follow_up_note: followUpNote || generatedMessages?.follow_up_note || '',
          candidate_id: activeProfileId
        })
      });
      if (res.ok) {
        showToast(`📌 Logged to CRM! Auto follow-up alert scheduled in 3 days.`);
        fetchCrmData();
      }
    } catch (e) {
      showToast('Error logging to CRM.');
    }
  };

  const updateConversationStatus = async (conv, newStatus) => {
    try {
      const res = await fetch('/api/crm/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...conv,
          candidate_id: activeProfileId,
          status: newStatus
        })
      });
      if (res.ok) {
        showToast(`Status updated to: ${newStatus}`);
        fetchCrmData();
      }
    } catch (e) {
      showToast('Failed to update status.');
    }
  };

  const deleteApplicationItem = async (appId) => {
    try {
      await fetch(`/api/crm/applications/${appId}?profile_id=${activeProfileId}`, { method: 'DELETE' });
      showToast('Removed from applications.');
      fetchCrmData();
    } catch (e) {}
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    showToast('Copied to clipboard!');
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handleResumeUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    showToast(`Parsing real resume for ${profile?.full_name || 'Candidate'}...`);
    try {
      const res = await fetch(`/api/profile/upload-resume?profile_id=${activeProfileId}`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Resume uploaded! Extracted ${data.characters_extracted} characters.`);
        fetchProfile();
      } else {
        const err = await res.json();
        showToast(`Upload failed: ${err.detail || 'Error'}`);
      }
    } catch (e) {
      showToast('Error uploading resume.');
    }
  };

  const saveProfileChanges = async () => {
    try {
      const res = await fetch(`/api/profile?profile_id=${activeProfileId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
      });
      if (res.ok) showToast(`${profile.full_name || 'Candidate'} profile and credentials saved!`);
    } catch (e) {
      showToast('Failed to save profile.');
    }
  };

  const saveSettingsChanges = async () => {
    setSavingSettings(true);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        showToast('Agent directives and settings saved!');
        fetchHealth();
        fetchPipelineStatus();
      }
    } catch (e) {
      showToast('Failed to save settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  const testIphoneNotification = async () => {
    const currentProfile = profiles.find(p => p.id === activeProfileId);
    const topic = currentProfile?.notification_topic || settings.notifications?.ntfy_topic || 'getmehired_alerts';
    const name = currentProfile?.full_name || profile?.full_name || 'Candidate';

    setTestNotifStatus(`Sending test ping to ${name}'s iPhone (${topic})...`);
    try {
      const res = await fetch('/api/notifications/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'ntfy', topic: topic, name: name })
      });
      const data = await res.json();
      if (data.success) {
        setTestNotifStatus(`✅ Ping sent to ${topic}! Check ${name}'s iPhone.`);
        showToast(`Push alert sent to ${name}'s iPhone!`);
      } else {
        setTestNotifStatus(`⚠️ Failed: ${data.error || 'Check topic'}`);
      }
    } catch (e) {
      setTestNotifStatus('Error sending notification.');
    }
  };

  // Filtered jobs
  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.location.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSource =
      sourceFilter === 'all' || job.source.toLowerCase() === sourceFilter.toLowerCase();
    const matchesScore = job.match_score >= minScore;
    return matchesSearch && matchesSource && matchesScore;
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            background: 'linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)',
            color: '#fff',
            padding: '12px 24px',
            borderRadius: 12,
            boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            zIndex: 9999,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            animation: 'fadeIn 0.3s ease'
          }}
        >
          <Sparkles size={18} />
          {toastMessage}
        </div>
      )}

      {/* Top Navbar */}
      <header
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          background: 'rgba(9, 13, 22, 0.9)',
          backdropFilter: 'blur(20px)',
          position: 'sticky',
          top: 0,
          zIndex: 100
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 16
          }}
        >
          {/* Logo & Agent Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(99, 102, 241, 0.5)'
              }}
            >
              <Cpu size={24} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h1 style={{ fontSize: '1.45rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
                  GetMeHired
                </h1>
                <span
                  style={{
                    fontSize: '0.7rem',
                    background: 'rgba(99, 102, 241, 0.2)',
                    color: '#a5b4fc',
                    border: '1px solid rgba(99, 102, 241, 0.4)',
                    padding: '2px 8px',
                    borderRadius: 6,
                    fontWeight: 700
                  }}
                >
                  {settings?.stage?.badge_text || `${(profile?.full_name || 'CANDIDATE').toUpperCase()} • ${settings?.target_salary_display || '7-10 LPA'}`}
                </span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    padding: '2px 8px',
                    borderRadius: 6,
                    fontWeight: 700
                  }}
                >
                  TARGET: {settings?.experience_level || '0-3 YRS'} • ALL COMPANIES
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {settings?.stage?.subtitle || `${(settings?.target_roles || ['AI Engineer']).slice(0, 3).join(' • ')} • ${(settings?.target_locations || ['Remote']).join(' • ')} ($0 Spend)`}
              </p>
            </div>
          </div>

          {/* Candidate Switcher, Model Status & Pipeline Trigger */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            {/* Dynamic Multi-Profile Switcher */}
            {profiles.length > 1 ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: 10,
                  padding: 3,
                  gap: 4
                }}
              >
                {profiles.map((p) => (
                  <button
                    key={p.id}
                    id={`profile-toggle-${p.id}`}
                    onClick={() => handleSwitchProfile(p.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '6px 13px',
                      borderRadius: 8,
                      border: 'none',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      background: activeProfileId === p.id
                        ? 'linear-gradient(135deg, #6366f1, #4f46e5)'
                        : 'transparent',
                      color: activeProfileId === p.id ? '#fff' : 'var(--text-muted)',
                      boxShadow: activeProfileId === p.id ? '0 2px 10px rgba(99, 102, 241, 0.4)' : 'none'
                    }}
                  >
                    <span>👤</span>
                    <span>{p.full_name?.split(' ')[0] || p.id}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 14px',
                  borderRadius: 8,
                  background: 'rgba(99, 102, 241, 0.15)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#a5b4fc'
                }}
              >
                <span>👤</span>
                <span>{profile?.full_name || 'Active Profile'}</span>
              </div>
            )}

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 14px',
                borderRadius: 20,
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.82rem'
              }}
            >
              <span className="pulse-indicator" />
              <span style={{ color: 'var(--text-muted)' }}>Local LLM:</span>
              <strong style={{ color: '#fff' }}>{health?.active_model || 'qwen3.5:4b'}</strong>
            </div>

            <button
              onClick={handleCleanDatabase}
              title="Wipe database to start fresh"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 14px',
                borderRadius: 8,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#f87171',
                fontSize: '0.84rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <Trash2 size={14} />
              Reset & Clean
            </button>

            <button
              onClick={triggerFullPipeline}
              disabled={pipelineRunning}
              className="btn-primary"
              style={{ padding: '8px 18px', fontSize: '0.88rem' }}
            >
              <Play
                size={15}
                style={{
                  animation: pipelineRunning ? 'spin 1s linear infinite' : 'none'
                }}
              />
              {pipelineRunning ? 'Hunting Opportunities...' : 'Run Cycle Now'}
            </button>
          </div>
        </div>

        {/* Autonomous Status Ribbon */}
        <div style={{ background: 'rgba(15, 20, 32, 0.95)', borderTop: '1px solid var(--border-subtle)', padding: '8px 24px' }}>
          <div style={{ maxWidth: 1400, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.82rem', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#34d399', fontWeight: 600 }}>
                <span className="pulse-indicator" />
                <span>Autonomous {pipelineStatus?.interval_minutes || 45}-Min Runner: ACTIVE</span>
              </div>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span style={{ color: 'var(--text-muted)' }}>
                Target: <strong>Agentic AI / GenAI (0-3 Yrs, 7-10 LPA)</strong>
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              {pipelineStatus?.enrichment_running && (
                <span style={{ color: '#818cf8', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
                  <Cpu size={14} style={{ animation: 'pulse 1.5s infinite' }} />
                  AI Enriching ({pipelineStatus.pending_enrichment || queueCount || 0} queued)
                </span>
              )}
              {queueCount > 0 && !pipelineStatus?.enrichment_running && (
                <span style={{ color: '#fbbf24', display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
                  <Clock size={13} />
                  {queueCount} in intake queue
                </span>
              )}
              {dueFollowups.length > 0 && (
                <span style={{ color: '#f59e0b', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <BellRing size={14} /> {dueFollowups.length} Follow-up{dueFollowups.length > 1 ? 's' : ''} Due!
                </span>
              )}
              <span style={{ color: 'var(--text-muted)' }}>
                AI-Enriched Opportunities: <strong style={{ color: '#34d399' }}>{jobs.length}</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '10px 24px 12px 24px' }}>
          <div className="tab-nav">
            <button
              className={`tab-btn ${activeTab === 'jobs' ? 'active' : ''}`}
              onClick={() => setActiveTab('jobs')}
            >
              <Briefcase size={16} />
              Matched Opportunities ({filteredJobs.length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'contacts' ? 'active' : ''}`}
              onClick={() => setActiveTab('contacts')}
            >
              <Users size={16} />
              Decision-Makers & Referral PoCs
            </button>
            <button
              className={`tab-btn ${activeTab === 'crm' ? 'active' : ''}`}
              onClick={() => setActiveTab('crm')}
            >
              <Calendar size={16} />
              Application & Follow-up CRM
              {dueFollowups.length > 0 && (
                <span style={{ background: '#f59e0b', color: '#000', fontSize: '0.7rem', padding: '1px 6px', borderRadius: 10, fontWeight: 800 }}>
                  {dueFollowups.length}
                </span>
              )}
            </button>
            <button
              className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              <FileText size={16} />
              {profile?.full_name?.split(' ')[0] || 'Candidate'} Profile & Resume
            </button>
            <button
              className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              <Sliders size={16} />
              Directives & iPhone Push
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '24px', flex: 1, width: '100%' }}>
        {/* TAB 1: JOBS & HIDDEN STARTUPS */}
        {activeTab === 'jobs' && (
          <div>
            {/* Filter Bar */}
            <div
              className="glass-panel"
              style={{
                padding: '16px 20px',
                marginBottom: 24,
                display: 'flex',
                gap: 16,
                flexWrap: 'wrap',
                alignItems: 'center'
              }}
            >
              <div style={{ flex: 1, minWidth: 240, position: 'relative' }}>
                <Search
                  size={18}
                  style={{ position: 'absolute', left: 14, top: 12, color: 'var(--text-dim)' }}
                />
                <input
                  type="text"
                  placeholder="Filter AI jobs & startups by title, company or location (Gurugram, Pune, Surat, Remote)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ paddingLeft: 42 }}
                />
              </div>

              <div style={{ minWidth: 170 }}>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                >
                  <option value="all">All Sources</option>
                  <option value="hidden startup lead">Hidden Startup Leads</option>
                  <option value="wellfound">Wellfound (Startups)</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="naukri">Naukri (India)</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 200 }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  Min Match: <strong>{minScore}%</strong>
                </span>
                <input
                  type="range"
                  min="0"
                  max="95"
                  step="5"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  style={{ cursor: 'pointer' }}
                />
              </div>
            </div>

            {/* Empty State */}
            {jobs.length === 0 && !loadingJobs && (
              <div
                className="glass-panel"
                style={{ padding: 48, textAlign: 'center', maxWidth: 720, margin: '40px auto' }}
              >
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: '50%',
                    background: 'rgba(99, 102, 241, 0.15)',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 20px auto'
                  }}
                >
                  <ShieldCheck size={32} color="#6366f1" />
                </div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8 }}>
                  {settings?.stage?.title || `Stage Set for ${profile?.full_name || 'Candidate'} (${settings?.target_salary_display || '7-10 LPA'})`}
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', lineHeight: 1.6, marginBottom: 24 }}>
                  {settings?.stage?.description || `Your profile and search preferences are pre-loaded. Click below to launch the hunt across ${(settings?.target_locations || ['Remote']).join(', ')}.`}
                </p>
                <button
                  onClick={triggerFullPipeline}
                  disabled={pipelineRunning}
                  className="btn-primary"
                  style={{ padding: '12px 28px', fontSize: '1rem' }}
                >
                  <Play size={18} />
                  {pipelineRunning ? 'Executing Pipeline...' : (settings?.stage?.button_text || 'Start Live Startup & Job Hunt')}
                </button>
              </div>
            )}

            {/* Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 20 }}>
              {filteredJobs.map((job) => {
                const isHighMatch = job.match_score >= 75;
                const isHidden = job.source.toLowerCase().includes('hidden');

                return (
                  <div
                    key={job.id}
                    className="glass-panel"
                    style={{
                      padding: 24,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      position: 'relative',
                      border: isHidden ? '1px solid rgba(168, 85, 247, 0.4)' : undefined
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 8 }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                            <span className={`badge ${isHidden ? 'badge-role-hm' : 'badge-source-linkedin'}`}>
                              {job.source}
                            </span>
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                              {job.date_posted || 'Active'}
                            </span>
                          </div>
                          <h3 style={{ fontSize: '1.18rem', fontWeight: 700, lineHeight: 1.3 }}>
                            {job.title}
                          </h3>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                            <Building size={15} />
                            <strong style={{ color: '#fff' }}>{job.company}</strong>
                          </div>
                        </div>

                        <div
                          style={{
                            textAlign: 'center',
                            background: isHighMatch ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            border: `1px solid ${isHighMatch ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
                            padding: '8px 12px',
                            borderRadius: 12,
                            minWidth: 70
                          }}
                        >
                          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: isHighMatch ? '#34d399' : '#fbbf24' }}>
                            {job.match_score || 88}%
                          </div>
                          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-muted)' }}>
                            AI FIT
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, margin: '12px 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                          <MapPin size={14} color="#06b6d4" />
                          <span>{job.location}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                          <DollarSign size={14} color="#10b981" />
                          <span style={{ color: '#34d399', fontWeight: 600 }}>{job.salary || '₹7-10 LPA'}</span>
                        </div>
                        {job.experience_required && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <Clock size={14} color={job.experience_required.includes('0-1') ? '#34d399' : '#818cf8'} />
                            <span
                              style={{
                                color: job.experience_required.includes('0-1') ? '#34d399' : (job.experience_required.includes('0-3') ? '#38bdf8' : '#cbd5e1'),
                                fontWeight: 700,
                                background: job.experience_required.includes('0-1') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                                padding: '1px 8px',
                                borderRadius: 6,
                                border: job.experience_required.includes('0-1') ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(255, 255, 255, 0.1)'
                              }}
                            >
                              {job.experience_required.includes('0-1') ? `⭐ ${job.experience_required}` : job.experience_required}
                            </span>
                          </div>
                        )}
                      </div>

                      {job.match_rationale && (
                        <p style={{ fontSize: '0.85rem', color: '#cbd5e1', background: 'rgba(255, 255, 255, 0.03)', padding: '10px 14px', borderRadius: 8, margin: '10px 0', borderLeft: '3px solid #6366f1' }}>
                          {job.match_rationale}
                        </p>
                      )}

                      {job.matching_skills && job.matching_skills.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '10px 0' }}>
                          {job.matching_skills.slice(0, 4).map((skill, i) => (
                            <span
                              key={i}
                              style={{
                                fontSize: '0.75rem',
                                background: 'rgba(99, 102, 241, 0.15)',
                                color: '#a5b4fc',
                                padding: '2px 8px',
                                borderRadius: 6,
                                border: '1px solid rgba(99, 102, 241, 0.25)'
                              }}
                            >
                              ✓ {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: 10, marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                      <button
                        onClick={() => selectJobForDeepDive(job)}
                        className="btn-primary"
                        style={{ flex: 1, justifyContent: 'center' }}
                      >
                        <Users size={16} />
                        Founders & Outreach
                      </button>

                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-secondary"
                        style={{ padding: '8px 14px' }}
                        title="Open Direct Link"
                      >
                        <ExternalLink size={16} />
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: DECISION MAKERS & REFERRAL POC MATRIX */}
        {activeTab === 'contacts' && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800 }}>Decision-Makers & Referral Point-of-Contact (PoC) Matrix</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Direct profiles of Founders, CEOs, Engineering Directors, and HR Leads across all matched companies with direct profile links for backdoor interviews and employee referrals.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 20 }}>
              {jobs.map((job) => (
                <div key={job.id} className="glass-panel" style={{ padding: 22 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                    <div>
                      <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>{job.company}</h4>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {job.location} • ₹7-10 LPA
                      </div>
                      {job.experience_required && (
                        <div style={{ marginTop: 4 }}>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              padding: '2px 8px',
                              borderRadius: 6,
                              background: job.experience_required.includes('0-1') ? 'rgba(52, 211, 153, 0.15)' : 'rgba(129, 140, 248, 0.15)',
                              color: job.experience_required.includes('0-1') ? '#34d399' : '#818cf8',
                              border: '1px solid rgba(255,255,255,0.08)',
                              fontWeight: 600
                            }}
                          >
                            {job.experience_required}
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="badge badge-match-high" style={{ fontSize: '0.85rem' }}>
                      Fit: {job.match_score || 90}%
                    </span>
                  </div>

                  {/* LinkedIn Company People Section Shortcut */}
                  <a
                    href={`https://www.linkedin.com/company/${job.company.toLowerCase().replace(/[^a-z0-9]/g, '')}/people/?keywords=AI`}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'rgba(10, 102, 194, 0.12)',
                      border: '1px solid rgba(10, 102, 194, 0.3)',
                      padding: '8px 12px',
                      borderRadius: 8,
                      marginBottom: 12,
                      color: '#38bdf8',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      textDecoration: 'none'
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Users size={14} /> Open {job.company} People on LinkedIn (AI Engineers, Leads, HR)
                    </span>
                    <ExternalLink size={12} />
                  </a>

                  {/* Contacts List */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {(job.contacts && job.contacts.length > 0) ? (
                      job.contacts.map((contact, idx) => {
                        const directUrl = contact.profile_url || contact.linkedin_search_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(contact.name)}`;
                        const isVerified = contact.is_verified_person || (directUrl && directUrl.includes('linkedin.com/in/'));
                        return (
                          <div
                            key={contact.id || idx}
                            style={{
                              background: 'rgba(255, 255, 255, 0.03)',
                              padding: '12px 14px',
                              borderRadius: 10,
                              border: isVerified ? '1px solid rgba(56, 189, 248, 0.25)' : '1px solid var(--border-subtle)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              gap: 12
                            }}
                          >
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                                <span className="badge badge-role-hm" style={{ fontSize: '0.72rem' }}>
                                  {contact.contact_type || 'Decision Maker'} ({contact.potential_score || 95}/100 Impact)
                                </span>
                                {isVerified && (
                                  <span style={{ fontSize: '0.7rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 600 }}>
                                    <ShieldCheck size={11} /> Verified Profile
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '0.98rem', fontWeight: 700, marginTop: 4, color: '#f8fafc' }}>
                                {contact.name}
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 2 }}>
                                {contact.role}
                              </div>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end', flexShrink: 0 }}>
                              <a
                                href={directUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="btn-secondary"
                                style={{
                                  fontSize: '0.78rem',
                                  padding: '6px 12px',
                                  background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(99, 102, 241, 0.2))',
                                  borderColor: 'rgba(56, 189, 248, 0.4)',
                                  color: '#38bdf8',
                                  fontWeight: 600,
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 5
                                }}
                              >
                                Visit Profile <ExternalLink size={12} />
                              </a>
                              <button
                                onClick={() => {
                                  setSelectedJob(job);
                                  setSelectedContact(contact);
                                  setActiveTab('crm');
                                }}
                                className="btn-secondary"
                                style={{ fontSize: '0.72rem', padding: '4px 8px', color: 'var(--text-muted)' }}
                                title="Add conversation to CRM"
                              >
                                Track in CRM
                              </button>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: 8 }}>
                        Discovering verified contacts and leadership profiles...
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => selectJobForDeepDive(job)}
                    className="btn-primary"
                    style={{ width: '100%', marginTop: 14, justifyContent: 'center' }}
                  >
                    View Job Deep-Dive & Directives
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: APPLICATION & FOLLOW-UP CRM */}
        {activeTab === 'crm' && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800 }}>Application & Conversation CRM Tracker</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Track every job you applied to, every founder/lead you messaged, and automatically get alerted when a 3-day follow-up is due.
              </p>
            </div>

            {/* Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
              <div className="glass-panel" style={{ padding: '16px 20px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Applications Tracked</span>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: 4 }}>{applications.length}</div>
              </div>
              <div className="glass-panel" style={{ padding: '16px 20px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>People Contacted</span>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: 4, color: '#38bdf8' }}>{conversations.length}</div>
              </div>
              <div className="glass-panel" style={{ padding: '16px 20px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Follow-ups Due Today</span>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: 4, color: dueFollowups.length > 0 ? '#f59e0b' : '#34d399' }}>
                  {dueFollowups.length}
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '16px 20px' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Interviews Scheduled</span>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: 4, color: '#34d399' }}>
                  {applications.filter(a => a.status === 'Interviewing').length}
                </div>
              </div>
            </div>

            {/* Follow-ups Due Alert Box */}
            {dueFollowups.length > 0 && (
              <div className="glass-panel" style={{ padding: 24, marginBottom: 24, border: '1px solid rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.05)' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <BellRing size={20} /> Action Required: {dueFollowups.length} Follow-up{dueFollowups.length > 1 ? 's' : ''} Due!
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {dueFollowups.map((conv) => (
                    <div key={conv.id} style={{ background: 'rgba(0, 0, 0, 0.3)', padding: 16, borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.98rem' }}>{conv.person_name} ({conv.person_role}) • <span style={{ color: '#38bdf8' }}>{conv.company}</span></div>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 2 }}>Sent on: {conv.date_sent} | Follow-up due: {conv.follow_up_due_date}</div>
                        {conv.follow_up_note && (
                          <div style={{ fontSize: '0.84rem', color: '#cbd5e1', background: 'rgba(255, 255, 255, 0.04)', padding: '6px 10px', borderRadius: 6, marginTop: 8 }}>
                            "{conv.follow_up_note.slice(0, 150)}..."
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {conv.follow_up_note && (
                          <button
                            onClick={() => copyToClipboard(conv.follow_up_note, `crm_${conv.id}`)}
                            className="btn-primary"
                            style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                          >
                            <Copy size={13} /> {copiedKey === `crm_${conv.id}` ? 'Copied Nudge!' : 'Copy Follow-up'}
                          </button>
                        )}
                        <button
                          onClick={() => updateConversationStatus(conv, 'Follow-up Sent')}
                          className="btn-secondary"
                          style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                        >
                          Mark Sent
                        </button>
                        <button
                          onClick={() => updateConversationStatus(conv, 'Call Scheduled')}
                          className="btn-success"
                          style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                        >
                          🎉 Interview!
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Conversations & Applications List */}
            <div className="glass-panel" style={{ padding: 24 }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>
                Active Networking & Outreach Conversations
              </h3>
              {conversations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)' }}>
                  No messages logged yet. When you copy an outreach note from a job drawer, click <strong>"📌 Log to CRM Tracker"</strong> to monitor replies and get follow-up reminders.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {conversations.map((c) => (
                    <div key={c.id} style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', padding: 16, borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className="badge badge-match-high">{c.status}</span>
                          <strong style={{ fontSize: '1rem' }}>{c.company}</strong>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>({c.person_name} - {c.person_role})</span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: 4 }}>
                          Date Sent: {c.date_sent} • Follow-up Due: {c.follow_up_due_date}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          value={c.status}
                          onChange={(e) => updateConversationStatus(c, e.target.value)}
                          style={{ padding: '6px 10px', fontSize: '0.82rem', width: 'auto' }}
                        >
                          <option value="Waiting Reply">Waiting Reply</option>
                          <option value="Follow-up Due">Follow-up Due</option>
                          <option value="Follow-up Sent">Follow-up Sent</option>
                          <option value="Replied">Replied</option>
                          <option value="Call Scheduled">Call Scheduled</option>
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: CANDIDATE PROFILE & CREDENTIALS */}
        {activeTab === 'profile' && (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800 }}>
                {profile?.full_name || 'Candidate'} — Profile & Resume Hub
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                {profile?.headline || 'Manage your candidate profile credentials, resume, and skills for autonomous matching.'}
              </p>
            </div>

            <div className="glass-panel" style={{ padding: 28, marginBottom: 24 }}>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Upload size={18} color="#6366f1" /> Upload / Replace Resume (PDF, TXT, or MD)
              </h3>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={handleResumeUpload}
                style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.05)', cursor: 'pointer' }}
              />
            </div>

            {profile && (
              <div className="glass-panel" style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
                <h3 style={{ fontSize: '1.15rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 10 }}>
                  🔗 Connected Career Accounts
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      LinkedIn Profile URL
                    </label>
                    <input
                      type="text"
                      value={profile.linkedin_url || ''}
                      onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Naukri Profile URL
                    </label>
                    <input
                      type="text"
                      value={profile.naukri_url || ''}
                      onChange={(e) => setProfile({ ...profile, naukri_url: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Wellfound (AngelList) Profile URL
                    </label>
                    <input
                      type="text"
                      value={profile.wellfound_url || ''}
                      onChange={(e) => setProfile({ ...profile, wellfound_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      GitHub Link
                    </label>
                    <input
                      type="text"
                      value={profile.github_url || ''}
                      onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                    />
                  </div>
                </div>

                {/* Candidate Background */}
                <h3 style={{ fontSize: '1.15rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 10, marginTop: 10 }}>
                  👤 Candidate Background & Skills
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={profile.full_name || ''}
                      onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Professional Headline
                    </label>
                    <input
                      type="text"
                      value={profile.headline || ''}
                      onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                    Core Technical Skills & Frameworks
                  </label>
                  <input
                    type="text"
                    value={Array.isArray(profile.skills) ? profile.skills.join(', ') : profile.skills || ''}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        skills: e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                      })
                    }
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                    Resume Text / Work Experience History
                  </label>
                  <textarea
                    rows={8}
                    value={profile.resume_text || ''}
                    onChange={(e) => setProfile({ ...profile, resume_text: e.target.value })}
                  />
                </div>

                <button onClick={saveProfileChanges} className="btn-success" style={{ alignSelf: 'flex-start' }}>
                  <Check size={16} /> Save Profile Changes
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: AGENT DIRECTIVES & IPHONE PUSH */}
        {activeTab === 'settings' && (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800 }}>Agent Directives & Strategy Settings</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Instruct your AI agent, set startup size preferences (50-300 employees), and configure iPhone lock screen push notifications.
              </p>
            </div>

            {settings && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                {/* 1. Agent Directives */}
                <div className="glass-panel" style={{ padding: 28, border: '1px solid var(--border-active)' }}>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Sparkles size={18} color="#6366f1" /> 🧠 Instruct Your AI Agent (Custom Directives)
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 14 }}>
                    Your agent uses these exact rules when reasoning on jobs, calculating fit, and drafting founder pitches.
                  </p>
                  <textarea
                    rows={5}
                    value={settings.agent_directives || ''}
                    onChange={(e) => setSettings({ ...settings, agent_directives: e.target.value })}
                    style={{ fontSize: '0.9rem', lineHeight: 1.6 }}
                  />

                  <div style={{ marginTop: 16 }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      🚫 Excluded Companies / Blacklist
                    </label>
                    <input
                      type="text"
                      value={Array.isArray(settings.excluded_companies) ? settings.excluded_companies.join(', ') : settings.excluded_companies || ''}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          excluded_companies: e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                        })
                      }
                    />
                  </div>
                </div>

                {/* 2. Autonomous Scheduler */}
                <div className="glass-panel" style={{ padding: 28 }}>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Clock size={18} color="#10b981" /> Autonomous 30-Minute Job Hunter Engine
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                        Execution Interval (Minutes)
                      </label>
                      <input
                        type="number"
                        min="5"
                        max="1440"
                        value={settings.scheduler?.interval_minutes || 30}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            scheduler: { ...settings.scheduler, interval_minutes: Number(e.target.value) }
                          })
                        }
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                        Minimum Fit for iPhone Alert (%)
                      </label>
                      <input
                        type="number"
                        min="50"
                        max="95"
                        value={settings.scheduler?.auto_notify_threshold || 75}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            scheduler: { ...settings.scheduler, auto_notify_threshold: Number(e.target.value) }
                          })
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* 3. iPhone Push Notifications Setup */}
                <div className="glass-panel" style={{ padding: 28 }}>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Smartphone size={18} color="#06b6d4" /> iPhone Push Notifications (ntfy.sh)
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
                    Download free <strong>ntfy</strong> on iOS App Store &rarr; subscribe to <code>{settings.notifications?.ntfy_topic || 'getmehired_alerts'}</code> &rarr; get instant lock screen dings!
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'flex-end' }}>
                    <div>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                        Notification Topic ({profile?.full_name ? `${profile.full_name}'s Device` : "Push Alerts"})
                      </label>
                      <input
                        type="text"
                        value={settings.notifications?.ntfy_topic || 'getmehired_alerts'}
                        onChange={(e) => {
                          const topicVal = e.target.value;
                          setSettings({
                            ...settings,
                            notifications: { ...settings.notifications, ntfy_topic: topicVal }
                          });
                        }}
                      />
                    </div>
                    <button onClick={testIphoneNotification} className="btn-secondary" style={{ height: 42 }}>
                      <Smartphone size={16} /> Send Test Ping
                    </button>
                  </div>
                  {testNotifStatus && (
                    <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#38bdf8' }}>
                      {testNotifStatus}
                    </div>
                  )}
                </div>

                {/* 4. Target Roles & Locations */}
                <div className="glass-panel" style={{ padding: 28 }}>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Target size={18} color="#6366f1" /> Target Roles & Startup Locations
                  </h3>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Target Job Roles
                    </label>
                    <input
                      type="text"
                      value={settings.target_roles ? settings.target_roles.join(', ') : ''}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          target_roles: e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                        })
                      }
                    />
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                      Target Locations (Gurugram, Pune, Surat, Dehradun, Remote)
                    </label>
                    <input
                      type="text"
                      value={settings.target_locations ? settings.target_locations.join(', ') : ''}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          target_locations: e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                        })
                      }
                    />
                  </div>
                </div>

                <button
                  onClick={saveSettingsChanges}
                  disabled={savingSettings}
                  className="btn-success"
                  style={{ alignSelf: 'flex-start' }}
                >
                  <Check size={16} /> Save Settings & Update Agent
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* JOB DEEP-DIVE & OUTREACH DRAWER */}
      {selectedJob && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            justifyContent: 'flex-end',
            animation: 'fadeIn 0.2s ease'
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectedJob(null);
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 780,
              background: '#0c111d',
              height: '100%',
              overflowY: 'auto',
              borderLeft: '1px solid var(--border-subtle)',
              padding: 32,
              boxShadow: '-10px 0 40px rgba(0,0,0,0.8)',
              display: 'flex',
              flexDirection: 'column',
              gap: 24
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span className="badge badge-source-linkedin">{selectedJob.source}</span>
                  <span className="badge badge-match-high">Fit: {selectedJob.match_score || 90}%</span>
                </div>
                <h2 style={{ fontSize: '1.45rem', fontWeight: 800 }}>{selectedJob.title}</h2>
                <div style={{ fontSize: '1.05rem', color: '#fff', marginTop: 4 }}>
                  {selectedJob.company} • <span style={{ color: 'var(--text-muted)' }}>{selectedJob.location}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="btn-secondary"
                style={{ padding: '6px 12px' }}
              >
                ✕ Close
              </button>
            </div>

            {/* Deep Reasoning */}
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 20, borderRadius: 14, border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck size={18} color="#10b981" /> Strategic Alignment for {profile?.full_name || 'Candidate'}
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.6, marginBottom: 12 }}>
                {selectedJob.match_rationale || `Strong fit for ${selectedJob.company}. Technical skill profile matches their stated requirements.`}
              </p>

              {selectedJob.tailored_bullets && selectedJob.tailored_bullets.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', fontWeight: 700 }}>
                    Tailored Resume Bullets:
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {selectedJob.tailored_bullets.map((bullet, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(0, 0, 0, 0.3)',
                          padding: '10px 14px',
                          borderRadius: 8,
                          fontSize: '0.85rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: 12
                        }}
                      >
                        <span>• {bullet}</span>
                        <button
                          onClick={() => copyToClipboard(bullet, `bullet_${idx}`)}
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
                        >
                          {copiedKey === `bullet_${idx}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Contacts Discovered */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Users size={18} color="#a855f7" /> Target Decision Makers & Founders
                </h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {jobContacts.map((contact) => {
                  const isSelected = selectedContact?.id === contact.id;
                  const isFounder = contact.contact_type.includes('Founder');

                  return (
                    <div
                      key={contact.id}
                      onClick={() => {
                        setSelectedContact(contact);
                        handleGenerateOutreach(contact, outreachTone);
                      }}
                      style={{
                        padding: 16,
                        borderRadius: 12,
                        background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                        border: isSelected ? '1px solid var(--border-active)' : '1px solid var(--border-subtle)',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8, gap: 8 }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                            <span className={`badge ${isFounder ? 'badge-role-hm' : 'badge-role-referrer'}`}>{contact.contact_type}</span>
                            {contact.is_verified_person && (
                              <span style={{ fontSize: '0.72rem', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>
                                ✓ Verified Leader
                              </span>
                            )}
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <strong style={{ fontSize: '1.02rem', color: '#fff' }}>{contact.name || contact.role}</strong>
                            {contact.name && contact.role && (
                              <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>{contact.role}</span>
                            )}
                          </div>
                        </div>
                        <span style={{ fontSize: '0.82rem', color: '#fbbf24', fontWeight: 700, whiteSpace: 'nowrap' }}>
                          ★ {contact.potential_score}/100 Impact
                        </span>
                      </div>

                      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 10 }}>
                        {contact.why_contact}
                      </p>

                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 2 }}>
                        <a
                          href={contact.profile_url || contact.linkedin_search_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="btn-secondary"
                          style={{
                            fontSize: '0.78rem',
                            padding: '5px 12px',
                            background: contact.is_verified_person ? 'rgba(10,102,194,0.35)' : 'rgba(10,102,194,0.18)',
                            borderColor: contact.is_verified_person ? '#0a66c2' : 'rgba(10,102,194,0.4)',
                            color: '#fff',
                            fontWeight: 600
                          }}
                        >
                          {contact.is_verified_person ? 'View LinkedIn Profile' : 'LinkedIn People'} <ExternalLink size={11} />
                        </a>
                        <a
                          href={contact.google_search_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '4px 10px', background: 'rgba(66,133,244,0.15)', borderColor: 'rgba(66,133,244,0.35)' }}
                        >
                          Google X-Ray <ExternalLink size={11} />
                        </a>
                        {contact.twitter_search_url && (
                          <a
                            href={contact.twitter_search_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '4px 10px', background: 'rgba(29,161,242,0.15)', borderColor: 'rgba(29,161,242,0.35)' }}
                          >
                            Twitter/X <ExternalLink size={11} />
                          </a>
                        )}
                        {contact.github_search_url && (
                          <a
                            href={contact.github_search_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '4px 10px', background: 'rgba(110,84,148,0.18)', borderColor: 'rgba(110,84,148,0.4)' }}
                          >
                            GitHub <ExternalLink size={11} />
                          </a>
                        )}
                        {contact.hunter_url && (
                          <a
                            href={contact.hunter_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '4px 10px', background: 'rgba(255,102,0,0.15)', borderColor: 'rgba(255,102,0,0.35)' }}
                          >
                            Email (Hunter) <ExternalLink size={11} />
                          </a>
                        )}
                      </div>

                    </div>
                  );
                })}
              </div>
            </div>

            {/* Auto-Drafted Outreach */}
            <div style={{ background: 'rgba(15, 20, 32, 0.95)', padding: 24, borderRadius: 16, border: '1px solid var(--border-active)', boxShadow: 'var(--shadow-glow)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <MessageSquare size={18} color="#6366f1" /> Tailored Message Generator
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Target: <strong>{selectedContact?.role || 'Founder / CTO'}</strong> at {selectedJob.company}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6 }}>
                  {['founder', 'direct', 'peer'].map((t) => (
                    <button
                      key={t}
                      onClick={() => {
                        setOutreachTone(t);
                        handleGenerateOutreach(selectedContact, t);
                      }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        border: '1px solid var(--border-subtle)',
                        background: outreachTone === t ? 'var(--primary)' : 'transparent',
                        color: outreachTone === t ? '#fff' : 'var(--text-muted)',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        textTransform: 'capitalize'
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tabs */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
                <button
                  className={`tab-btn ${activeMessageType === 'connection_note' ? 'active' : ''}`}
                  onClick={() => setActiveMessageType('connection_note')}
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  LinkedIn Note (&lt;300 chars)
                </button>
                <button
                  className={`tab-btn ${activeMessageType === 'inmail_dm' ? 'active' : ''}`}
                  onClick={() => setActiveMessageType('inmail_dm')}
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  Founder Pitch / InMail
                </button>
                <button
                  className={`tab-btn ${activeMessageType === 'referral_request' ? 'active' : ''}`}
                  onClick={() => setActiveMessageType('referral_request')}
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  Referral Ask
                </button>
                <button
                  className={`tab-btn ${activeMessageType === 'cold_email' ? 'active' : ''}`}
                  onClick={() => setActiveMessageType('cold_email')}
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  Cold Email
                </button>
              </div>

              {generatingOutreach ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Sparkles size={24} style={{ animation: 'pulseGlow 1.5s infinite' }} />
                  <div style={{ marginTop: 10, fontSize: '0.9rem' }}>
                    Drafting high-conversion pitch with local AI...
                  </div>
                </div>
              ) : generatedMessages ? (
                <div>
                  {activeMessageType === 'cold_email' && (
                    <div style={{ marginBottom: 10 }}>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                        Subject Line
                      </label>
                      <input
                        type="text"
                        readOnly
                        value={generatedMessages.cold_email_subject || ''}
                        style={{ fontSize: '0.85rem' }}
                      />
                    </div>
                  )}

                  <div style={{ position: 'relative' }}>
                    <textarea
                      rows={8}
                      readOnly
                      value={
                        activeMessageType === 'connection_note'
                          ? generatedMessages.connection_note
                          : activeMessageType === 'inmail_dm'
                          ? generatedMessages.inmail_dm
                          : activeMessageType === 'referral_request'
                          ? generatedMessages.referral_request
                          : generatedMessages.cold_email_body
                      }
                      style={{ fontSize: '0.88rem', lineHeight: 1.6 }}
                    />
                    <button
                      onClick={() => {
                        const contentToCopy =
                          activeMessageType === 'connection_note'
                            ? generatedMessages.connection_note
                            : activeMessageType === 'inmail_dm'
                            ? generatedMessages.inmail_dm
                            : activeMessageType === 'referral_request'
                            ? generatedMessages.referral_request
                            : `${generatedMessages.cold_email_subject}\n\n${generatedMessages.cold_email_body}`;
                        copyToClipboard(contentToCopy, 'msg_box');
                      }}
                      className="btn-primary"
                      style={{ position: 'absolute', right: 12, bottom: 16, padding: '6px 14px', fontSize: '0.8rem' }}
                    >
                      {copiedKey === 'msg_box' ? <Check size={14} /> : <Copy size={14} />}
                      {copiedKey === 'msg_box' ? 'Copied!' : 'Copy Message'}
                    </button>
                  </div>

                  {activeMessageType === 'connection_note' && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: 6 }}>
                      Character Count: {generatedMessages.connection_note?.length || 0} / 300 (Within LinkedIn invite limit)
                    </div>
                  )}

                  {/* 1-Click Log to CRM Button */}
                  <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Sent this message? Track it in your CRM:
                    </span>
                    <button
                      onClick={() => {
                        const currentMsg =
                          activeMessageType === 'connection_note'
                            ? generatedMessages.connection_note
                            : activeMessageType === 'inmail_dm'
                            ? generatedMessages.inmail_dm
                            : generatedMessages.cold_email_body;
                        logToCrmTracker(selectedContact, currentMsg, generatedMessages.follow_up_note);
                      }}
                      className="btn-success"
                      style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                    >
                      📌 Log Outreach & Set 3-Day Follow-Up Alert
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <button
                    onClick={() => handleGenerateOutreach(selectedContact, outreachTone)}
                    className="btn-primary"
                  >
                    <Sparkles size={16} /> Draft Founder Pitch Now
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
