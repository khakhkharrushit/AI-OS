"use client";

import React, { useState, useEffect, useRef } from "react";

interface Step {
  step_number: number;
  description: string;
  target_agent: string;
  tool: string;
  arguments: Record<string, any>;
}

interface Plan {
  response: string;
  steps: Step[];
}

interface Message {
  role: "user" | "agent" | "error";
  content: string;
  plan?: Plan;
  logs?: string[];
  pending_action?: any;
  timestamp: string;
}

interface SystemStats {
  os: string;
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  process_count: number;
}

interface CalendarEvent {
  id: number;
  title: string;
  event_date: string;
  event_time: string;
  duration_minutes: number;
  description: string;
  location: string;
}

interface EmailDraft {
  id: number;
  recipient: string;
  subject: string;
  body: string;
  cc: string;
  status: string;
  created_at: string;
}

export default function AIOSDashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "memory" | "calendar" | "emails" | "agents">("chat");
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [preferences, setPreferences] = useState<Record<string, string>>({});
  const [memoryFacts, setMemoryFacts] = useState<Array<{ id: number; topic: string; content: string; timestamp: string }>>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [emailDrafts, setEmailDrafts] = useState<EmailDraft[]>([]);
  const [agentsList, setAgentsList] = useState<Record<string, Array<{ name: string; description: string; high_risk: boolean }>>>({});
  
  // Modals / forms
  const [newPrefKey, setNewPrefKey] = useState("");
  const [newPrefVal, setNewPrefVal] = useState("");
  const [newFactTopic, setNewFactTopic] = useState("");
  const [newFactContent, setNewFactContent] = useState("");
  const [newEventTitle, setNewEventTitle] = useState("");
  const [newEventDate, setNewEventDate] = useState("");
  const [newEventTime, setNewEventTime] = useState("10:00 AM");

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Fetch initial system state & memory
  useEffect(() => {
    fetchSystemStats();
    fetchMemory();
    fetchCalendar();
    fetchEmailDrafts();
    fetchAgentsManifest();

    const interval = setInterval(() => {
      fetchSystemStats();
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  // Web Speech Recognition setup
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInput(transcript);
          setIsListening(false);
          sendMessage(transcript);
        };

        recognition.onerror = () => setIsListening(false);
        recognition.onend = () => setIsListening(false);

        recognitionRef.current = recognition;
      }
    }
  }, []);

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please use Chrome/Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error(err);
      }
    }
  };

  const speakText = (text: string) => {
    if (!voiceEnabled || typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    // Clean markdown symbols for natural vocal speech
    const cleanSpeech = text.replace(/[*_#`\-]/g, " ").replace(/https?:\/\/\S+/g, "link").slice(0, 250);
    const utterance = new SpeechSynthesisUtterance(cleanSpeech);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  const fetchSystemStats = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/system/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      // Backend not running yet or unreachable
    }
  };

  const fetchMemory = async () => {
    try {
      const prefRes = await fetch("http://127.0.0.1:8000/api/memory/preferences");
      if (prefRes.ok) {
        const data = await prefRes.json();
        setPreferences(data.preferences || {});
      }
      const factRes = await fetch("http://127.0.0.1:8000/api/memory/facts");
      if (factRes.ok) {
        const data = await factRes.json();
        setMemoryFacts(data.facts || []);
      }
    } catch (e) {}
  };

  const fetchCalendar = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/calendar/events");
      if (res.ok) {
        const data = await res.json();
        setCalendarEvents(data.events || []);
      }
    } catch (e) {}
  };

  const fetchEmailDrafts = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/email/drafts");
      if (res.ok) {
        const data = await res.json();
        setEmailDrafts(data.drafts || []);
      }
    } catch (e) {}
  };

  const fetchAgentsManifest = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/agents");
      if (res.ok) {
        const data = await res.json();
        setAgentsList(data.agents || {});
      }
    } catch (e) {}
  };

  const sendMessage = async (textToSend?: string) => {
    const userMessage = (textToSend || input).trim();
    if (!userMessage) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newHistory = [...messages, { role: "user" as const, content: userMessage, timestamp: timeStr }];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    try {
      const historyPayload = newHistory.slice(-8).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: userMessage, 
          history: historyPayload 
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: data.reply,
            plan: data.plan,
            logs: data.agent_logs,
            pending_action: data.pending_action,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
        speakText(data.reply);
        fetchMemory();
        fetchCalendar();
        fetchEmailDrafts();
      } else {
        setMessages((prev) => [
          ...prev,
          { 
            role: "error", 
            content: data.detail?.error || "Error occurred during execution",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev, 
        { 
          role: "error", 
          content: "Failed to connect to AI OS Backend at http://127.0.0.1:8000. Please ensure the backend server is running.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (action: any, index: number) => {
    setMessages((prev) =>
      prev.map((msg, i) => (i === index ? { ...msg, pending_action: null } : msg))
    );

    setMessages((prev) => [
      ...prev,
      { 
        role: "user", 
        content: `⚡ Human Verification Approved: Execute ${action.tool_name}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      },
    ]);
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "",
          pending_action_approved: action,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: data.reply,
            logs: data.agent_logs,
            pending_action: data.pending_action,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          },
        ]);
        speakText(data.reply);
        fetchMemory();
      } else {
        setMessages((prev) => [
          ...prev,
          { 
            role: "error", 
            content: data.detail?.error || "Error occurred during resumption",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: "error", content: String(err), timestamp: "" }]);
    } finally {
      setLoading(false);
    }
  };

  const saveNewPreference = async () => {
    if (!newPrefKey || !newPrefVal) return;
    try {
      await fetch("http://127.0.0.1:8000/api/memory/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: newPrefKey, value: newPrefVal })
      });
      setNewPrefKey("");
      setNewPrefVal("");
      fetchMemory();
    } catch (e) {}
  };

  const saveNewFact = async () => {
    if (!newFactTopic || !newFactContent) return;
    try {
      await fetch("http://127.0.0.1:8000/api/memory/facts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: newFactTopic, content: newFactContent })
      });
      setNewFactTopic("");
      setNewFactContent("");
      fetchMemory();
    } catch (e) {}
  };

  const saveNewCalendarEvent = async () => {
    if (!newEventTitle || !newEventDate) return;
    try {
      await fetch("http://127.0.0.1:8000/api/calendar/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newEventTitle, event_date: newEventDate, event_time: newEventTime })
      });
      setNewEventTitle("");
      setNewEventDate("");
      fetchCalendar();
    } catch (e) {}
  };

  const quickWorkflows = [
    { label: "🚀 Prepare Interview Workspace", prompt: "Prepare my interview workspace: check system info, search for my resume, and open Chrome" },
    { label: "🩺 Full System Health Diagnostic", prompt: "Run a full system diagnostic: get CPU, RAM, Disk usage and list top 10 running processes" },
    { label: "🌐 AI & Tech News Brief", prompt: "Search the web for the latest artificial intelligence news and summarize key breakthroughs" },
    { label: "📅 Schedule Team Sync", prompt: "Create a calendar event for Project 1 Review tomorrow at 3:00 PM" },
    { label: "📸 Desktop Screen Diagnostics", prompt: "Capture desktop screenshot and analyze active windows and diagnostics" },
    { label: "✉️ Draft Project Status Email", prompt: "Create an email draft to team@aios.org with subject 'Phase 7 Completed' and brief summary" },
  ];

  const agentBadges = [
    { name: "FileAgent", color: "from-blue-500/20 to-cyan-500/20 border-cyan-500/30 text-cyan-300", icon: "📁" },
    { name: "SystemAgent", color: "from-purple-500/20 to-pink-500/20 border-purple-500/30 text-purple-300", icon: "⚙️" },
    { name: "MemoryAgent", color: "from-amber-500/20 to-yellow-500/20 border-amber-500/30 text-amber-300", icon: "🧠" },
    { name: "BrowserAgent", color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-300", icon: "🌐" },
    { name: "DocumentAgent", color: "from-indigo-500/20 to-blue-500/20 border-indigo-500/30 text-indigo-300", icon: "📄" },
    { name: "EmailAgent", color: "from-rose-500/20 to-orange-500/20 border-rose-500/30 text-rose-300", icon: "✉️" },
    { name: "CalendarAgent", color: "from-orange-500/20 to-amber-500/20 border-orange-500/30 text-orange-300", icon: "📅" },
    { name: "VisionAgent", color: "from-fuchsia-500/20 to-violet-500/20 border-fuchsia-500/30 text-fuchsia-300", icon: "👁️" }
  ];

  return (
    <div className="flex h-screen w-screen bg-[#090b10] text-neutral-100 font-sans overflow-hidden">
      
      {/* LEFT SIDEBAR NAVIGATION */}
      <aside className="w-72 bg-[#0e121a]/95 border-r border-neutral-800/80 flex flex-col justify-between shrink-0 shadow-2xl backdrop-blur-xl">
        <div>
          {/* Brand Header */}
          <div className="p-5 border-b border-neutral-800/80 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 shadow-lg shadow-blue-500/25">
                <span className="text-lg font-black tracking-tighter text-white">AI</span>
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-[#0e121a] animate-pulse"></span>
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight bg-gradient-to-r from-white via-neutral-200 to-neutral-400 bg-clip-text text-transparent">
                  AI Operating System
                </h1>
                <p className="text-[11px] font-mono text-neutral-400">Windows Multi-Agent Core</p>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="p-3 space-y-1">
            {[
              { id: "chat", label: "Agent Command Center", icon: "💬" },
              { id: "memory", label: "Memory & Preferences", icon: "🧠" },
              { id: "calendar", label: "Calendar & Schedule", icon: "📅" },
              { id: "emails", label: "Email & Drafts", icon: "✉️" },
              { id: "agents", label: "Agent Tool Catalog", icon: "⚡" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-gradient-to-r from-blue-600/30 to-indigo-600/20 text-blue-300 border border-blue-500/40 shadow-sm"
                    : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50"
                }`}
              >
                <span className="text-base">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Quick Workflows Section */}
          <div className="p-3">
            <p className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider px-3 mb-2 font-mono">
              Automated Workflows
            </p>
            <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              {quickWorkflows.map((wf, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setActiveTab("chat");
                    sendMessage(wf.prompt);
                  }}
                  className="w-full text-left p-2 rounded-lg bg-neutral-900/80 hover:bg-neutral-800 border border-neutral-800 hover:border-neutral-700 transition text-[11px] text-neutral-300 hover:text-white truncate block"
                >
                  {wf.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* System Resource Telemetry Bar */}
        <div className="p-4 border-t border-neutral-800/80 bg-black/20 text-xs font-mono space-y-2">
          <div className="flex items-center justify-between text-[11px] text-neutral-400">
            <span>System Telemetry</span>
            <span className="text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live
            </span>
          </div>

          {stats ? (
            <div className="space-y-1.5 text-[11px]">
              <div>
                <div className="flex justify-between text-neutral-400 text-[10px]">
                  <span>CPU Usage</span>
                  <span>{stats.cpu_percent}%</span>
                </div>
                <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden mt-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(stats.cpu_percent, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-neutral-400 text-[10px]">
                  <span>RAM Usage</span>
                  <span>{stats.ram_percent}% ({stats.ram_used_gb} GB)</span>
                </div>
                <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden mt-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(stats.ram_percent, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="flex justify-between text-[10px] text-neutral-400 pt-1">
                <span>Disk C: {stats.disk_percent}%</span>
                <span>Procs: {stats.process_count}</span>
              </div>
            </div>
          ) : (
            <p className="text-[11px] text-neutral-400">Connecting to telemetry...</p>
          )}
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        
        {/* Top Header Bar */}
        <header className="h-14 border-b border-neutral-800/80 bg-[#0e121a]/80 backdrop-blur px-6 flex items-center justify-between shrink-0">
          {/* Agent Badges Bar */}
          <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
            {agentBadges.map((ag) => (
              <span
                key={ag.name}
                className={`px-2 py-0.5 rounded-md text-[10px] font-mono border bg-gradient-to-r ${ag.color} flex items-center gap-1 shrink-0`}
              >
                <span>{ag.icon}</span>
                {ag.name}
              </span>
            ))}
          </div>

          {/* Voice Controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              className={`p-1.5 rounded-lg border text-xs font-mono transition flex items-center gap-1.5 ${
                voiceEnabled
                  ? "bg-blue-500/20 border-blue-500/40 text-blue-300"
                  : "bg-neutral-800 border-neutral-700 text-neutral-400"
              }`}
              title="Toggle Text-To-Speech audio response"
            >
              <span>{voiceEnabled ? "🔊 Voice TTS On" : "🔇 Voice TTS Off"}</span>
            </button>
            <span className="w-px h-5 bg-neutral-800"></span>
            <div className="flex items-center gap-1 text-[11px] font-mono text-neutral-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              FastAPI: 8000
            </div>
          </div>
        </header>

        {/* TAB 1: COMMAND CENTER / CHAT */}
        {activeTab === "chat" && (
          <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden">
            {/* Messages Scroll Container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-16 max-w-2xl mx-auto">
                  <div className="relative mb-6">
                    <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-2xl shadow-blue-500/30">
                      <span className="text-4xl">⚡</span>
                    </div>
                  </div>
                  <h2 className="text-2xl font-bold tracking-tight text-white mb-2">
                    What can I execute for you today?
                  </h2>
                  <p className="text-sm text-neutral-400 mb-8 leading-relaxed">
                    AI OS orchestrates 8 specialized agents to inspect files, execute multi-step plans, analyze documents, automate browsers, and control your Windows desktop.
                  </p>
                  
                  <div className="grid grid-cols-2 gap-2.5 w-full">
                    {quickWorkflows.slice(0, 4).map((wf, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(wf.prompt)}
                        className="p-3.5 rounded-xl bg-neutral-900/90 hover:bg-neutral-800/90 border border-neutral-800/80 hover:border-neutral-700 text-left transition text-xs text-neutral-300 hover:text-white flex flex-col gap-1 shadow-sm"
                      >
                        <span className="font-semibold text-white">{wf.label}</span>
                        <span className="text-[11px] text-neutral-400 truncate">{wf.prompt}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
                  >
                    <div className="flex items-center gap-2 mb-1.5 px-1">
                      <span className="text-[10px] font-mono text-neutral-400">
                        {msg.role === "user" ? "User" : msg.role === "error" ? "System Error" : "AI OS Orchestrator"}
                      </span>
                      <span className="text-[10px] font-mono text-neutral-400">{msg.timestamp}</span>
                    </div>

                    <div
                      className={`max-w-[85%] rounded-2xl p-4.5 shadow-lg ${
                        msg.role === "user"
                          ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-xs"
                          : msg.role === "error"
                          ? "bg-rose-950/70 border border-rose-800/80 text-rose-200 rounded-bl-xs"
                          : "bg-[#121620] border border-neutral-800 rounded-bl-xs"
                      }`}
                    >
                      {/* Message Content */}
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>

                      {/* Structured Plan Visualizer Stepper */}
                      {msg.plan && msg.plan.steps && msg.plan.steps.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-neutral-800/80">
                          <p className="text-[11px] font-mono font-bold text-neutral-400 uppercase tracking-wider mb-2.5">
                            ⚡ Multi-Agent Execution Plan ({msg.plan.steps.length} Steps)
                          </p>
                          <div className="space-y-2">
                            {msg.plan.steps.map((st, sIdx) => (
                              <div
                                key={sIdx}
                                className="flex items-start gap-3 p-2.5 rounded-lg bg-black/40 border border-neutral-800/60 text-xs"
                              >
                                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 font-mono text-[10px] shrink-0">
                                  {st.step_number || sIdx + 1}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="font-medium text-neutral-200">{st.description}</span>
                                    <span className="px-2 py-0.5 rounded bg-neutral-800 text-[10px] font-mono text-cyan-300">
                                      {st.target_agent} : {st.tool}
                                    </span>
                                  </div>
                                  {st.arguments && Object.keys(st.arguments).length > 0 && (
                                    <div className="mt-1 font-mono text-[10px] text-neutral-400 truncate">
                                      {JSON.stringify(st.arguments)}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Detailed Agent Logs */}
                      {msg.logs && msg.logs.length > 0 && (
                        <details className="mt-3 group">
                          <summary className="cursor-pointer text-xs font-mono font-semibold text-neutral-400 hover:text-neutral-300 select-none flex items-center gap-1.5">
                            <span className="transition-transform group-open:rotate-90 text-[10px]">▶</span>
                            Agent Execution Logs ({msg.logs.length} events)
                          </summary>
                          <div className="mt-2 p-3 bg-black/60 border border-neutral-800 rounded-xl font-mono text-xs text-neutral-300 space-y-1 overflow-x-auto max-h-60">
                            {msg.logs.map((log, lIdx) => (
                              <div
                                key={lIdx}
                                className={`${
                                  log.includes("SECURITY ALERT")
                                    ? "text-amber-400 font-bold"
                                    : log.includes("Error")
                                    ? "text-rose-400"
                                    : log.includes("Success") || log.includes("Approved")
                                    ? "text-emerald-400"
                                    : log.includes("Routing")
                                    ? "text-blue-400"
                                    : "text-neutral-300"
                                }`}
                              >
                                {log}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}

                      {/* Safety Interception & Human Approval Card */}
                      {msg.pending_action && (
                        <div className="mt-4 p-4 rounded-xl bg-amber-950/40 border border-amber-500/60 shadow-xl">
                          <div className="flex items-center gap-2 text-sm font-bold text-amber-400 mb-2">
                            <span>🛡️</span> Security Validation Interception
                          </div>
                          <p className="text-xs text-neutral-200 mb-2 leading-relaxed">
                            A high-risk operating system operation requires your explicit authorization before execution:
                          </p>
                          <div className="p-2.5 rounded-lg bg-black/60 border border-amber-500/30 text-xs font-mono mb-3 space-y-1">
                            <div><span className="text-neutral-400">Agent:</span> <span className="text-amber-300 font-bold">{msg.pending_action.agent_name}</span></div>
                            <div><span className="text-neutral-400">Tool:</span> <span className="text-amber-300 font-bold">{msg.pending_action.tool_name}</span></div>
                            <div><span className="text-neutral-400">Arguments:</span> <span className="text-neutral-200">{JSON.stringify(msg.pending_action.arguments)}</span></div>
                          </div>
                          <button
                            onClick={() => handleApprove(msg.pending_action, idx)}
                            className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-neutral-950 font-bold text-xs tracking-wide transition shadow-lg flex items-center justify-center gap-2"
                          >
                            <span>✓</span> Approve & Resume Multi-Step Plan
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {loading && (
                <div className="flex items-center gap-3 p-4 rounded-2xl bg-[#121620] border border-neutral-800 w-fit">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                  </span>
                  <span className="text-xs font-mono text-neutral-300">
                    AI OS Reasoning, Planning & Dispatching Agents...
                  </span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Bottom Command Input Bar */}
            <div className="p-4 bg-[#0e121a]/95 border-t border-neutral-800/80 backdrop-blur">
              <div className="max-w-4xl mx-auto flex items-center gap-2">
                {/* Voice Microphone Button */}
                <button
                  onClick={toggleVoiceInput}
                  className={`p-3 rounded-xl border transition flex items-center justify-center shrink-0 ${
                    isListening
                      ? "bg-rose-500 text-white border-rose-400 animate-pulse shadow-lg shadow-rose-500/40"
                      : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border-neutral-700"
                  }`}
                  title="Speak instruction using microphone"
                >
                  <span className="text-base">{isListening ? "🎙️ Recording..." : "🎙️"}</span>
                </button>

                {/* Text Input */}
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Enter natural language command (e.g. 'Search web for AI news', 'Summarize resume.pdf', 'Check CPU')..."
                    className="w-full bg-[#151a24] border border-neutral-700/80 rounded-xl px-4 py-3 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition"
                  />
                </div>

                {/* Send Button */}
                <button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 font-semibold text-xs tracking-wide transition text-white shadow-lg shadow-blue-500/20 shrink-0"
                >
                  Execute
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MEMORY & PREFERENCES */}
        {activeTab === "memory" && (
          <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full space-y-8">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">🧠 Long-Term Memory & User Preferences</h2>
              <p className="text-xs text-neutral-400">Context injected into the Planner prompt so the AI remembers your habits and instructions across sessions.</p>
            </div>

            {/* Preferences Table */}
            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-neutral-200 uppercase tracking-wider font-mono mb-4">
                User Defaults & Settings
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                {Object.entries(preferences).map(([k, v]) => (
                  <div key={k} className="p-3 rounded-xl bg-black/40 border border-neutral-800 flex justify-between items-center text-xs">
                    <span className="font-mono text-cyan-300 font-semibold">{k}</span>
                    <span className="font-mono text-neutral-300 bg-neutral-800 px-2 py-1 rounded">{v}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 pt-2 border-t border-neutral-800">
                <input
                  type="text"
                  placeholder="Key (e.g. default_browser)"
                  value={newPrefKey}
                  onChange={(e) => setNewPrefKey(e.target.value)}
                  className="flex-1 bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                />
                <input
                  type="text"
                  placeholder="Value (e.g. brave)"
                  value={newPrefVal}
                  onChange={(e) => setNewPrefVal(e.target.value)}
                  className="flex-1 bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                />
                <button
                  onClick={saveNewPreference}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white"
                >
                  Save Preference
                </button>
              </div>
            </div>

            {/* Stored Knowledge Facts */}
            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-neutral-200 uppercase tracking-wider font-mono mb-4">
                Learned Notes & Workflow Facts
              </h3>
              <div className="space-y-2 mb-4">
                {memoryFacts.map((f) => (
                  <div key={f.id} className="p-3 rounded-xl bg-black/40 border border-neutral-800 text-xs">
                    <div className="flex justify-between text-neutral-400 font-mono text-[10px] mb-1">
                      <span className="text-amber-400 font-semibold">[{f.topic}]</span>
                      <span>{f.timestamp}</span>
                    </div>
                    <div className="text-neutral-200">{f.content}</div>
                  </div>
                ))}
              </div>
              <div className="flex flex-col gap-2 pt-2 border-t border-neutral-800">
                <input
                  type="text"
                  placeholder="Topic (e.g. resume_location)"
                  value={newFactTopic}
                  onChange={(e) => setNewFactTopic(e.target.value)}
                  className="w-full bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Fact or note content to remember..."
                    value={newFactContent}
                    onChange={(e) => setNewFactContent(e.target.value)}
                    className="flex-1 bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                  />
                  <button
                    onClick={saveNewFact}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-xs font-semibold text-white shrink-0"
                  >
                    Save Note
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: CALENDAR & SCHEDULE */}
        {activeTab === "calendar" && (
          <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">📅 Calendar & Task Scheduler</h2>
              <p className="text-xs text-neutral-400">Events scheduled by CalendarAgent or manual booking.</p>
            </div>

            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-6 shadow-xl space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder="Event Title (e.g. Project Demo)"
                  value={newEventTitle}
                  onChange={(e) => setNewEventTitle(e.target.value)}
                  className="bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                />
                <input
                  type="date"
                  value={newEventDate}
                  onChange={(e) => setNewEventDate(e.target.value)}
                  className="bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="10:00 AM"
                    value={newEventTime}
                    onChange={(e) => setNewEventTime(e.target.value)}
                    className="flex-1 bg-black/40 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-white"
                  />
                  <button
                    onClick={saveNewCalendarEvent}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white"
                  >
                    Add
                  </button>
                </div>
              </div>

              <div className="space-y-2 pt-4">
                {calendarEvents.length === 0 ? (
                  <p className="text-xs text-neutral-400 text-center py-6">No scheduled calendar events found.</p>
                ) : (
                  calendarEvents.map((ev) => (
                    <div key={ev.id} className="p-3.5 rounded-xl bg-black/40 border border-neutral-800 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-bold text-white">{ev.title}</div>
                        <div className="text-[11px] text-neutral-400 font-mono">
                          {ev.event_date} at {ev.event_time} ({ev.duration_minutes} mins)
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-mono text-[10px]">
                        Event #{ev.id}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: EMAIL DRAFTS */}
        {activeTab === "emails" && (
          <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">✉️ Email Drafts & Dispatcher</h2>
              <p className="text-xs text-neutral-400">Created by EmailAgent with safety approval safeguards.</p>
            </div>

            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-6 shadow-xl space-y-3">
              {emailDrafts.length === 0 ? (
                <p className="text-xs text-neutral-400 text-center py-6">No email drafts stored in memory.</p>
              ) : (
                emailDrafts.map((d) => (
                  <div key={d.id} className="p-4 rounded-xl bg-black/40 border border-neutral-800 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm">{d.subject}</span>
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px] uppercase">
                        {d.status}
                      </span>
                    </div>
                    <div className="text-neutral-400 text-[11px]">To: <span className="text-cyan-300 font-mono">{d.recipient}</span></div>
                    <div className="text-neutral-300 bg-black/30 p-2.5 rounded-lg whitespace-pre-wrap font-sans text-xs">
                      {d.body}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 5: AGENT CAPABILITY CATALOG */}
        {activeTab === "agents" && (
          <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">⚡ Registered Agent Tool Catalog</h2>
              <p className="text-xs text-neutral-400">All 8 active specialized agents and their executable tools.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(agentsList).map(([agName, tools]) => (
                <div key={agName} className="bg-[#121620] border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-3">
                  <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                    <span className="font-bold text-white text-sm">{agName}</span>
                    <span className="text-xs font-mono text-neutral-400">{tools.length} Tools</span>
                  </div>
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {tools.map((t) => (
                      <div key={t.name} className="p-2.5 rounded-lg bg-black/40 border border-neutral-800/80 text-xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-cyan-300 font-semibold">{t.name}</span>
                          {t.high_risk && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-mono font-bold">
                              HIGH RISK
                            </span>
                          )}
                        </div>
                        <p className="text-neutral-400 text-[11px]">{t.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
