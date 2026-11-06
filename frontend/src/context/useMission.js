import { useContext } from 'react';
import { MissionContext } from './MissionContextInstance';

export function useMission() {
  const context = useContext(MissionContext);
  if (!context) {
    throw new Error('useMission must be used within a MissionProvider');
  }
  return context;
}
