import React from 'react';
import { Modal } from './Modal';
import { Button } from './Button';

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description: string;
  onConfirm?: () => void;
  confirmText?: string;
  cancelText?: string;
  type?: 'info' | 'danger' | 'warning';
  loading?: boolean;
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  onConfirm,
  confirmText = 'CONFIRM',
  cancelText = 'CANCEL',
  type = 'info',
  loading = false,
}) => {
  const getConfirmVariant = () => {
    if (type === 'danger') return 'danger';
    return 'primary';
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="space-y-5">
        <p className="text-xs text-dark-400 font-sans leading-relaxed">
          {description}
        </p>

        <div className="flex justify-end gap-2.5 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelText}
          </Button>
          {onConfirm && (
            <Button
              variant={getConfirmVariant()}
              onClick={() => {
                onConfirm();
                onClose();
              }}
              loading={loading}
            >
              {confirmText}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};
