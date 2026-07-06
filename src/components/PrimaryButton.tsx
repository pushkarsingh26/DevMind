import React from 'react';

interface PrimaryButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
}

export const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  onClick,
  disabled = false,
  loading = false,
  children,
}) => {
  const isButtonDisabled = disabled || loading;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isButtonDisabled}
      className={`w-full py-3 px-4 font-semibold text-sm tracking-wide rounded-md border text-center font-mono uppercase cursor-pointer
        ${
          isButtonDisabled
            ? 'bg-dark-800 border-dark-700 text-dark-500 cursor-not-allowed'
            : 'bg-brand-600 border-brand-500 text-white hover:bg-brand-500 hover:border-brand-400 active:bg-brand-700'
        }
      `}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          {/* Static text, no animation */}
          <span>[ PROCESSING... ]</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
};
