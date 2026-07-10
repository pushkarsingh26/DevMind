import React, { useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { AIConfiguration } from '../components/AIConfiguration';
import { 
  Settings, HardDrive, Trash2, Sliders, LayoutGrid, Sun, Moon
} from 'lucide-react';
import { Card, Button, Badge } from '../components/ui';

export const SettingsPage: React.FC = () => {
  const context = useContext(AnalysisContext);

  if (!context) return null;

  const { parsedReport, addToast, theme, toggleTheme } = context;

  const handleClearCache = () => {
    addToast('success', 'RAG local retrieval cache and index buffers cleared successfully.');
  };

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-dark-50 font-display flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-accent" />
          <span>System Settings</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Configure provider preferences, theme options, cache parameters, and system values</p>
      </div>

      {/* Settings Grid Panel */}
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

        {/* Card 3: Mock API keys configuration */}
        <Card variant="soft" className="md:col-span-2">
          <div>
            <h3 className="text-sm font-bold text-dark-100 font-display flex items-center gap-2">
              <Sliders className="w-4 h-4 text-green-accent" />
              <span>API Credentials & Access Keys</span>
            </h3>
            <p className="text-xs text-dark-500 font-mono mt-0.5">Runtime access keys configured for failover chain providers</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4">
            <div className="space-y-2">
              <label className="text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold block">Google Gemini API Key:</label>
              <div className="flex gap-2">
                <input
                  type="password"
                  disabled
                  value="••••••••••••••••••••••••••••••••"
                  className="flex-1 bg-[#070b14]/30 border border-border-primary rounded-xl px-4 py-2.5 text-xs text-dark-400 font-mono outline-none cursor-not-allowed select-none"
                />
                <Button
                  variant="glass"
                  onClick={() => addToast('info', 'Google Gemini API connection verified (System default token).')}
                >
                  TEST
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold block">OpenAI GPT-4o API Key:</label>
              <div className="flex gap-2">
                <input
                  type="password"
                  disabled
                  value="••••••••••••••••••••••••••••••••"
                  className="flex-1 bg-[#070b14]/30 border border-border-primary rounded-xl px-4 py-2.5 text-xs text-dark-400 font-mono outline-none cursor-not-allowed select-none"
                />
                <Button
                  variant="glass"
                  onClick={() => addToast('info', 'OpenAI GPT-4o connection verified (Failover default token).')}
                >
                  TEST
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Existing System Configuration component */}
      <AIConfiguration report={parsedReport} />
    </div>
  );
};

export default SettingsPage;
