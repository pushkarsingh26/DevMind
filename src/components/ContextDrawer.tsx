import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Search,
  ChevronDown,
  Copy,
  Check,
  FileCode,
  Tag,
  Layers,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import type { ContextChunk } from '../types';

interface ContextDrawerProps {
  open: boolean;
  onClose: () => void;
  chunks: ContextChunk[];
}

const PAGE_SIZE = 20;

export const ContextDrawer: React.FC<ContextDrawerProps> = ({ open, onClose, chunks }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Reset state when drawer opens/closes
  useEffect(() => {
    if (open) {
      setSearchQuery('');
      setExpandedIndex(null);
      setVisibleCount(PAGE_SIZE);
    }
  }, [open]);

  // Keyboard ESC to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Lock body scroll when drawer is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  // Filtered chunks based on search
  const filteredChunks = useMemo(() => {
    if (!searchQuery.trim()) return chunks;
    const q = searchQuery.toLowerCase();
    return chunks.filter(
      (c) =>
        c.path.toLowerCase().includes(q) ||
        c.content.toLowerCase().includes(q)
    );
  }, [chunks, searchQuery]);

  // Paginated slice
  const displayedChunks = useMemo(
    () => filteredChunks.slice(0, visibleCount),
    [filteredChunks, visibleCount]
  );

  const hasMore = visibleCount < filteredChunks.length;

  // Intersection Observer for infinite scroll lazy loading
  useEffect(() => {
    if (!open || !sentinelRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
          setIsLoadingMore(true);
          // Simulate a small delay for a smoother loading feel
          setTimeout(() => {
            setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, filteredChunks.length));
            setIsLoadingMore(false);
          }, 300);
        }
      },
      { root: listRef.current, threshold: 0.1 }
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [open, hasMore, isLoadingMore, filteredChunks.length]);

  // Reset visible count on search change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
    setExpandedIndex(null);
  }, [searchQuery]);

  const handleCopy = useCallback((content: string, id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const toggleExpand = useCallback((index: number) => {
    setExpandedIndex((prev) => (prev === index ? null : index));
  }, []);

  // Unique files covered
  const uniqueFiles = useMemo(() => new Set(chunks.map((c) => c.path)).size, [chunks]);
  const topScore = useMemo(() => {
    const scores = chunks.filter((c) => c.score !== undefined).map((c) => c.score as number);
    return scores.length > 0 ? Math.max(...scores) : 0;
  }, [chunks]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Drawer panel */}
          <motion.div
            className="fixed top-0 right-0 h-full z-[95] flex flex-col bg-dark-950 border-l border-dark-800 shadow-2xl shadow-black/50"
            style={{ width: 'min(720px, 90vw)' }}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-dark-800 bg-dark-900/80 backdrop-blur shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                  <Layers className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-dark-100 font-mono uppercase tracking-wider">
                    Retrieved Semantic Context
                  </h2>
                  <p className="text-[11px] text-dark-500 font-mono mt-0.5">
                    {filteredChunks.length} of {chunks.length} chunks · {uniqueFiles} files · Top: {(topScore * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-dark-400 hover:text-dark-100 hover:bg-dark-800 transition-colors cursor-pointer"
                aria-label="Close context drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search bar */}
            <div className="px-6 py-3 border-b border-dark-850 shrink-0">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-500 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search by file path or content..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-dark-200 font-mono placeholder:text-dark-600 focus:outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/20 transition-all"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-500 hover:text-dark-300 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Chunk list */}
            <div ref={listRef} className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-4 space-y-3">
              {displayedChunks.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 text-dark-500 font-mono text-sm">
                  <Search className="w-8 h-8 mb-3 text-dark-600" />
                  <p>No chunks match your search.</p>
                </div>
              )}

              {displayedChunks.map((chunk, idx) => {
                const chunkId = chunk.id || chunk.chunk_id || `chunk_${idx}`;
                const isExpanded = expandedIndex === idx;
                const scoreStr = chunk.score !== undefined ? `${(chunk.score * 100).toFixed(1)}%` : 'N/A';
                const scoreValue = chunk.score ?? 0;

                // Score-based color intensity
                const scoreColor =
                  scoreValue >= 0.8
                    ? 'text-emerald-400 border-emerald-500/20 bg-emerald-950/20'
                    : scoreValue >= 0.6
                      ? 'text-cyan-400 border-cyan-500/20 bg-cyan-950/20'
                      : scoreValue >= 0.4
                        ? 'text-amber-400 border-amber-500/20 bg-amber-950/20'
                        : 'text-dark-400 border-dark-700 bg-dark-900';

                return (
                  <motion.div
                    key={chunkId}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15, delay: Math.min(idx * 0.02, 0.3) }}
                    className={`border rounded-lg bg-dark-900/60 transition-all duration-200 overflow-hidden ${
                      isExpanded
                        ? 'border-cyan-500/30 shadow-lg shadow-cyan-500/5'
                        : 'border-dark-800/80 hover:border-dark-700'
                    }`}
                  >
                    {/* Chunk header */}
                    <div
                      onClick={() => toggleExpand(idx)}
                      className="flex items-center justify-between p-3.5 cursor-pointer select-none group"
                    >
                      <div className="flex items-center gap-3 truncate min-w-0">
                        <div
                          className={`p-1.5 rounded shrink-0 transition-colors ${
                            isExpanded
                              ? 'bg-cyan-500/10 border border-cyan-500/20 text-cyan-400'
                              : 'bg-dark-900 border border-dark-800 text-dark-400 group-hover:text-dark-300'
                          }`}
                        >
                          <FileCode className="w-4 h-4" />
                        </div>
                        <div className="truncate min-w-0">
                          <p className="text-xs font-semibold text-dark-200 truncate font-mono">
                            {chunk.path}
                          </p>
                          <p className="text-[10px] text-dark-500 font-mono mt-0.5">
                            L{chunk.start_line}–L{chunk.end_line} · {chunk.end_line - chunk.start_line + 1} lines
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div
                          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${scoreColor}`}
                        >
                          <Tag className="w-3 h-3" />
                          <span>{scoreStr}</span>
                        </div>

                        <button
                          onClick={(e) => handleCopy(chunk.content, chunkId, e)}
                          className="text-dark-500 hover:text-dark-300 p-1.5 rounded hover:bg-dark-800 cursor-pointer transition-colors"
                          title="Copy snippet code"
                        >
                          {copiedId === chunkId ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>

                        <ChevronRight
                          className={`w-4 h-4 text-dark-500 transition-transform duration-200 ${
                            isExpanded ? 'rotate-90' : ''
                          }`}
                        />
                      </div>
                    </div>

                    {/* Code preview */}
                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: 'auto' }}
                          exit={{ height: 0 }}
                          transition={{ duration: 0.25, ease: 'easeInOut' }}
                        >
                          <div className="border-t border-dark-850/50 bg-dark-950 p-4 font-mono text-xs text-dark-300 overflow-x-auto leading-relaxed max-h-[400px] overflow-y-auto">
                            <pre className="relative">
                              <code className="block select-text">
                                {chunk.content.split('\n').map((line, lineIdx) => {
                                  const currentLineNum = chunk.start_line + lineIdx;
                                  return (
                                    <div
                                      key={lineIdx}
                                      className="flex hover:bg-dark-900/55 px-1 rounded-sm"
                                    >
                                      <span className="text-dark-600 select-none text-right pr-4 w-12 shrink-0 border-r border-dark-850/60 mr-4">
                                        {currentLineNum}
                                      </span>
                                      <span className="text-dark-300 break-all whitespace-pre">
                                        {line || ' '}
                                      </span>
                                    </div>
                                  );
                                })}
                              </code>
                            </pre>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}

              {/* Sentinel element for infinite scroll */}
              {hasMore && (
                <div ref={sentinelRef} className="flex items-center justify-center py-6">
                  {isLoadingMore ? (
                    <div className="flex items-center gap-2 text-dark-500 font-mono text-xs">
                      <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                      <span>Loading more chunks...</span>
                    </div>
                  ) : (
                    <button
                      onClick={() => setVisibleCount((prev) => Math.min(prev + PAGE_SIZE, filteredChunks.length))}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border border-dark-800 bg-dark-900 text-dark-400 hover:text-dark-200 hover:border-dark-700 font-mono text-xs cursor-pointer transition-all"
                    >
                      <ChevronDown className="w-3.5 h-3.5" />
                      <span>Load more ({filteredChunks.length - visibleCount} remaining)</span>
                    </button>
                  )}
                </div>
              )}

              {/* Loaded-all footer */}
              {!hasMore && displayedChunks.length > 0 && displayedChunks.length > PAGE_SIZE && (
                <p className="text-center text-[10px] text-dark-600 font-mono py-3">
                  All {filteredChunks.length} chunks loaded
                </p>
              )}
            </div>

            {/* Bottom bar */}
            <div className="px-6 py-3 border-t border-dark-800 bg-dark-900/80 backdrop-blur flex items-center justify-between shrink-0">
              <p className="text-[10px] text-dark-500 font-mono">
                Showing {displayedChunks.length} of {filteredChunks.length} chunks
              </p>
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg border border-dark-800 bg-dark-900 text-dark-300 hover:text-dark-100 hover:border-dark-700 font-mono text-xs cursor-pointer transition-all"
              >
                Close
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
