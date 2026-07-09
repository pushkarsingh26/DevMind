import React, { useState } from 'react';
import { Download, Printer, ChevronDown } from 'lucide-react';
import { useChatContext } from '../ChatContext';

export const ChatExportMenu: React.FC = () => {
  const { activeConversation, messages, repositories, selectedRepositoryId } = useChatContext();
  const [isOpen, setIsOpen] = useState(false);

  if (!activeConversation || messages.length === 0) {
    return null;
  }

  const handleExportMarkdown = () => {
    const repo = repositories.find((r) => r.id === selectedRepositoryId);
    let md = `# DevMind Grounded Chat Session\n\n`;
    md += `- **Session Title:** ${activeConversation.title || 'Untitled Session'}\n`;
    md += `- **Repository:** ${repo ? `${repo.owner}/${repo.name}` : 'Unknown'}\n`;
    md += `- **Date:** ${new Date(activeConversation.updated_at).toLocaleString()}\n\n`;
    md += `---\n\n`;

    messages.forEach((msg) => {
      const role = msg.role === 'user' ? 'USER' : 'DEVMIND AI';
      md += `## ${role}\n\n`;
      md += `${msg.content}\n\n`;

      if (msg.citations && msg.citations.length > 0) {
        md += `### Citations\n\n`;
        msg.citations.forEach((cit) => {
          const scoreStr = cit.score !== undefined ? `${(cit.score * 100).toFixed(0)}%` : 'N/A';
          md += `- \`${cit.path}\` (Lines L${cit.start_line}-L${cit.end_line}, Score: ${scoreStr})\n`;
        });
        md += `\n`;
      }

      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `devmind-chat-${activeConversation.id}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setIsOpen(false);
  };

  const handlePrintPDF = () => {
    setIsOpen(false);
    // Timeout gives dropdown time to close before print dialog opens
    setTimeout(() => {
      window.print();
    }, 150);
  };

  return (
    <div className="chat-export-container">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="chat-export-trigger-btn"
        title="Export options"
      >
        <Download className="w-3.5 h-3.5" />
        <span>EXPORT CHAT</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="chat-export-dropdown">
          <button onClick={handleExportMarkdown} className="chat-export-dropdown-item">
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export as Markdown (.md)</span>
          </button>
          <button onClick={handlePrintPDF} className="chat-export-dropdown-item">
            <Printer className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export/Print as PDF</span>
          </button>
        </div>
      )}
    </div>
  );
};
