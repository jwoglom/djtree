import React, { useEffect } from 'react';

interface AdminModalProps {
  url: string;
  onClose: () => void;
}

export const AdminModal: React.FC<AdminModalProps> = ({ url, onClose }) => {
  useEffect(() => {
    // Close modal on Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Add ?_popup=1 to the URL for Django's popup mode
  const popupUrl = url.includes('?') ? `${url}&_popup=1` : `${url}?_popup=1`;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#fff',
          borderRadius: '8px',
          width: '90%',
          height: '90%',
          maxWidth: '1400px',
          maxHeight: '900px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '15px 20px',
            borderBottom: '1px solid #ddd',
            backgroundColor: '#f8f8f8',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '18px', color: '#333' }}>
            Django Admin
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '0',
              width: '30px',
              height: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#666',
            }}
            title="Close (Esc)"
          >
            ×
          </button>
        </div>

        {/* Iframe */}
        <iframe
          src={popupUrl}
          sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
          style={{
            flex: 1,
            border: 'none',
            width: '100%',
            height: '100%',
          }}
          title="Django Admin"
        />
      </div>
    </div>
  );
};
