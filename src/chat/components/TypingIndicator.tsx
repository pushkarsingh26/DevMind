import { motion } from 'framer-motion';

interface TypingIndicatorProps {
  model?: string;
  provider?: string;
}

export function TypingIndicator({ model, provider }: TypingIndicatorProps) {
  const label = model
    ? `${model}${provider ? ` (${provider})` : ''} is thinking`
    : 'Thinking';

  return (
    <motion.div
      className="typing-indicator"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.2 }}
    >
      <div className="typing-dots">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="typing-dot"
            animate={{ y: [0, -6, 0] }}
            transition={{
              duration: 0.8,
              repeat: Infinity,
              delay: i * 0.18,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      <span className="typing-label">{label}…</span>
    </motion.div>
  );
}
