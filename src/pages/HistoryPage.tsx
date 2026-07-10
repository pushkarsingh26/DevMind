import React, { useContext, useState } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { useChatContext } from '../chat/ChatContext';
import { useNavigate } from 'react-router-dom';
import { 
  History, MessageSquare, FolderGit2, Trash2, Cpu, 
  RefreshCw, Trash, ArrowUpRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, Button, Badge } from '../components/ui';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const analysisContext = useContext(AnalysisContext);
  const chatContext = useChatContext();

  const [activeTab, setActiveTab] = useState<'runs' | 'chats' | 'repos'>('runs');
  const [deletingRepoId, setDeletingRepoId] = useState<string | null>(null);

  if (!analysisContext) return null;

  const { history, clearHistory, deleteHistoryItem, loadHistoryItem } = analysisContext;
  const { conversations, selectConversation, deleteConversation, readyRepositories, deleteRepository, clearAll } = chatContext;

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleRestoreRun = (item: any) => {
    loadHistoryItem(item);
    navigate('/repositories');
  };

  const handleRestoreChat = (id: string) => {
    selectConversation(id);
    navigate('/chat');
  };

  const handleRestoreRepo = (id: string) => {
    chatContext.selectRepository(id);
    chatContext.startNewConversation();
    navigate('/chat');
  };

  const handleDeleteRepository = async (id: string, name: string) => {
    const confirm = window.confirm(`Are you sure you want to delete indexed repository "${name}"? This wipes its vector mappings.`);
    if (confirm) {
      setDeletingRepoId(id);
      try {
        await deleteRepository(id);
      } catch (e) {
        console.error(e);
      } finally {
        setDeletingRepoId(null);
      }
    }
  };

  const handleClearRepos = async () => {
    const confirm = window.confirm('Are you absolutely sure you want to clear ALL indexed repository vector stores?');
    if (confirm) {
      try {
        await clearAll();
      } catch (e) {
        console.error(e);
      }
    }
  };

  const handleDeleteAnalysisItem = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const confirm = window.confirm('Remove this analysis record from cache history?');
    if (confirm) {
      deleteHistoryItem(id);
    }
  };

  return (
    <div className="space-y-8 select-none text-left">
      
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-dark-50 font-display flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-accent" />
          <span>Platform History Console</span>
        </h2>
        <p className="text-xs text-dark-500 font-mono mt-1">Review, restore, or wipe cached runs, chats, and vector indexes</p>
      </div>

      {/* Tabs list */}
      <div className="border-b border-border-primary flex gap-2">
        <button
          onClick={() => setActiveTab('runs')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-mono text-xs font-bold uppercase transition select-none cursor-pointer
            ${activeTab === 'runs'
              ? 'border-cyan-accent text-cyan-accent font-semibold'
              : 'border-transparent text-dark-400 hover:text-dark-200'
            }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Runs ({history.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('chats')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-mono text-xs font-bold uppercase transition select-none cursor-pointer
            ${activeTab === 'chats'
              ? 'border-cyan-accent text-cyan-accent font-semibold'
              : 'border-transparent text-dark-400 hover:text-dark-200'
            }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Chats ({conversations.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('repos')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-mono text-xs font-bold uppercase transition select-none cursor-pointer
            ${activeTab === 'repos'
              ? 'border-cyan-accent text-cyan-accent font-semibold'
              : 'border-transparent text-dark-400 hover:text-dark-200'
            }`}
        >
          <FolderGit2 className="w-3.5 h-3.5" />
          <span>Indexes ({readyRepositories.length})</span>
        </button>
      </div>

      {/* Tab panel body content */}
      <Card variant="soft" className="min-h-[300px] flex flex-col justify-between">
        <div className="flex-1">
          <AnimatePresence mode="wait">
            
            {/* Tab 1: Analysis history runs */}
            {activeTab === 'runs' && (
              <motion.div
                key="runs"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                {history.length === 0 ? (
                  <div className="md:col-span-2 py-16 flex flex-col items-center justify-center text-center text-dark-500 font-mono text-xs">
                    <Cpu className="w-8 h-8 text-dark-600 mb-2.5 animate-pulse" />
                    <span>No historical analysis runs cached.</span>
                  </div>
                ) : (
                  history.map((item) => (
                    <Card
                      key={item.id}
                      interactive
                      onClick={() => handleRestoreRun(item)}
                      className="flex flex-col justify-between min-h-[140px] text-left"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="truncate min-w-0">
                          <span className="text-[10px] font-mono text-dark-500 block">
                            {formatDate(item.timestamp)} @ {formatTimestamp(item.timestamp)}
                          </span>
                          <h4 className="text-sm font-semibold text-dark-200 truncate mt-1">
                            {item.repositoryName}
                          </h4>
                          <span className="text-[9px] font-mono text-dark-400 mt-1 block truncate">
                            Owner: {item.repositoryOwner}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Badge variant="secondary">
                            {item.taskType}
                          </Badge>
                          <button
                            onClick={(e) => handleDeleteAnalysisItem(item.id, e)}
                            className="p-1 rounded-lg hover:bg-rose-500/10 text-dark-500 hover:text-rose-500 transition cursor-pointer bg-transparent border-none"
                            title="Delete record"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <div className="border-t border-border-primary/50 pt-3 mt-3 flex items-center justify-between text-[9px] font-mono text-dark-500">
                        <span className="flex items-center gap-1">
                          <Cpu className="w-3.5 h-3.5 text-purple-accent" />
                          {item.provider} ({item.model.split('/').pop()})
                        </span>
                        <span className="text-dark-300 font-bold uppercase flex items-center gap-1">
                          RESTORE <ArrowUpRight className="w-3 h-3 text-cyan-accent" />
                        </span>
                      </div>
                    </Card>
                  ))
                )}
              </motion.div>
            )}

            {/* Tab 2: Chat conversations */}
            {activeTab === 'chats' && (
              <motion.div
                key="chats"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                className="space-y-2.5"
              >
                {conversations.length === 0 ? (
                  <div className="py-16 flex flex-col items-center justify-center text-center text-dark-500 font-mono text-xs">
                    <MessageSquare className="w-8 h-8 text-dark-600 mb-2.5 animate-pulse" />
                    <span>No active chat conversations index.</span>
                  </div>
                ) : (
                  conversations.map((conv) => (
                    <Card
                      key={conv.id}
                      interactive
                      onClick={() => handleRestoreChat(conv.id)}
                      className="p-4 cursor-pointer text-left flex items-center justify-between"
                    >
                      <div className="truncate min-w-0 flex items-center gap-3">
                        <MessageSquare className="w-4 h-4 text-cyan-accent shrink-0" />
                        <div className="truncate text-left">
                          <span className="text-xs font-semibold text-dark-200 block truncate hover:text-cyan-accent">
                            {conv.title || 'Untitled Session'}
                          </span>
                          <span className="text-[9px] font-mono text-dark-500 mt-1 block">
                            Last active: {new Date(conv.updated_at).toLocaleDateString()} · {conv.message_count} messages
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm('Delete this chat session completely?')) {
                            deleteConversation(conv.id);
                          }
                        }}
                        className="p-2 rounded-lg hover:bg-rose-500/10 text-dark-500 hover:text-rose-500 transition cursor-pointer bg-transparent border-none shrink-0"
                        title="Delete chat"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </Card>
                  ))
                )}
              </motion.div>
            )}

            {/* Tab 3: Indexed repositories */}
            {activeTab === 'repos' && (
              <motion.div
                key="repos"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                {readyRepositories.length === 0 ? (
                  <div className="md:col-span-2 py-16 flex flex-col items-center justify-center text-center text-dark-500 font-mono text-xs">
                    <FolderGit2 className="w-8 h-8 text-dark-600 mb-2.5 animate-pulse" />
                    <span>No indexed vector repositories found.</span>
                  </div>
                ) : (
                  readyRepositories.map((repo) => (
                    <Card
                      key={repo.id}
                      interactive
                      onClick={() => handleRestoreRepo(repo.id)}
                      className="flex flex-col justify-between min-h-[125px] text-left"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="truncate min-w-0">
                          <h4 className="text-sm font-semibold text-dark-200 truncate">
                            {repo.owner}/{repo.name}
                          </h4>
                          <span className="text-[10px] font-mono text-dark-500 mt-1 block">
                            Language: <span className="text-cyan-accent font-semibold">{repo.language || 'Unknown'}</span>
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteRepository(repo.id, `${repo.owner}/${repo.name}`);
                          }}
                          disabled={deletingRepoId === repo.id}
                          className="p-1 rounded-lg hover:bg-rose-500/10 text-dark-500 hover:text-rose-500 transition cursor-pointer disabled:opacity-40 bg-transparent border-none shrink-0"
                          title="Delete index mappings"
                        >
                          {deletingRepoId === repo.id ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-rose-400" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>

                      <div className="border-t border-border-primary/50 pt-2.5 mt-2.5 flex items-center justify-between text-[9px] font-mono text-dark-500">
                        <span>STATUS: <span className="text-emerald-400 font-semibold">{repo.status}</span></span>
                        <span className="text-dark-300 font-bold uppercase flex items-center gap-1">
                          CHAT GROUNDING <ArrowUpRight className="w-3 h-3 text-cyan-accent" />
                        </span>
                      </div>
                    </Card>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Tab card footer controls (Clear all actions) */}
        <div className="border-t border-border-primary/60 pt-4 mt-6 flex justify-between items-center">
          <span className="text-[9px] font-mono text-dark-500 uppercase tracking-widest font-semibold">
            PLATFORM DATA DESTRUCTION GATEWAY
          </span>
          {activeTab === 'runs' && history.length > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={clearHistory}
              className="flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>CLEAR REPORT CACHE</span>
            </Button>
          )}
          {activeTab === 'runs' && history.length === 0 && (
            <span className="text-[9px] font-mono text-dark-600">No cached runs to clear</span>
          )}
          {activeTab === 'chats' && conversations.length > 0 && (
            <span className="text-[9px] font-mono text-dark-500 uppercase">Delete chat items individually above</span>
          )}
          {activeTab === 'chats' && conversations.length === 0 && (
            <span className="text-[9px] font-mono text-dark-600">No chat history to clear</span>
          )}
          {activeTab === 'repos' && readyRepositories.length > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={handleClearRepos}
              className="flex items-center gap-1.5"
            >
              <Trash className="w-3.5 h-3.5" />
              <span>WIPE VECTOR INDEXES</span>
            </Button>
          )}
          {activeTab === 'repos' && readyRepositories.length === 0 && (
            <span className="text-[9px] font-mono text-dark-600">No active repositories indexed</span>
          )}
        </div>
      </Card>
    </div>
  );
};

export default HistoryPage;
