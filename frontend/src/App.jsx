import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MissionProvider } from './context/MissionContext';
import Navbar from './components/Navbar';
import ResultBadge from './components/ResultBadge';
import UploadPage from './pages/UploadPage';
import DetectionsPage from './pages/DetectionsPage';
import HazardMapPage from './pages/HazardMapPage';

/**
 * LunaSafe AI - Main Application Router & Shell
 */
export default function App() {
  return (
    <MissionProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
          {/* Main Top Navigation */}
          <Navbar />

          {/* Primary View Area */}
          <main className="flex-1 w-full pb-12">
            <Routes>
              {/* Screen 1: Orbital Satellite Image Ingestion & Setup */}
              <Route path="/" element={<UploadPage />} />
              <Route path="/upload" element={<UploadPage />} />

              {/* Screen 2: Boulder Obstacle Detection Viewer & Threshold Filter */}
              <Route path="/detections" element={<DetectionsPage />} />

              {/* Screen 3: Landing Hazard Heatmap & Region Explanation */}
              <Route path="/hazard-map" element={<HazardMapPage />} />

              {/* Fallback to Upload Page */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Mission Control Footer */}
          <footer className="border-t border-slate-900 bg-slate-950/80 text-xs text-slate-400 py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-300">LunaSafe AI</span>
                <span>•</span>
                <span>Autonomous Lunar Landing Site Safety Assessment</span>
              </div>

              <div className="flex items-center gap-4 text-slate-400">
                <ResultBadge />
              </div>
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </MissionProvider>
  );
}
