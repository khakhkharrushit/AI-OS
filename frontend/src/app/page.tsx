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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface Message {
  role: "user" | "agent" | "error";
  content: string;
  plan?: Plan;
  logs?: string[];
  pending_action?: any;
  timestamp: string;
  document_info?: {
    name: string;
    path: string;
    ext: string;
    viewUrl: string;
  };
  login_credentials?: {
    url: string;
    username: string;
    password: string;
  };
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
  battery_percent?: number | null;
  power_plugged?: boolean | null;
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
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [preferences, setPreferences] = useState<Record<string, string>>({});
  const [memoryFacts, setMemoryFacts] = useState<Array<{ id: number; topic: string; content: string; timestamp: string }>>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [emailDrafts, setEmailDrafts] = useState<EmailDraft[]>([]);
  const [agentsList, setAgentsList] = useState<Record<string, Array<{ name: string; description: string; high_risk: boolean }>>>({});
  const [savedContacts, setSavedContacts] = useState<Record<string, string>>({});
  const [docFeedback, setDocFeedback] = useState<Record<string, string>>({});
  const [pendingContactSetup, setPendingContactSetup] = useState<{ name: string; msg: string } | null>(null);
  const [contactPhoneInput, setContactPhoneInput] = useState("");
  const [smtpEmailInput, setSmtpEmailInput] = useState("");
  const [smtpPasswordInput, setSmtpPasswordInput] = useState("");
  const [smtpSavedMsg, setSmtpSavedMsg] = useState("");

  // Load contacts from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = JSON.parse(localStorage.getItem("ai_os_contacts") || "{}");
        setSavedContacts(stored);
      } catch (e) {}
    }
  }, []);

  const saveSmtpCredentials = async () => {
    if (!smtpEmailInput || !smtpPasswordInput) {
      alert("Please enter both your email address and Google App Password.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/email/smtp-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email_address: smtpEmailInput,
          app_password: smtpPasswordInput,
        }),
      });
      if (res.ok) {
        setSmtpSavedMsg("✅ SMTP credentials saved! Direct background email sending is now active.");
        setTimeout(() => setSmtpSavedMsg(""), 4000);
      }
    } catch (e) {
      alert("Failed to save SMTP credentials: " + e);
    }
  };

  const sendDraftViaSmtp = async (draft: EmailDraft) => {
    try {
      const res = await fetch(`${API_BASE}/api/email/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient: draft.recipient,
          subject: draft.subject,
          body: draft.body,
          cc: draft.cc || "",
        }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.result || "Email sent successfully!");
        fetchEmailDrafts();
      } else {
        alert("Failed to send: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("Error sending email: " + e);
    }
  };

  const saveContactNumber = (name: string, phone: string, autoOpenMsg?: string) => {
    const cleanPhone = phone.replace(/[^0-9]/g, "");
    if (cleanPhone.length < 10) {
      alert("Please enter a valid phone number (at least 10 digits with country code).");
      return;
    }
    const updated = { ...savedContacts, [name.toLowerCase().trim()]: cleanPhone };
    setSavedContacts(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("ai_os_contacts", JSON.stringify(updated));
    }
    setPendingContactSetup(null);
    setContactPhoneInput("");
    if (autoOpenMsg) {
      const waUrl = `https://web.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(autoOpenMsg)}`;
      window.open(waUrl, "_blank");
    }
  };

  const handleLaunchDesktop = async (filePath: string) => {
    setDocFeedback((prev) => ({ ...prev, [filePath + "_launch"]: "⏳ Launching..." }));
    try {
      const res = await fetch(`${API_BASE}/api/documents/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath }),
      });
      const data = await res.json();
      setDocFeedback((prev) => ({ ...prev, [filePath + "_launch"]: "✅ Launched" }));
      setTimeout(() => {
        setDocFeedback((prev) => ({ ...prev, [filePath + "_launch"]: "" }));
      }, 3000);
    } catch (e) {
      setDocFeedback((prev) => ({ ...prev, [filePath + "_launch"]: "❌ Failed" }));
      setTimeout(() => {
        setDocFeedback((prev) => ({ ...prev, [filePath + "_launch"]: "" }));
      }, 3000);
    }
  };

  const handleRevealInExplorer = async (filePath: string) => {
    setDocFeedback((prev) => ({ ...prev, [filePath + "_reveal"]: "⏳ Opening..." }));
    try {
      const res = await fetch(`${API_BASE}/api/documents/reveal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath }),
      });
      const data = await res.json();
      setDocFeedback((prev) => ({ ...prev, [filePath + "_reveal"]: "✅ Revealed" }));
      setTimeout(() => {
        setDocFeedback((prev) => ({ ...prev, [filePath + "_reveal"]: "" }));
      }, 3000);
    } catch (e) {
      setDocFeedback((prev) => ({ ...prev, [filePath + "_reveal"]: "❌ Failed" }));
      setTimeout(() => {
        setDocFeedback((prev) => ({ ...prev, [filePath + "_reveal"]: "" }));
      }, 3000);
    }
  };

  const getDocInfoFromMessage = (msg: Message) => {
    if (msg.document_info) return msg.document_info;
    const allLogs = msg.logs || [];
    let foundPath = "";
    for (const log of allLogs) {
      const m = log.match(/\(Path:\s*([^)]+)\)/i);
      if (m && m[1]) {
        foundPath = m[1].trim();
        break;
      }
    }
    if (!foundPath) {
      const m = (msg.content || "").match(/\(Path:\s*([^)]+)\)/i);
      if (m && m[1]) foundPath = m[1].trim();
    }
    if (!foundPath) {
      const m = (msg.content || "").match(/([a-zA-Z]:\\[^\s'")\n\r]+\.(docx|pdf|txt|pptx|xlsx|doc|ppt|xls|md|html))/i);
      if (m && m[1]) foundPath = m[1].trim();
    }
    if (foundPath) {
      const docName = foundPath.split(/[\\/]/).pop() || "Document";
      const docExt = foundPath.substring(foundPath.lastIndexOf(".")).toLowerCase();
      return {
        name: docName,
        path: foundPath,
        ext: docExt,
        viewUrl: `${API_BASE}/api/documents/raw?path=${encodeURIComponent(foundPath)}`,
      };
    }
    return null;
  };

  
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
  const isSpeakingRef = useRef<boolean>(false);
  const desiredListeningRef = useRef<boolean>(false);
  const finalTranscriptRef = useRef<string>("");
  const autoSendOnEndRef = useRef<boolean>(false);

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
        // Use non-continuous mode: each utterance is a single command
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-US";
        recognition.maxAlternatives = 1;

        recognition.onresult = (event: any) => {
          // If AI is speaking, completely ignore any results (echo cancellation)
          if (isSpeakingRef.current) return;
          
          let interimTranscript = "";
          let finalTranscript = "";
          
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) {
              finalTranscript += result[0].transcript;
            } else {
              interimTranscript += result[0].transcript;
            }
          }
          
          // Accumulate final transcript
          if (finalTranscript.trim()) {
            finalTranscriptRef.current += (finalTranscriptRef.current ? " " : "") + finalTranscript.trim();
          }
          
          // Show live preview: accumulated final + current interim
          const displayText = (finalTranscriptRef.current + (interimTranscript ? " " + interimTranscript : "")).trim();
          if (displayText) {
            setInput(displayText);
          }
        };

        recognition.onerror = (e: any) => {
          if (e.error === "no-speech") {
            // Restart on silence if still desired
            if (desiredListeningRef.current && !isSpeakingRef.current) {
              setTimeout(() => {
                if (desiredListeningRef.current && !isSpeakingRef.current) {
                  try { recognition.start(); } catch (err) {}
                }
              }, 200);
            }
            return;
          }
          if (e.error === "aborted") return;
          setIsListening(false);
          desiredListeningRef.current = false;
        };

        recognition.onend = () => {
          if (isSpeakingRef.current) {
            // AI is talking, don't restart
            setIsListening(false);
            return;
          }
          if (desiredListeningRef.current) {
            // Check if we should auto-send
            if (autoSendOnEndRef.current && finalTranscriptRef.current.trim()) {
              const textToSend = finalTranscriptRef.current.trim();
              finalTranscriptRef.current = "";
              autoSendOnEndRef.current = false;
              desiredListeningRef.current = false;
              setIsListening(false);
              // Auto-send the voice command
              setTimeout(() => sendMessage(textToSend), 100);
            } else {
              // Restart recognition for continuous listening
              setTimeout(() => {
                if (desiredListeningRef.current && !isSpeakingRef.current) {
                  try {
                    recognition.start();
                  } catch (e) {
                    setIsListening(false);
                    desiredListeningRef.current = false;
                  }
                }
              }, 100);
            }
          } else {
            setIsListening(false);
          }
        };

        recognitionRef.current = recognition;
      }
    }
  }, []);

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
      return;
    }
    if (desiredListeningRef.current) {
      // Stop listening — if there's accumulated text, auto-send it
      const accumulatedText = finalTranscriptRef.current.trim() || input.trim();
      desiredListeningRef.current = false;
      autoSendOnEndRef.current = false;
      setIsListening(false);
      try {
        recognitionRef.current.stop();
      } catch (err) {}
      // If user stopped listening with text ready, send it
      if (accumulatedText) {
        finalTranscriptRef.current = "";
        setTimeout(() => sendMessage(accumulatedText), 200);
      }
    } else {
      // Cancel any ongoing TTS first
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      isSpeakingRef.current = false;
      setIsSpeaking(false);
      finalTranscriptRef.current = "";
      autoSendOnEndRef.current = false;
      desiredListeningRef.current = true;
      setIsListening(true);
      setInput("");
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error("SpeechRecognition start error:", err);
      }
    }
  };
  const speakText = (text: string) => {
    if (!voiceEnabled || typeof window === "undefined" || !window.speechSynthesis) return;
    
    // Stop microphone BEFORE speaking to avoid echo loop
    desiredListeningRef.current = false;
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }

    window.speechSynthesis.cancel();
    isSpeakingRef.current = true;
    setIsSpeaking(true);

    // Only speak first 200 chars to keep it brief
    const cleanSpeech = text
      .replace(/[*_#`\-]/g, " ")
      .replace(/https?:\/\/\S+/g, "link")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 200);
    const utterance = new SpeechSynthesisUtterance(cleanSpeech);
    utterance.rate = 1.1;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    const onSpeakEnd = () => {
      // Wait 1500ms after TTS ends before allowing mic to restart
      // This prevents echo: mic won't pick up speaker residual sound
      setTimeout(() => {
        isSpeakingRef.current = false;
        setIsSpeaking(false);
      }, 1500);
    };

    utterance.onend = onSpeakEnd;
    utterance.onerror = onSpeakEnd;

    window.speechSynthesis.speak(utterance);
  };
  const fetchSystemStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/system/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {}
  };

  const fetchMemory = async () => {
    try {
      const prefRes = await fetch(`${API_BASE}/api/memory/preferences`);
      if (prefRes.ok) {
        const data = await prefRes.json();
        setPreferences(data.preferences || {});
      }
      const factRes = await fetch(`${API_BASE}/api/memory/facts`);
      if (factRes.ok) {
        const data = await factRes.json();
        setMemoryFacts(data.facts || []);
      }
    } catch (e) {}
  };

  const fetchCalendar = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/calendar/events`);
      if (res.ok) {
        const data = await res.json();
        setCalendarEvents(data.events || []);
      }
    } catch (e) {}
  };

  const fetchEmailDrafts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/email/drafts`);
      if (res.ok) {
        const data = await res.json();
        setEmailDrafts(data.drafts || []);
      }
    } catch (e) {}
  };

  const fetchAgentsManifest = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgentsList(data.agents || {});
      }
    } catch (e) {}
  };

  const sendMessage = async (textToSend?: string) => {
    // Stop recording and cancel speech immediately
    desiredListeningRef.current = false;
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    isSpeakingRef.current = false;
    setIsSpeaking(false);

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

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: userMessage, 
          history: historyPayload 
        }),
      });

      const data = await res.json();

      if (res.ok) {
        // Extract document info if any document was referenced
        let detectedDocInfo: { name: string; path: string; ext: string; viewUrl: string } | undefined = undefined;
        let detectedPath = "";
        const allLogs = data.agent_logs || [];
        for (const log of allLogs) {
          const m = log.match(/\(Path:\s*([^)]+)\)/i);
          if (m && m[1]) {
            detectedPath = m[1].trim();
            break;
          }
        }
        if (!detectedPath) {
          const m = (data.reply || "").match(/\(Path:\s*([^)]+)\)/i);
          if (m && m[1]) detectedPath = m[1].trim();
        }
        if (!detectedPath) {
          const m = (data.reply || "").match(/([a-zA-Z]:\\[^\s'")\n\r]+\.(docx|pdf|txt|pptx|xlsx|doc|ppt|xls|md|html))/i);
          if (m && m[1]) detectedPath = m[1].trim();
        }
        if (detectedPath) {
          const docName = detectedPath.split(/[\\/]/).pop() || "Document";
          const docExt = detectedPath.substring(detectedPath.lastIndexOf(".")).toLowerCase();
          detectedDocInfo = {
            name: docName,
            path: detectedPath,
            ext: docExt,
            viewUrl: `${API_BASE}/api/documents/raw?path=${encodeURIComponent(detectedPath)}`,
          };
        }

        // Extract login credentials if present in steps
        let detectedCreds: { url: string; username: string; password: string } | undefined = undefined;
        if (data.plan?.steps) {
          for (const st of data.plan.steps) {
            if (st.tool === "autofill_login_credentials" && st.arguments) {
              detectedCreds = {
                url: st.arguments.url || "",
                username: st.arguments.username || "",
                password: st.arguments.password || "",
              };
              break;
            }
          }
        }

        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: data.reply,
            plan: data.plan,
            logs: data.agent_logs,
            pending_action: data.pending_action,
            document_info: detectedDocInfo,
            login_credentials: detectedCreds,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
        speakText(data.reply);
        fetchMemory();
        fetchCalendar();
        fetchEmailDrafts();

        // --- OPEN URLS DIRECTLY IN THIS CHROME TAB ---
        // The frontend executes window.open for BrowserAgent actions (opening in the exact active profile)
        if (data.plan?.steps) {
          data.plan.steps.forEach((step: any) => {
            if (step.target_agent === "BrowserAgent") {
              if (step.tool === "play_youtube_video") {
                const query = step.arguments?.query || "";
                const ytUrl = query 
                  ? `https://www.youtube.com/results?search_query=${encodeURIComponent(query.trim())}`
                  : "https://www.youtube.com";
                setTimeout(() => {
                  window.open(ytUrl, "_blank");
                }, 100);
              } else if (step.tool === "autofill_login_credentials") {
                const targetUrl = step.arguments?.url || "";
                if (targetUrl) {
                  setTimeout(() => {
                    window.open(targetUrl, "_blank");
                  }, 150);
                }
              } else if (step.tool === "open_url" && step.arguments?.url) {
                setTimeout(() => {
                  window.open(step.arguments.url, "_blank");
                }, 100);
              } else if (step.tool === "send_whatsapp_message" || step.tool === "open_whatsapp_chat") {
                const msg = step.arguments?.message || "";
                const contact = (step.arguments?.contact || "").trim();
                let cleanPhone = contact.replace(/[^0-9]/g, "");

                // Check stored contacts in localStorage for auto-resolution
                if (cleanPhone.length < 10 && typeof window !== "undefined") {
                  try {
                    const savedContacts = JSON.parse(localStorage.getItem("ai_os_contacts") || "{}");
                    const normalized = contact.toLowerCase();
                    if (savedContacts[normalized]) {
                      cleanPhone = savedContacts[normalized].replace(/[^0-9]/g, "");
                    } else {
                      // Check partial match (e.g. "ashutosh" matching "ashutosh vit")
                      for (const [name, phone] of Object.entries(savedContacts)) {
                        if (normalized.includes(name) || name.includes(normalized)) {
                          cleanPhone = (phone as string).replace(/[^0-9]/g, "");
                          break;
                        }
                      }
                    }
                  } catch (e) {
                    console.error("Failed to load contacts:", e);
                  }
                }

                // Automatically copy message to clipboard
                if (msg && typeof navigator !== "undefined" && navigator.clipboard) {
                  navigator.clipboard.writeText(msg).catch(() => {});
                }

                // If phone is known, open directly into that contact's chat (No contact selection modal needed!)
                // If phone is not yet mapped, open WhatsApp Web with prefilled message
                const waUrl = cleanPhone.length >= 10
                  ? `https://web.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(msg)}`
                  : (msg ? `https://web.whatsapp.com/send?text=${encodeURIComponent(msg)}` : "https://web.whatsapp.com");

                setTimeout(() => {
                  window.open(waUrl, "_blank");
                }, 100);
              }

            }

            if (step.target_agent === "EmailAgent") {
              const recipient = step.arguments?.recipient || "";
              const subject = step.arguments?.subject || "";
              const body = step.arguments?.body || "";
              const cc = step.arguments?.cc || "";
              let gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipient)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
              if (cc) gmailUrl += `&cc=${encodeURIComponent(cc)}`;

              if (step.tool === "create_email_draft" || step.tool === "open_mail_client") {
                setTimeout(() => {
                  window.open(gmailUrl, "_blank");
                }, 150);
              }
              fetchEmailDrafts();
            }

            if (step.target_agent === "DocumentAgent" || step.target_agent === "FileAgent") {
              const toolName = step.tool || "";
              if (["open_document", "open_latest_document", "open_file"].includes(toolName)) {
                let docPath = detectedPath;
                if (!docPath && step.arguments?.query) {
                  const q = step.arguments.query;
                  if (q.includes(":") || q.includes("\\") || q.includes("/")) {
                    docPath = q;
                  }
                }
                if (docPath) {
                  const ext = docPath.substring(docPath.lastIndexOf(".")).toLowerCase();
                  const rawUrl = `${API_BASE}/api/documents/raw?path=${encodeURIComponent(docPath)}`;
                  if ([".pdf", ".txt", ".md", ".json", ".html", ".png", ".jpg", ".jpeg"].includes(ext)) {
                    setTimeout(() => {
                      window.open(rawUrl, "_blank");
                    }, 150);
                  }
                  if ([".docx", ".doc", ".pptx", ".xlsx"].includes(ext)) {
                    handleLaunchDesktop(docPath);
                  }
                }
              }
            }
          });
        }

        // Direct fallback: if user prompt was asking to open and doc was detected
        if (userMessage.toLowerCase().includes("open") && detectedDocInfo) {
          if ([".pdf", ".txt", ".md", ".json", ".html", ".png", ".jpg", ".jpeg"].includes(detectedDocInfo.ext)) {
            setTimeout(() => {
              window.open(detectedDocInfo!.viewUrl, "_blank");
            }, 150);
          }
          if ([".docx", ".doc", ".pptx", ".xlsx"].includes(detectedDocInfo.ext)) {
            handleLaunchDesktop(detectedDocInfo.path);
          }
        }


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
      const res = await fetch(`${API_BASE}/api/chat`, {
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
        fetchEmailDrafts();

        if (action.agent_name === "EmailAgent" || action.target_agent === "EmailAgent") {
          const args = action.arguments || {};
          const recipient = args.recipient || "";
          const subject = args.subject || "";
          const body = args.body || "";
          const cc = args.cc || "";
          let gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipient)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
          if (cc) gmailUrl += `&cc=${encodeURIComponent(cc)}`;
          setTimeout(() => {
            window.open(gmailUrl, "_blank");
          }, 150);
        }
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
      await fetch(`${API_BASE}/api/memory/preferences`, {
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
      await fetch(`${API_BASE}/api/memory/facts`, {
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
      await fetch(`${API_BASE}/api/calendar/events`, {
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
            {stats?.battery_percent !== undefined && stats?.battery_percent !== null && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-neutral-800/80 border border-neutral-700/60 text-xs font-mono">
                <span>{stats.power_plugged ? "⚡" : "🔋"}</span>
                <span className={stats.battery_percent <= 20 ? "text-rose-400 font-bold" : "text-emerald-400 font-medium"}>
                  {stats.battery_percent}%
                </span>
                <span className="text-[10px] text-neutral-400">
                  {stats.power_plugged ? "Charging" : "Battery"}
                </span>
              </div>
            )}
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
                          {msg.pending_action.agent_name === "EmailAgent" && (
                            <button
                              onClick={() => {
                                const args = msg.pending_action.arguments || {};
                                const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(args.recipient || "")}&su=${encodeURIComponent(args.subject || "")}&body=${encodeURIComponent(args.body || "")}`;
                                window.open(gmailUrl, "_blank");
                              }}
                              className="w-full mt-2 py-2 rounded-lg bg-red-600/80 hover:bg-red-500 text-white font-semibold text-xs tracking-wide transition shadow-lg flex items-center justify-center gap-2"
                            >
                              <span>🚀</span> 1-Click Open in Gmail Web Compose
                            </button>
                          )}
                        </div>
                      )}

                      {/* Interactive Web Login Credentials Card */}
                      {msg.login_credentials && (
                        <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-violet-950/50 via-purple-950/50 to-indigo-950/50 border border-purple-500/40 shadow-xl backdrop-blur-md">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2.5">
                              <div className="w-9 h-9 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-lg">
                                🔐
                              </div>
                              <div>
                                <h4 className="text-xs font-bold text-white tracking-tight flex items-center gap-2">
                                  <span>Automated Portal Login</span>
                                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                    AUTOFILL READY
                                  </span>
                                </h4>
                                <a 
                                  href={msg.login_credentials.url} 
                                  target="_blank" 
                                  rel="noreferrer"
                                  className="text-[11px] font-mono text-cyan-400 hover:underline truncate max-w-sm block"
                                >
                                  {msg.login_credentials.url}
                                </a>
                              </div>
                            </div>
                          </div>

                          <div className="space-y-2 text-xs font-mono bg-black/50 p-3 rounded-lg border border-purple-500/20">
                            <div className="flex items-center justify-between">
                              <span className="text-neutral-400">Username:</span>
                              <div className="flex items-center gap-2">
                                <span className="text-white font-bold">{msg.login_credentials.username}</span>
                                <button
                                  onClick={() => {
                                    navigator.clipboard.writeText(msg.login_credentials!.username);
                                    alert("Username copied to clipboard!");
                                  }}
                                  className="px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] text-neutral-300 transition"
                                  title="Copy username"
                                >
                                  📋 Copy
                                </button>
                              </div>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-neutral-400">Password:</span>
                              <div className="flex items-center gap-2">
                                <span className="text-white font-mono">{msg.login_credentials.password}</span>
                                <button
                                  onClick={() => {
                                    navigator.clipboard.writeText(msg.login_credentials!.password);
                                    alert("Password copied to clipboard!");
                                  }}
                                  className="px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] text-neutral-300 transition"
                                  title="Copy password"
                                >
                                  📋 Copy
                                </button>
                              </div>
                            </div>
                          </div>

                          <p className="mt-2.5 text-[11px] text-purple-200/80 leading-relaxed">
                            ⚡ <strong>Status:</strong> The login portal has opened in your browser. Note: VTOP requires an image CAPTCHA — solve the CAPTCHA to complete sign-in.
                          </p>
                        </div>
                      )}

                      {/* Interactive Document Card */}
                      {(() => {
                        const docInfo = getDocInfoFromMessage(msg);
                        if (!docInfo) return null;
                        return (
                          <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-blue-950/40 via-indigo-950/40 to-cyan-950/40 border border-blue-500/40 shadow-xl backdrop-blur-md">
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-3 min-w-0">
                                <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-xl shrink-0">
                                  {docInfo.ext === ".pdf" ? "📕" : [".docx", ".doc"].includes(docInfo.ext) ? "📘" : docInfo.ext === ".pptx" ? "📙" : docInfo.ext === ".xlsx" ? "📗" : "📄"}
                                </div>
                                <div className="min-w-0">
                                  <h4 className="text-sm font-bold text-white tracking-tight flex items-center gap-2 truncate">
                                    <span>{docInfo.name}</span>
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 uppercase shrink-0">
                                      {docInfo.ext.replace(".", "") || "FILE"}
                                    </span>
                                  </h4>
                                  <p className="text-[11px] font-mono text-neutral-400 truncate max-w-md" title={docInfo.path}>
                                    {docInfo.path}
                                  </p>
                                </div>
                              </div>
                            </div>

                            {/* Document Action Buttons */}
                            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-blue-500/20">
                              <button
                                onClick={() => window.open(docInfo.viewUrl, "_blank")}
                                className="py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition flex items-center justify-center gap-1.5 shadow-md hover:shadow-blue-500/25 cursor-pointer"
                                title="Open directly in a new browser tab"
                              >
                                <span>🚀</span> Open in Browser
                              </button>
                              <button
                                onClick={() => handleLaunchDesktop(docInfo.path)}
                                className="py-2 px-3 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 hover:text-white font-semibold text-xs border border-neutral-700 transition flex items-center justify-center gap-1.5 cursor-pointer"
                                title="Launch with native desktop application"
                              >
                                <span>💻</span> {docFeedback[docInfo.path + "_launch"] || "Launch Desktop"}
                              </button>
                              <button
                                onClick={() => handleRevealInExplorer(docInfo.path)}
                                className="py-2 px-3 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 hover:text-white font-semibold text-xs border border-neutral-700 transition flex items-center justify-center gap-1.5 cursor-pointer"
                                title="Show file in Windows File Explorer"
                              >
                                <span>📂</span> {docFeedback[docInfo.path + "_reveal"] || "File Explorer"}
                              </button>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                ))
              )}

              {pendingContactSetup && (
                <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-500/50 shadow-lg text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold text-emerald-400">
                      <span>💬</span>
                      <span>WhatsApp Direct-Chat Setup: {pendingContactSetup.name}</span>
                    </div>
                    <button 
                      onClick={() => setPendingContactSetup(null)}
                      className="text-neutral-400 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
                  <p className="text-neutral-300">
                    To open {pendingContactSetup.name}&apos;s chat directly with zero clicks every time, enter their phone number once:
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="e.g. +919876543210 or 9876543210"
                      value={contactPhoneInput}
                      onChange={(e) => setContactPhoneInput(e.target.value)}
                      className="flex-1 px-3 py-2 rounded-lg bg-black/60 border border-emerald-500/40 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                    />
                    <button
                      onClick={() => saveContactNumber(pendingContactSetup.name, contactPhoneInput, pendingContactSetup.msg)}
                      className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-bold tracking-wide transition shadow"
                    >
                      Save & Direct Open
                    </button>
                  </div>
                </div>
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
                  className={`px-3.5 py-3 rounded-xl border transition flex items-center gap-2 font-mono text-xs shrink-0 ${
                    isListening
                      ? "bg-rose-600 text-white border-rose-400 animate-pulse shadow-lg shadow-rose-500/40 font-bold"
                      : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border-neutral-700"
                  }`}
                  title={isListening ? "Click to stop recording and keep text" : "Click to speak your instruction"}
                >
                  <span>{isListening ? "🔴 Listening..." : "🎙️ Voice"}</span>
                </button>

                {/* Text Input */}
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder={
                      isListening
                        ? "Speak your command (e.g. 'open notepad and create file rk and write my name is rk')..."
                        : "Enter natural language command..."
                    }
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
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white mb-1">📧 Email Hub & Live Dispatcher</h2>
                <p className="text-xs text-neutral-400">Send directly via Gmail Web Compose, desktop mailto, or automated background SMTP.</p>
              </div>
            </div>

            {/* SMTP Setup Card */}
            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm flex items-center gap-2">
                  <span>⚡</span> Background SMTP Delivery Configuration (Optional)
                </span>
                <span className="text-[11px] text-neutral-400">For 100% autonomous sending without browser clicks</span>
              </div>
              <p className="text-xs text-neutral-300">
                Enter your Gmail or Outlook credentials (use a 16-character <span className="text-cyan-300 font-mono">Google App Password</span> for security).
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input
                  type="email"
                  placeholder="Your Email (e.g. user@gmail.com)"
                  value={smtpEmailInput}
                  onChange={(e) => setSmtpEmailInput(e.target.value)}
                  className="bg-black/50 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
                <input
                  type="password"
                  placeholder="16-character App Password"
                  value={smtpPasswordInput}
                  onChange={(e) => setSmtpPasswordInput(e.target.value)}
                  className="bg-black/50 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              <div className="flex items-center justify-between pt-1">
                <button
                  onClick={saveSmtpCredentials}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs transition shadow-md flex items-center gap-2"
                >
                  <span>💾</span> Save SMTP Credentials
                </button>
                {smtpSavedMsg && <span className="text-xs text-emerald-400 font-medium">{smtpSavedMsg}</span>}
              </div>
            </div>

            {/* Stored Emails & Drafts */}
            <div className="bg-[#121620] border border-neutral-800 rounded-2xl p-6 shadow-xl space-y-3">
              <h3 className="font-bold text-white text-sm border-b border-neutral-800 pb-2">
                Stored Email Dispatches & Drafts ({emailDrafts.length})
              </h3>
              {emailDrafts.length === 0 ? (
                <p className="text-xs text-neutral-400 text-center py-6">No email drafts stored in memory.</p>
              ) : (
                emailDrafts.map((d) => {
                  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(d.recipient)}&su=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
                  const mailtoUrl = `mailto:${encodeURIComponent(d.recipient)}?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
                  return (
                    <div key={d.id} className="p-4 rounded-xl bg-black/40 border border-neutral-800 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{d.subject}</span>
                        <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono text-[10px] uppercase font-bold">
                          {d.status}
                        </span>
                      </div>
                      <div className="text-neutral-400 text-[11px]">To: <span className="text-cyan-300 font-mono">{d.recipient}</span></div>
                      <div className="text-neutral-300 bg-black/30 p-2.5 rounded-lg whitespace-pre-wrap font-sans text-xs">
                        {d.body}
                      </div>
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => window.open(gmailUrl, "_blank")}
                          className="px-3 py-1.5 rounded-lg bg-red-600/80 hover:bg-red-500 text-white font-semibold text-[11px] transition flex items-center gap-1.5"
                        >
                          <span>🚀</span> Open in Gmail Web
                        </button>
                        <button
                          onClick={() => window.open(mailtoUrl, "_blank")}
                          className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-semibold text-[11px] transition flex items-center gap-1.5"
                        >
                          <span>✉️</span> Windows Mail
                        </button>
                        <button
                          onClick={() => sendDraftViaSmtp(d)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white font-semibold text-[11px] transition flex items-center gap-1.5"
                        >
                          <span>⚡</span> Send via SMTP
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}\n\n        {activeTab === "agents" && (
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
