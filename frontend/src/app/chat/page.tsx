"use client";

import Link from 'next/link';

import { Send, Bot, MapPin, Cpu, Zap, Square, Sun, Moon, Menu, X, ChevronLeft, Plus } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';
import { useSession, signIn, signOut } from "next-auth/react";

const BudgetChart = dynamic(() => import('@/components/BudgetChart'), { ssr: false });

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  budgetData?: any; // Budget chart data nếu có
  statusText?: string; // Text hiệu ứng động (Streaming status)
}

interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
}

const SUGGESTIONS = [
  { icon: '🗺️', label: 'Lộ trình An Giang 3N2Đ', text: 'Hãy gợi ý cho tôi lộ trình du lịch An Giang 3 ngày 2 đêm' },
  { icon: '🍜', label: 'Đặc sản Phú Quốc', text: 'Món ăn đặc sản ở Phú Quốc là gì?' },
  { icon: '🌸', label: 'Mùa đẹp Cần Thơ', text: 'Thời điểm tốt nhất để du lịch Cần Thơ?' },
  { icon: '🏔️', label: 'Khám phá Cà Mau', text: 'Các điểm tham quan nổi tiếng ở Cà Mau?' },
];

export default function Chat() {
  const { data: session, status } = useSession();
  const isSignedIn = status === "authenticated";
  const user = session?.user;
  const [mounted, setMounted] = useState(false);
  const [dark, setDark] = useState(false);
  const [mode, setMode] = useState<'vllm' | 'ollama'>('ollama');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem('vivu-theme');
    if (saved === 'dark') setDark(true);
  }, []);

  useEffect(() => {
    const fetchConversations = async () => {
      if (!isSignedIn) return;
      try {
        const res = await fetch('/api/conversations');
        if (res.ok) setConversations(await res.json());
      } catch (err) { }
    };
    fetchConversations();
  }, [isSignedIn, conversationId]);

  const loadConversation = async (id: string) => {
    try {
      const res = await fetch(`/api/conversations/${id}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
        setConversationId(data.id);
        setSidebarOpen(false);
      }
    } catch (err) { }
  };

  const newConversation = () => {
    setMessages([]);
    setConversationId(null);
    setSidebarOpen(false);
  };

  const toggleDark = () => {
    setDark(prev => {
      localStorage.setItem('vivu-theme', !prev ? 'dark' : 'light');
      return !prev;
    });
  };

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const autoGrow = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  };

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isLoading) return;
    const trimmed = userText.trim();
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: trimmed };
    const allMessages = [...messages, userMsg];
    setMessages(allMessages);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setIsLoading(true);
    setSidebarOpen(false);

    const assistantId = crypto.randomUUID();
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '' }]);

    abortControllerRef.current = new AbortController();
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: allMessages, mode, top_k: 3, conversationId }),
        signal: abortControllerRef.current.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          const t = line.trim();
          if (t.startsWith('0:')) {
            try {
              const token = JSON.parse(t.slice(2));
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + token } : m));
            } catch (_) { /* skip */ }
          } else if (t.startsWith('8:')) {
            try {
              const metaArr = JSON.parse(t.slice(2));
              for (const meta of (Array.isArray(metaArr) ? metaArr : [metaArr])) {
                if (meta.type === 'budget_chart' && meta.data) {
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId ? { ...m, budgetData: meta.data } : m
                  ));
                } else if (meta.type === 'status' && meta.message) {
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId ? { ...m, statusText: meta.message } : m
                  ));
                } else if (meta.conversationId) {
                  setConversationId(meta.conversationId);
                }
              }
            } catch (_) { /* skip */ }
          } else if (t.startsWith('3:')) {
            try {
              const err = JSON.parse(t.slice(2));
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: `⚠️ ${err}` } : m));
            } catch (_) { /* skip */ }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: `⚠️ Lỗi kết nối: ${err.message}` } : m
        ));
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const stopGeneration = () => { abortControllerRef.current?.abort(); setIsLoading(false); };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  // ── Theme classes ──────────────────────────────────────────────────────────
  const bg = dark ? 'bg-gray-950' : 'bg-white';
  const bgSidebar = dark ? 'bg-gray-900 border-gray-800' : 'bg-gray-50 border-gray-100';
  const bgInput = dark ? 'bg-gray-900 border-gray-700 focus-within:border-emerald-600/50' : 'bg-white border-gray-200 focus-within:border-emerald-400 shadow-sm';
  const bgTextarea = dark ? 'bg-transparent text-gray-100 placeholder:text-gray-500' : 'bg-transparent text-gray-900 placeholder:text-gray-400';
  const bgCard = dark ? 'bg-gray-800/60 border-gray-700 hover:border-emerald-700/50' : 'bg-white border-gray-100 hover:border-emerald-200 shadow-sm hover:shadow-md';
  const textPrimary = dark ? 'text-gray-100' : 'text-gray-900';
  const textSecondary = dark ? 'text-gray-400' : 'text-gray-500';
  const bgUserMsg = 'bg-emerald-500 text-white';
  const bgBotMsg = dark ? 'bg-gray-800 text-gray-100 border border-gray-700' : 'bg-gray-50 text-gray-800 border border-gray-100';
  const btnIcon = dark ? 'hover:bg-gray-800 text-gray-400 hover:text-gray-200' : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700';
  const sidebarItem = dark
    ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100';

  if (!mounted) return null;

  return (
    <div className={`flex h-screen ${bg} ${textPrimary} font-sans transition-colors duration-200`}>

      {/* ── Sidebar ── */}
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 flex flex-col border-r transition-transform duration-300 ${bgSidebar}
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:relative md:translate-x-0
      `}>
        {/* Logo */}
        <div className={`p-5 border-b ${dark ? 'border-gray-800' : 'border-gray-100'} flex items-center justify-between`}>
          <Link href="/" className="flex items-center gap-2 font-bold text-lg group">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md group-hover:shadow-emerald-200 transition-shadow">
              <MapPin className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">ViVu</span>
          </Link>
          <button className={`md:hidden p-1.5 rounded-lg ${btnIcon}`} onClick={() => setSidebarOpen(false)}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Engine toggle */}
        <div className={`p-4 border-b ${dark ? 'border-gray-800' : 'border-gray-100'}`}>
          <p className={`text-[10px] font-semibold uppercase tracking-widest mb-2 ${textSecondary}`}>Engine AI</p>
          <div className={`flex rounded-xl p-0.5 ${dark ? 'bg-gray-800 border border-gray-700' : 'bg-gray-100 border border-gray-200'}`}>
            {(['ollama', 'vllm'] as const).map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs py-1.5 rounded-lg font-medium transition-all duration-200 ${mode === m
                  ? 'bg-emerald-500 text-white shadow-md'
                  : `${textSecondary} hover:${textPrimary}`
                  }`}>
                {m === 'vllm' ? <Zap className="w-3 h-3" /> : <Cpu className="w-3 h-3" />}
                {m === 'vllm' ? 'vLLM' : 'Ollama'}
              </button>
            ))}
          </div>
        </div>

        {/* Chat history */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isSignedIn && (
            <button onClick={newConversation} className={`w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-all bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm`}>
              <Plus className="w-4 h-4" /> Cuộc trò chuyện mới
            </button>
          )}

          <div className="pt-2 space-y-0.5">
            <p className={`text-[10px] font-semibold uppercase tracking-widest mb-2 px-2 mt-2 ${textSecondary}`}>Lịch sử</p>
            {!isSignedIn ? (
              <div className="px-3 py-2">
                <p className={`text-xs mb-3 ${textSecondary}`}>Đăng nhập để lưu lịch sử vĩnh viễn.</p>
                <button onClick={() => signIn('google')} className="w-full flex items-center justify-center gap-2 py-2 text-xs font-medium bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                  <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="w-4 h-4" alt="Google" />
                  Đăng nhập Google
                </button>
              </div>
            ) : conversations.length === 0 ? (
              <p className={`text-xs px-3 py-2 ${textSecondary}`}>Chưa có cuộc trò chuyện nào.</p>
            ) : (
              conversations.map(c => (
                <button key={c.id} onClick={() => loadConversation(c.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors truncate ${conversationId === c.id
                      ? (dark ? 'bg-gray-800 text-emerald-400' : 'bg-gray-200 text-emerald-600')
                      : sidebarItem
                    }`}>
                  {c.title || 'Cuộc trò chuyện mới'}
                </button>
              ))
            )}
          </div>
        </div>


        <Link href="/"
          className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm transition-colors ${sidebarItem}`}>
          <ChevronLeft className="w-4 h-4" /> Về trang chủ
        </Link>
        <button onClick={toggleDark}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${dark ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400 hover:bg-amber-500/15' : 'bg-gray-100 border border-gray-200 text-gray-600 hover:bg-gray-200'
            }`}>
          {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          {dark ? 'Chế độ sáng' : 'Chế độ tối'}
        </button>
        {isSignedIn && (
          <button onClick={() => signOut()} className={`mt-2 w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10`}>
            Đăng xuất
          </button>
        )}
        {/* Bottom controls */}

      </aside>

      {/* ── Main Chat ── */}
      <div className="flex-1 flex flex-col min-h-0">

        {/* Mobile top bar */}
        <div className={`md:hidden flex items-center justify-between px-4 py-3 border-b shrink-0 ${dark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-100 shadow-sm'}`}>
          <button onClick={() => setSidebarOpen(true)} className={`p-2 rounded-lg ${btnIcon}`}>
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-semibold text-sm bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">
            ViVu AI · {mode === 'vllm' ? 'vLLM' : 'Ollama'}
          </span>
          <button onClick={toggleDark} className={`p-2 rounded-lg ${btnIcon}`}>
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>

        {/* ── Messages ── */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-8">

            {/* Empty state */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 shadow-lg ${dark ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-emerald-50 border border-emerald-100'}`}>
                  <Bot className="w-8 h-8 text-emerald-500" />
                </div>
                <h2 className={`text-2xl font-bold mb-2 ${textPrimary}`}>Xin chào!</h2>
                <p className={`text-sm max-w-sm mb-8 leading-relaxed ${textSecondary}`}>
                  Tôi là <span className="text-emerald-600 font-semibold">ViVu</span>, trợ lý du lịch AI.
                  Hỏi tôi bất kỳ điều gì về du lịch Việt Nam!
                </p>
                <div className="grid grid-cols-2 gap-3 w-full max-w-md">
                  {SUGGESTIONS.map(s => (
                    <button suppressHydrationWarning key={s.label} onClick={() => sendMessage(s.text)}
                      className={`flex items-start gap-2 p-4 rounded-xl border text-left text-sm transition-all group ${bgCard}`}>
                      <span className="shrink-0">{s.icon}</span>
                      <span className={`${textSecondary} group-hover:${textPrimary} transition-colors text-xs`}>{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Messages */}
            {messages.map(m => (
              <div key={m.id} className={`mb-7 flex ${m.role === 'user' ? 'justify-end' : 'justify-start gap-3'}`}>
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 shrink-0 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md mt-0.5">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                <div className={`${m.role === 'user'
                  ? `max-w-[75%] rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm ${bgUserMsg}`
                  : `flex-1 min-w-0 rounded-2xl rounded-tl-sm px-5 py-3 ${bgBotMsg}`
                  }`}>
                  {(m.role === 'assistant' && (m.content === '' || m.content === '🌴 ') && isLoading) ? (
                    <span className="flex items-center gap-2 h-6 text-[15px] font-medium text-emerald-600 dark:text-emerald-400 animate-pulse whitespace-pre-wrap">
                      {m.statusText || '🌴 Đang phân tích trả lời câu hỏi....'}
                    </span>
                  ) : (
                    m.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:bg-gray-800 prose-pre:border prose-pre:border-gray-700">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content}
                        </ReactMarkdown>
                        {m.budgetData && <BudgetChart data={m.budgetData} />}
                      </div>
                    ) : (
                      <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{m.content}</p>
                    )
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} className="h-2" />
          </div>
        </div>

        {/* ── Input ── */}
        <div className={`shrink-0 px-4 pb-5 pt-3 ${dark ? '' : ''}`}>
          <div className="max-w-3xl mx-auto">
            <div className={`flex items-end gap-3 border rounded-2xl px-4 py-3 transition-all ${bgInput}`}>
              <textarea suppressHydrationWarning
                ref={textareaRef} rows={1}
                className={`flex-1 resize-none outline-none text-[15px] leading-relaxed max-h-40 overflow-y-auto ${bgTextarea}`}
                placeholder={`Hỏi về du lịch Việt Nam... `}
                value={input}
                onChange={e => { setInput(e.target.value); autoGrow(); }}
                onKeyDown={onKeyDown}
                disabled={isLoading}
              />
              {isLoading ? (
                <button onClick={stopGeneration}
                  className="shrink-0 w-9 h-9 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 flex items-center justify-center transition-colors">
                  <Square className="w-4 h-4 text-red-500 fill-red-500" />
                </button>
              ) : (
                <button suppressHydrationWarning onClick={() => sendMessage(input)}
                  disabled={!input.trim()}
                  className="shrink-0 w-9 h-9 rounded-xl bg-emerald-500 hover:bg-emerald-600 flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-emerald-200">
                  <Send className="w-4 h-4 text-white" />
                </button>
              )}
            </div>
            <p className={`text-center text-[11px] mt-2 ${textSecondary}`}>
              ViVu có thể mắc lỗi. Hãy kiểm chứng thông tin quan trọng. ·{' '}
              <Link href="/" className="text-emerald-600 hover:underline">Về trang chủ</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
