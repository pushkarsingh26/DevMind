import React, { useState, useRef, useEffect } from 'react';
import type { RepositoryListItem } from '../types';
import { Settings, Trash2, X, RefreshCw, AlertTriangle, Search, ChevronDown, Check, FolderGit2 } from 'lucide-react';
import { useChatContext } from '../ChatContext';
import { motion, AnimatePresence } from 'framer-motion';

interface RepositorySelectorProps {
  repositories: RepositoryListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export const RepositorySelector: React.FC<RepositorySelectorProps> = ({
  repositories,
  selectedId,
  onSelect,
  disabled = false,
}) => {
  const { deleteRepository, clearAll, readyRepositories } = useChatContext();
  
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [isManageOpen, setIsManageOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isClearingAll, setIsClearingAll] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedRepo = repositories.find((r) => r.id === selectedId);

  const filteredRepos = readyRepositories.filter((repo) =>
    `${repo.owner}/${repo.name}`.toLowerCase().includes(search.toLowerCase()) ||
    (repo.language || '').toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = (id: string) => {
    if (disabled) return;
    onSelect(id);
    setIsOpen(false);
    setSearch('');
  };

  const handleDelete = async (id: string, name: string) => {
    const confirm = window.confirm(`Are you sure you want to delete "${name}"? This will wipe the vector store indices and chat logs.`);
    if (confirm) {
      setDeletingId(id);
      try {
        await deleteRepository(id);
      } catch (e) {
        console.error(e);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const handleClearAll = async () => {
    const confirm = window.confirm('Are you absolutely sure you want to CLEAR ALL repositories?');
    if (confirm) {
      setIsClearingAll(true);
      try {
        await clearAll();
        setIsManageOpen(false);
      } catch (e) {
        console.error(e);
      } finally {
        setIsClearingAll(false);
      }
    }
  };

  // Color mapping for languages
  const getLanguageColor = (lang?: string) => {
    const l = (lang || '').toLowerCase();
    if (l.includes('typescript') || l.includes('ts')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    if (l.includes('javascript') || l.includes('js')) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    if (l.includes('python')) return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
    if (l.includes('go')) return 'bg-teal-500/10 text-teal-400 border-teal-500/20';
    if (l.includes('rust')) return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    return 'bg-dark-800 text-dark-400 border-dark-700/50';
  };

  return (
    <div className="repo-selector-container relative w-full" ref={containerRef}>
      <div className="flex items-center justify-between mb-1.5 px-1">
        <label className="repo-selector-label uppercase text-[9px] font-mono tracking-widest text-dark-500 font-bold">GROUND CHAT IN:</label>
        <button
          onClick={() => setIsManageOpen(true)}
          className="manage-repos-btn flex items-center gap-1 text-[10px] font-mono text-cyan-400 hover:text-cyan-300 transition bg-transparent border-none cursor-pointer p-0"
          title="Manage Repositories"
        >
          <Settings className="w-3 h-3" />
          <span>MANAGE</span>
        </button>
      </div>

      {/* Searchable dropdown trigger */}
      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => setIsOpen(!isOpen)}
          className={`w-full bg-[#070b14]/90 border border-dark-800 hover:border-dark-700 focus:border-cyan-500/50 rounded-xl px-3.5 py-3 text-xs text-dark-200 font-mono flex items-center justify-between focus:outline-none transition-all duration-200 select-none
            ${disabled ? 'opacity-60 cursor-not-allowed bg-dark-900' : 'cursor-pointer'}
            ${isOpen ? 'border-cyan-500/40 ring-1 ring-cyan-500/10' : ''}
          `}
        >
          {selectedRepo ? (
            <div className="flex items-center gap-2 truncate min-w-0">
              <FolderGit2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span className="truncate text-dark-100 font-semibold">{selectedRepo.owner}/{selectedRepo.name}</span>
              <span className={`text-[8px] font-mono border rounded px-1.5 py-0.5 shrink-0 ${getLanguageColor(selectedRepo.language)}`}>
                {selectedRepo.language || 'Codebase'}
              </span>
            </div>
          ) : (
            <span className="text-dark-500">SELECT INDEXED REPOSITORY</span>
          )}
          {!disabled && <ChevronDown className={`w-3.5 h-3.5 text-dark-400 transition-transform duration-200 ${isOpen ? 'rotate-180 text-cyan-400' : ''}`} />}
        </button>

        {/* Dropdown Options List */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 5, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute left-0 right-0 mt-2 z-50 bg-[#0f172a] border border-dark-800 rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[300px]"
            >
              {/* Dropdown Search Input */}
              <div className="p-2 border-b border-dark-850 bg-[#070b14]/50 flex items-center gap-2 shrink-0">
                <Search className="w-3.5 h-3.5 text-dark-500 ml-1.5 shrink-0" />
                <input
                  type="text"
                  placeholder="Search repository..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-transparent text-xs text-dark-200 outline-none border-none p-1.5 font-mono placeholder-dark-600"
                />
              </div>

              {/* Items scroll */}
              <div className="overflow-y-auto py-1 flex-1 scrollbar-thin">
                {filteredRepos.length === 0 ? (
                  <div className="p-4 text-center text-[10px] text-dark-600 font-mono">
                    No matching repositories found.
                  </div>
                ) : (
                  filteredRepos.map((repo) => {
                    const isSelected = repo.id === selectedId;
                    return (
                      <button
                        key={repo.id}
                        type="button"
                        onClick={() => handleSelect(repo.id)}
                        className={`w-full flex items-center justify-between px-3.5 py-3 hover:bg-dark-900/60 transition-colors text-left cursor-pointer border-b border-dark-850/30 last:border-b-0
                          ${isSelected ? 'bg-dark-900' : ''}
                        `}
                      >
                        <div className="flex items-center gap-2.5 truncate min-w-0">
                          <FolderGit2 className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-dark-500'}`} />
                          <div className="truncate flex flex-col">
                            <span className={`text-xs font-mono truncate leading-none ${isSelected ? 'text-cyan-400 font-bold' : 'text-dark-200'}`}>
                              {repo.owner}/{repo.name}
                            </span>
                            {repo.repository_hash && (
                              <span className="text-[8px] font-mono text-dark-600 mt-1 uppercase">
                                HASH: {repo.repository_hash.slice(0, 10)}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0 ml-2">
                          <span className={`text-[8px] font-mono border rounded px-1.5 py-0.5 ${getLanguageColor(repo.language)}`}>
                            {repo.language || 'Codebase'}
                          </span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {selectedId && !disabled && (
        <span className="repo-selector-helper text-emerald-400/90 text-[10px] font-mono mt-1 px-1 block">
          ✓ Vector context active (RAG grounded).
        </span>
      )}

      {/* Repository Management Modal */}
      {isManageOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-dark-800 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="px-5 py-4 border-b border-dark-800 bg-[#070b14] flex items-center justify-between">
              <span className="font-display text-sm font-bold text-dark-100 flex items-center gap-2">
                <Settings className="w-4 h-4 text-cyan-400" />
                Manage Indexed Repositories
              </span>
              <button 
                onClick={() => setIsManageOpen(false)}
                className="text-dark-500 hover:text-dark-200 transition bg-transparent border-none cursor-pointer p-1 rounded-lg hover:bg-dark-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* List Content */}
            <div className="p-5 max-h-[300px] overflow-y-auto space-y-2.5">
              {repositories.length === 0 ? (
                <div className="text-center py-8 text-dark-500 font-mono text-[11px]">
                  No repositories indexed yet.
                </div>
              ) : (
                repositories.map((repo) => (
                  <div 
                    key={repo.id} 
                    className="flex items-center justify-between p-3.5 bg-[#070b14]/50 border border-dark-850 rounded-xl hover:border-dark-850 hover:bg-[#070b14] transition duration-200"
                  >
                    <div className="flex flex-col truncate pr-2 text-left">
                      <span className="text-xs font-semibold font-sans text-dark-200 truncate">
                        {repo.owner}/{repo.name}
                      </span>
                      <span className="text-[10px] font-mono text-dark-500 mt-1">
                        {repo.language || 'Unknown'} · Status: <span className={repo.status === 'READY' ? 'text-emerald-400' : 'text-amber-400 animate-pulse'}>{repo.status}</span>
                      </span>
                    </div>
                    <button
                      onClick={() => handleDelete(repo.id, `${repo.owner}/${repo.name}`)}
                      disabled={deletingId !== null || isClearingAll}
                      className="text-rose-500 hover:text-rose-400 p-2 rounded-lg hover:bg-rose-500/10 transition disabled:opacity-40 bg-transparent border-none cursor-pointer shrink-0"
                      title="Delete Repository"
                    >
                      {deletingId === repo.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            {repositories.length > 0 && (
              <div className="px-5 py-4 border-t border-dark-800 bg-[#070b14]/80 flex items-center justify-between">
                <span className="text-[10px] font-mono text-dark-500 uppercase tracking-wider font-semibold">
                  Total indexed: {repositories.length}
                </span>
                <button
                  onClick={handleClearAll}
                  disabled={deletingId !== null || isClearingAll}
                  className="flex items-center gap-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-rose-950/40 text-white font-mono text-[10px] px-3.5 py-2 rounded-xl transition font-semibold border-none cursor-pointer"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>CLEAR ALL DATA</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
