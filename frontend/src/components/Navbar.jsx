import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useMission } from '../context/useMission';

export default function Navbar() {
  const { imageMeta } = useMission();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinkClass = ({ isActive }) =>
    `px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-2 ${
      isActive
        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
    }`;

  return (
    <header className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <div className="flex items-center gap-3">
            <NavLink to="/" className="flex items-center gap-3 group">
              <div className="relative w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-violet-500 p-0.5 flex items-center justify-center shadow-lg shadow-cyan-950/50 group-hover:scale-105 transition-transform">
                <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                  {/* Moon icon with safety crosshair */}
                  <svg className="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 3a9 9 0 0 0 9 9 9 9 0 1 1-9-9Z" fill="currentColor" fillOpacity="0.2" />
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeDasharray="2 2" />
                  </svg>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold tracking-tight text-white group-hover:text-cyan-300 transition-colors">
                    LunaSafe <span className="text-cyan-400">AI</span>
                  </span>
                  <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    Mock Data
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-none hidden sm:block">
                  Lunar Landing-Site Safety Assessment
                </p>
              </div>
            </NavLink>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-2">
            <NavLink to="/" className={navLinkClass} end>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Upload & Setup
            </NavLink>

            <NavLink to="/detections" className={navLinkClass}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m-3-3h6" />
              </svg>
              Boulder Detections
            </NavLink>

            <NavLink to="/hazard-map" className={navLinkClass}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              Hazard Map
            </NavLink>
          </nav>

          {/* Telemetry info pill */}
          <div className="hidden lg:flex items-center gap-3 text-xs">
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-slate-400">Target:</span>
              <span className="text-slate-200 font-mono font-medium">{imageMeta.id}</span>
              <span className="text-slate-500 font-mono">({imageMeta.width}×{imageMeta.height})</span>
              {imageMeta.isSample && (
                <span className="text-[10px] text-amber-400 font-sans font-medium">(Mock value)</span>
              )}
            </div>

            <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
              <span className="text-slate-400">Scale:</span>
              {imageMeta.pixelScaleM !== null ? (
                <div className="flex items-center gap-1.5">
                  <span className="text-cyan-300 font-mono font-medium">
                    {imageMeta.pixelScaleM} m/px
                  </span>
                  {imageMeta.isSample && (
                    <span className="text-[10px] text-amber-400 font-sans font-medium">(Mock value)</span>
                  )}
                </div>
              ) : (
                <span className="text-amber-400 font-mono">Unavailable</span>
              )}
            </div>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none"
              aria-label="Toggle Navigation Menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950 px-4 pt-2 pb-4 space-y-2">
          <NavLink
            to="/"
            end
            onClick={() => setMobileMenuOpen(false)}
            className={navLinkClass}
          >
            Upload & Setup
          </NavLink>
          <NavLink
            to="/detections"
            onClick={() => setMobileMenuOpen(false)}
            className={navLinkClass}
          >
            Boulder Detections
          </NavLink>
          <NavLink
            to="/hazard-map"
            onClick={() => setMobileMenuOpen(false)}
            className={navLinkClass}
          >
            Hazard Map
          </NavLink>
          <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 px-2">
            <span>
              Scale: {imageMeta.pixelScaleM ? `${imageMeta.pixelScaleM} m/px ${imageMeta.isSample ? '(Mock value)' : ''}` : 'Unavailable'}
            </span>
            <span className="text-amber-400 font-medium">Mock Data</span>
          </div>
        </div>
      )}
    </header>
  );
}
