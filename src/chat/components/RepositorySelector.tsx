import React, { useState } from 'react';
import type { RepositoryListItem } from '../types';
import { Settings, Trash2, X, RefreshCw, AlertTriangle } from 'lucide-react';
import { useChatContext } from '../ChatContext';

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
  const [isManageOpen, setIsManageOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isClearingAll, setIsClearingAll] = useState(false);

  // Use memoized ready repositories from context (computed once when repos change)
  const displayRepos = readyRepositories;

  const handleDelete = async (id: string, name: string) => {
    const confirm = window.confirm(`Are you sure you want to delete the repository "${name}"? This will permanently wipe its metadata, vector index, and grounded chat history.`);
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
    const confirm = window.confirm('Are you absolutely sure you want to CLEAR ALL repositories? This will reset DevMind to a fresh installation state.');
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

  return (
    <div className="repo-selector-container">
      <div className="flex items-center justify-between mb-1.5">
        <label className="repo-selector-label uppercase text-[9px] font-mono tracking-wider text-dark-400">GROUND CHAT IN:</label>
        <button
          onClick={() => setIsManageOpen(true)}
          className="manage-repos-btn flex items-center gap-1 text-[10px] font-mono text-cyan-500 hover:text-cyan-400 transition bg-transparent border-none cursor-pointer p-0"
          title="Manage Repositories"
        >
          <Settings className="w-3 h-3" />
          <span>MANAGE</span>
        </button>
      </div>

      <div className="relative">
        <select
          className={`repo-selector-dropdown ${disabled ? 'repo-selector-dropdown--disabled' : ''}`}
          value={selectedId || ''}
          onChange={(e) => onSelect(e.target.value)}
          disabled={disabled}
        >
          <option value="" disabled>
            -- SELECT INDEXED REPOSITORY --
          </option>
          {displayRepos.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.owner}/{repo.name} ({repo.language || 'Unknown'})
            </option>
          ))}
        </select>
        {!disabled && <span className="repo-selector-arrow">▾</span>}
      </div>

      {selectedId && !disabled && (
        <span className="repo-selector-helper text-cyan-500/80 text-[10px] font-mono mt-1 block">
          ✓ Semantic vector store active (grounded chat).
        </span>
      )}

      {/* Management Modal */}
      {isManageOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1527] border border-dark-800 rounded-lg max-w-md w-full shadow-[0_10px_30px_rgba(0,0,0,0.6)] overflow-hidden">
            {/* Modal Header */}
            <div className="px-4 py-3 border-b border-dark-800 bg-[#090d16] flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-dark-100 uppercase tracking-wider flex items-center gap-2">
                <Settings className="w-4 h-4 text-cyan-500" />
                Manage Indexed Repositories
              </span>
              <button 
                onClick={() => setIsManageOpen(false)}
                className="text-dark-500 hover:text-dark-200 transition bg-transparent border-none cursor-pointer p-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 max-h-[300px] overflow-y-auto space-y-2">
              {repositories.length === 0 ? (
                <div className="text-center py-6 text-dark-500 font-mono text-[11px]">
                  No repositories indexed yet.
                </div>
              ) : (
                repositories.map((repo) => (
                  <div 
                    key={repo.id} 
                    className="flex items-center justify-between p-2.5 bg-[#090d16]/60 border border-dark-800 rounded hover:border-dark-700 transition"
                  >
                    <div className="flex flex-col truncate pr-2 text-left">
                      <span className="text-xs font-semibold font-mono text-dark-200 truncate">
                        {repo.owner}/{repo.name}
                      </span>
                      <span className="text-[10px] font-mono text-dark-500">
                        {repo.language || 'Unknown'} • {repo.status}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDelete(repo.id, `${repo.owner}/${repo.name}`)}
                      disabled={deletingId !== null || isClearingAll}
                      className="text-red-500 hover:text-red-400 p-1.5 rounded hover:bg-red-500/10 transition disabled:opacity-40 bg-transparent border-none cursor-pointer"
                      title="Delete Repository"
                    >
                      {deletingId === repo.id ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            {repositories.length > 0 && (
              <div className="px-4 py-3 border-t border-dark-800 bg-[#090d16]/80 flex items-center justify-between">
                <span className="text-[9px] font-mono text-dark-500">
                  TOTAL INDEXED: {repositories.length}
                </span>
                <button
                  onClick={handleClearAll}
                  disabled={deletingId !== null || isClearingAll}
                  className="flex items-center gap-1 bg-red-600 hover:bg-red-500 disabled:bg-red-950/40 text-white font-mono text-[10px] px-3 py-1.5 rounded transition font-semibold border-none cursor-pointer"
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
