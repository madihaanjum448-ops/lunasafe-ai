import React, { useState } from 'react';
import { useMission } from '../context/useMission';

export default function WarningsBanner() {
  const { warnings } = useMission();
  const [collapsed, setCollapsed] = useState(false);

  if (!warnings || warnings.length === 0) {
    return null;
  }

  return (
    <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-3.5 backdrop-blur-sm text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-amber-400 flex-shrink-0 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="font-semibold text-amber-300">
            Descent Warnings ({warnings.length})
          </span>
        </div>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-amber-400 hover:text-amber-200 text-xs font-mono"
        >
          {collapsed ? 'Show' : 'Hide'}
        </button>
      </div>

      {!collapsed && (
        <ul className="mt-2.5 space-y-1 pl-6 list-disc text-amber-200/90 leading-relaxed">
          {warnings.map((warning, index) => (
            <li key={index}>{warning}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
