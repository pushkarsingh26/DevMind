import { motion } from 'framer-motion';

interface FollowUpSuggestionsProps {
  suggestions: string[];
  onClick: (suggestion: string) => void;
}

export function FollowUpSuggestions({ suggestions, onClick }: FollowUpSuggestionsProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="follow-up-suggestions">
      <span className="follow-up-label">Suggested follow-ups:</span>
      <div className="follow-up-list">
        {suggestions.map((q, idx) => (
          <motion.button
            key={idx}
            className="follow-up-pill"
            onClick={() => onClick(q)}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05, duration: 0.2 }}
          >
            {q}
            <span className="follow-up-arrow">→</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
