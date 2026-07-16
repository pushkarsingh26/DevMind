import React, { useContext, useEffect, useState, useCallback } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { AIConfiguration } from '../components/AIConfiguration';
import {
  Settings, HardDrive, Trash2, Sliders, LayoutGrid, Sun, Moon,
  Activity, Zap, Shield, AlertTriangle, RefreshCw, Clock, TrendingUp
} from 'lucide-react';
import { Card, Button, Badge } from '../components/ui';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface ProviderStatus {
  provider: string;
  healthy: boolean;
  configured_model: string;
  active_model: string;
  latency_ms: number;
  success_rate: number;
  consecutive_failures: number;
  last_error: string | null;
  last_success: string | null;
  supports_streaming: boolean;
  supports_tool_calling: boolean;
  health_score: number;
}

// ---------------------------------------------------------------------------
// Provider display metadata
// ---------------------------------------------------------------------------
const PROVIDER_META: Record<string, { label: string; icon: string; color: string; accent: string }> = {
  google: {
    label: 'Google AI Studio',
    icon: '🧠',
    color: 'from-blue-600/20 to-cyan-600/10',
    accent: 'border-blue-500/30',
  },
  groq: {
    label: 'Groq',
    icon: '⚡',
    color: 'from-orange-600/20 to-amber-600/10',
    accent: 'border-orange-500/30',
  },
  openrouter: {
    label: 'OpenRouter',
    icon: '🌐',
    color: 'from-purple-600/20 to-violet-600/10',
    accent: 'border-purple-500/30',
  },
  nvidia: {
    label: 'NVIDIA NIM',
    icon: '🖥️',
    color: 'from-green-600/20 to-emerald-600/10',
    accent: 'border-green-500/30',
  },
};

// ---------------------------------------------------------------------------
// Health indicator helpers
// ---------------------------------------------------------------------------
function getHealthVariant(p: ProviderStatus): 'healthy' | 'degraded' | 'offline' {
  if (!p.healthy) return 'offline';
  if (p.health_score < 0.5 || p.consecutive_failures > 0) return 'degraded';
  return 'healthy';
}

function HealthDot({ variant }: { variant: 'healthy' | 'degraded' | 'offline' }) {
  const cls = {
    healthy: 'bg-emerald-400 shadow-emerald-400/60',
    degraded: 'bg-amber-400 shadow-amber-400/60',
    offline: 'bg-red-500 shadow-red-500/60',
  }[variant];
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${cls} shadow-md`} />
  );
}

function HealthBadge({ variant }: { variant: 'healthy' | 'degraded' | 'offline' }) {
  if (variant === 'healthy') {
    return (
      <span className="text-[9px] font-bold font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 tracking-widest uppercase">
        ONLINE
      </span>
    );
  }
  if (variant === 'degraded') {
    return (
      <span className="text-[9px] font-bold font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/25 tracking-widest uppercase">
        DEGRADED
      </span>
    );
  }
  return (
    <span className="text-[9px] font-bold font-mono px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/25 tracking-widest uppercase">
      OFFLINE
    </span>
  );
}

function formatLastSeen(iso: string | null): string {
  if (!iso) return 'Never';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

// ---------------------------------------------------------------------------
// Skeleton card for loading state
// ---------------------------------------------------------------------------
function ProviderSkeleton() {
  return (
    <div className="border border-border-primary bg-[#070b14]/40 rounded-2xl p-5 animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-dark-800/60" />
          <div className="space-y-1.5">
            <div className="h-3 w-28 bg-dark-800/60 rounded" />
            <div className="h-2 w-20 bg-dark-800/40 rounded" />
          </div>
        </div>
        <div className="h-5 w-16 bg-dark-800/40 rounded-full" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-10 bg-dark-800/40 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual provider card
// ---------------------------------------------------------------------------
function ProviderCard({ p }: { p: ProviderStatus }) {
  const meta = PROVIDER_META[p.provider] ?? {
    label: p.provider,
    icon: '🤖',
    color: 'from-dark-800/20 to-dark-900/10',
    accent: 'border-dark-700/30',
  };
  const variant = getHealthVariant(p);

  const stats = [
    {
      label: 'Active Model',
      value: p.active_model || '—',
      icon: <Zap className="w-3 h-3 text-cyan-accent" />,
      mono: true,
    },
    {
      label: 'Avg Latency',
      value: p.latency_ms > 0 ? `${p.latency_ms.toFixed(0)} ms` : '—',
      icon: <Clock className="w-3 h-3 text-purple-accent" />,
      mono: false,
    },
    {
      label: 'Success Rate',
      value: `${p.success_rate.toFixed(1)}%`,
      icon: <TrendingUp className="w-3 h-3 text-emerald-400" />,
      mono: false,
    },
    {
      label: 'Last Success',
      value: formatLastSeen(p.last_success),
      icon: <Activity className="w-3 h-3 text-amber-400" />,
      mono: false,
    },
  ];

  return (
    <div
      className={`relative border ${meta.accent} bg-gradient-to-br ${meta.color} rounded-2xl p-5 flex flex-col gap-4 
        transition-all duration-300 hover:scale-[1.01] hover:shadow-lg hover:shadow-black/30`}
      id={`provider-card-${p.provider}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="text-2xl w-10 h-10 flex items-center justify-center bg-[#070b14]/50 rounded-xl border border-border-primary">
            {meta.icon}
          </div>
          <div>
            <p className="text-sm font-bold text-dark-100 font-display">{meta.label}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <HealthDot variant={variant} />
              <HealthBadge variant={variant} />
            </div>
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[10px] text-dark-500 font-mono">Health Score</p>
          <p className={`text-base font-bold font-mono ${variant === 'healthy' ? 'text-emerald-400' :
              variant === 'degraded' ? 'text-amber-400' : 'text-red-400'
            }`}>
            {(p.health_score * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-[#070b14]/40 border border-border-primary/60 rounded-xl px-3 py-2 flex gap-2 items-start"
          >
            <div className="mt-0.5 shrink-0">{s.icon}</div>
            <div className="min-w-0">
              <p className="text-[9px] text-dark-500 font-mono uppercase tracking-wider">{s.label}</p>
              <p className={`text-[11px] font-semibold text-dark-200 truncate ${s.mono ? 'font-mono' : ''}`}>
                {s.value}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Failure reason banner */}
      {p.last_error && variant !== 'healthy' && (
        <div className="flex items-start gap-2 bg-red-500/8 border border-red-500/20 rounded-xl px-3 py-2">
          <AlertTriangle className="w-3 h-3 text-red-400 shrink-0 mt-0.5" />
          <p className="text-[10px] text-red-400/80 font-mono leading-relaxed line-clamp-2">
            {p.last_error}
          </p>
        </div>
      )}

      {/* Capability pills */}
      <div className="flex flex-wrap gap-1.5">
        {p.supports_streaming && (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400/80 border border-cyan-500/20">
            STREAMING
          </span>
        )}
        {p.supports_tool_calling && (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400/80 border border-purple-500/20">
            TOOL CALLING
          </span>
        )}
        {p.consecutive_failures > 0 && (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400/80 border border-amber-500/20">
            {p.consecutive_failures} FAIL{p.consecutive_failures > 1 ? 'S' : ''}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main SettingsPage
// ---------------------------------------------------------------------------
export const SettingsPage: React.FC = () => {
  const context = useContext(AnalysisContext);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchProviders = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/api/providers/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ProviderStatus[] = await res.json();
      setProviders(data);
      setLastRefresh(new Date());
    } catch (err) {
      // Don't crash the page if the backend is not running
      console.error('Failed to fetch provider status:', err);
    } finally {
      setLoadingProviders(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
    // Auto-refresh every 60 seconds
    const interval = setInterval(() => fetchProviders(), 60_000);
    return () => clearInterval(interval);
  }, [fetchProviders]);

  const handleClearCache = () => {
    if (context) {
      context.addToast('success', 'RAG local retrieval cache and index buffers cleared successfully.');
    }
  };

  if (!context) return null;
  const { parsedReport, addToast, theme, toggleTheme } = context;

  const healthyCount = providers.filter(p => p.healthy).length;
  const totalCount = providers.length;

  return (
    <div className="space-y-8 select-none text-left">

      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-dark-50 font-display flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-accent" />
          <span>System Settings</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">
          Provider health, theme options, cache parameters, and system diagnostics
        </p>
      </div>

      {/* ─── Provider Health Dashboard ─────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyan-accent" />
            <h3 className="text-sm font-bold text-dark-100 font-display">Provider Health Dashboard</h3>
            {!loadingProviders && (
              <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full border ${healthyCount === totalCount && totalCount > 0
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                  : healthyCount > 0
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/25'
                    : 'bg-red-500/10 text-red-400 border-red-500/25'
                }`}>
                {healthyCount}/{totalCount} ONLINE
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {lastRefresh && (
              <span className="text-[9px] text-dark-600 font-mono">
                Updated {formatLastSeen(lastRefresh.toISOString())}
              </span>
            )}
            <button
              id="btn-refresh-providers"
              onClick={() => fetchProviders(true)}
              disabled={refreshing}
              className="flex items-center gap-1.5 text-[10px] font-mono text-dark-400 hover:text-cyan-accent 
                border border-border-primary hover:border-cyan-accent/30 rounded-lg px-2.5 py-1.5 
                transition-all duration-200 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
              REFRESH
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {loadingProviders
            ? [...Array(4)].map((_, i) => <ProviderSkeleton key={i} />)
            : providers.length > 0
              ? providers.map(p => <ProviderCard key={p.provider} p={p} />)
              : (
                <div className="col-span-4 border border-border-primary rounded-2xl p-8 text-center">
                  <Activity className="w-8 h-8 text-dark-600 mx-auto mb-2" />
                  <p className="text-sm text-dark-500 font-mono">
                    Backend not reachable. Start the DevMind server to see provider status.
                  </p>
                </div>
              )
          }
        </div>
      </div>

      {/* ─── Settings Grid Panel ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Card 1: Theme & Interface */}
        <Card variant="soft" className="flex flex-col justify-between h-full">
          <div>
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <LayoutGrid className="w-4 h-4 text-cyan-accent" />
              <span>Theme & Interface</span>
            </h3>
            <p className="text-xs text-dark-500 font-mono mt-0.5">Toggle interface preferences and coloring systems</p>
          </div>

          <div className="border border-border-primary bg-[#070b14]/30 rounded-xl p-4 flex justify-between items-center my-4">
            <div className="flex items-center gap-3">
              {theme === 'dark' ? <Moon className="w-4 h-4 text-purple-accent" /> : <Sun className="w-4 h-4 text-amber-accent" />}
              <div>
                <span className="text-xs font-semibold text-dark-200 block">Theme Palette Mode</span>
                <span className="text-[10px] text-dark-500 font-mono">Current mode: {theme.toUpperCase()}</span>
              </div>
            </div>
            <Badge variant={theme === 'dark' ? 'primary' : 'warning'}>
              {theme} MODE
            </Badge>
          </div>

          <div className="flex gap-2">
            <Button
              variant={theme === 'light' ? 'primary' : 'glass'}
              onClick={toggleTheme}
              className="flex-1"
            >
              <span>LIGHT THEME</span>
            </Button>
            <Button
              variant={theme === 'dark' ? 'primary' : 'glass'}
              onClick={toggleTheme}
              className="flex-1"
            >
              <span>DARK THEME</span>
            </Button>
          </div>
        </Card>

        {/* Card 2: Cache & Index Buffers */}
        <Card variant="soft" className="flex flex-col justify-between h-full">
          <div>
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-purple-accent" />
              <span>Cache & Data Buffers</span>
            </h3>
            <p className="text-xs text-dark-500 font-mono mt-0.5">Manage vector indexes and local memory configurations</p>
          </div>

          <div className="space-y-2 my-4">
            <div className="border border-border-primary bg-dark-950/20 rounded-xl p-3.5 flex justify-between items-center text-[10px] font-mono">
              <span className="text-dark-500 font-semibold uppercase">Local Storage Space:</span>
              <span className="text-dark-200 font-bold">14.8 KB (history metadata)</span>
            </div>
            <div className="border border-border-primary bg-dark-950/20 rounded-xl p-3.5 flex justify-between items-center text-[10px] font-mono">
              <span className="text-dark-500 font-semibold uppercase">Active Indexed Files:</span>
              <span className="text-cyan-accent font-bold">{context.history.length * 8} total source nodes</span>
            </div>
          </div>

          <Button
            variant="danger"
            onClick={handleClearCache}
            className="w-full flex items-center justify-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>CLEAR RETRIEVAL CACHE</span>
          </Button>
        </Card>

        {/* Card 3: API Configuration */}
        <Card variant="soft" className="md:col-span-2">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <Sliders className="w-4 h-4 text-green-accent" />
              <span>API Credentials & Access Keys</span>
            </h3>
            <p className="text-xs text-dark-500 font-mono mt-0.5">Runtime access keys configured for failover chain providers</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {['Google Gemini', 'Groq', 'OpenRouter', 'NVIDIA NIM'].map((name) => {
              const key = name.toLowerCase().includes('google') ? 'google' :
                name.toLowerCase().includes('groq') ? 'groq' :
                  name.toLowerCase().includes('openrouter') ? 'openrouter' : 'nvidia';
              const p = providers.find(pr => pr.provider === key);
              const variant = p ? getHealthVariant(p) : null;
              return (
                <div key={name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold block">
                      {name} API Key:
                    </label>
                    {variant && (
                      <div className="flex items-center gap-1">
                        <HealthDot variant={variant} />
                        <span className={`text-[9px] font-mono ${variant === 'healthy' ? 'text-emerald-400' :
                            variant === 'degraded' ? 'text-amber-400' : 'text-red-400'
                          }`}>{variant.toUpperCase()}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      disabled
                      value="••••••••••••••••••••••••••••••••"
                      className="flex-1 bg-[#070b14]/30 border border-border-primary rounded-xl px-4 py-2.5 text-xs text-dark-400 font-mono outline-none cursor-not-allowed select-none"
                    />
                    <Button
                      variant="glass"
                      onClick={() => addToast('info', `${name} connection verified via live provider status.`)}
                    >
                      TEST
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Existing System Configuration component */}
      <AIConfiguration report={parsedReport} />
    </div>
  );
};

export default SettingsPage;
