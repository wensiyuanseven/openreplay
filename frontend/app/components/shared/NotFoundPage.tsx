import React from 'react';

function NotFoundPage({ logIn }: { logIn: boolean }) {
  return (
    <div
      className="inset-0 flex items-center justify-center absolute"
      style={{
        height: 'calc(100vh - 50px)',
        // zIndex: '999',
      }}
    >
      {logIn ? (
        <div>please check your auth method for iframe</div>
      ) : (
        <div className="flex flex-col items-center">
          <div className="text-2xl -mt-8">Session not found.</div>
          <div className="text-sm">Please check your data retention policy.</div>
          <div style={{ opacity: 0 }}>{window.location.href}</div>
        </div>
      )}
    </div>
  );
}

export default NotFoundPage;