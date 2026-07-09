import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CitationRef } from '../types';

interface CitationCardProps {
  citation: CitationRef;
  index: number;
}

function scoreColor(score?: number): string {
  if (!score) return 'citation-score--neutral';
  if (score >= 0.85) return 'citation-score--high';
  if (score >= 0.65) return 'citation-score--medium';
  return 'citation-score--low';
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const filename = citation.path.split('/').pop() ?? citation.path;
  const scoreLabel = citation.score != null ? `${(citation.score * 100).toFixed(0)}%` : null;

  return (
    <motion.div
      className="citation-card"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.2 }}
    >
      <button
        className="citation-header"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="citation-header-left">
          <span className="citation-icon">📄</span>
          <span className="citation-filename" title={citation.path}>
            {filename}
          </span>
          <span className="citation-lines">
            L{citation.start_line}–{citation.end_line}
          </span>
        </div>
        <div className="citation-header-right">
          {scoreLabel && (
            <span className={`citation-score ${scoreColor(citation.score)}`}>
              {scoreLabel}
            </span>
          )}
          <span className={`citation-chevron ${expanded ? 'citation-chevron--open' : ''}`}>
            ▾
          </span>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            className="citation-path-full"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <code className="citation-path-text">{citation.path}</code>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
