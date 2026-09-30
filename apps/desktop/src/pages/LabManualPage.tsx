import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { Experiment } from '../types';

interface LabManualPageProps {
  experiments?: Experiment[];
}

export const LabManualPage: React.FC<LabManualPageProps> = ({ experiments = [] }) => {
  const [page, setPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [navVersion, setNavVersion] = useState<number>(0);

  const totalPages = experiments.reduce(
    (maxPage, exp) => Math.max(maxPage, exp.page_end || 0),
    35
  );

  // Relative path when served from the local core server; fallback to localhost API when in Vite/Tauri dev mode
  const basePdfUrl =
    typeof window !== 'undefined' &&
    window.location.protocol.startsWith('http') &&
    window.location.port === '8000'
      ? './api/manual/pdf'
      : 'http://127.0.0.1:8000/api/manual/pdf';

  const applyPdfView = (nextPage: number, nextZoom: number) => {
    const clampedPage = Math.max(1, Math.min(totalPages, nextPage));
    const clampedZoom = Math.max(50, Math.min(250, nextZoom));
    setPage(clampedPage);
    setZoom(clampedZoom);
    setNavVersion((v) => v + 1);
  };

  const viewerSrc = `${basePdfUrl}?v=${navVersion}#page=${page}&zoom=${zoom}`;

  return (
    <div className="flex flex-col h-full w-full bg-zinc-950 text-zinc-100 overflow-hidden select-none">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-zinc-800 bg-zinc-950 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center space-x-2.5">
          <span className="text-base" role="img" aria-label="Lab Manual">
            📘
          </span>
          <h1 className="text-sm md:text-base font-semibold text-zinc-100 tracking-tight">
            Electrical &amp; Electronics Engineering — Lab Manual
          </h1>
        </div>

        {/* Built-in Viewer Controls (Page Navigation & Zoom) */}
        <div className="flex items-center space-x-3 text-xs">
          {experiments.length > 0 && (
            <select
              aria-label="Jump to Experiment"
              value=""
              onChange={(e) => {
                const targetPage = Number(e.target.value);
                if (targetPage > 0) {
                  applyPdfView(targetPage, zoom);
                }
              }}
              className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 focus:outline-none focus:border-zinc-700"
            >
              <option value="">Jump to Experiment...</option>
              {experiments.map((exp) => (
                <option key={exp.exp_number} value={exp.page_start}>
                  Exp {exp.exp_number}: {exp.title} (p. {exp.page_start})
                </option>
              ))}
            </select>
          )}

          {/* Page Navigation */}
          <div className="flex items-center space-x-1 bg-zinc-900 border border-zinc-800 rounded px-1.5 py-0.5">
            <button
              onClick={() => applyPdfView(page - 1, zoom)}
              disabled={page <= 1}
              title="Previous Page"
              className="p-1 text-zinc-400 hover:text-zinc-100 disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] text-zinc-300 px-1.5">
              Page {page} / {totalPages}
            </span>
            <button
              onClick={() => applyPdfView(page + 1, zoom)}
              disabled={page >= totalPages}
              title="Next Page"
              className="p-1 text-zinc-400 hover:text-zinc-100 disabled:opacity-40 transition"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center space-x-1 bg-zinc-900 border border-zinc-800 rounded px-1.5 py-0.5">
            <button
              onClick={() => applyPdfView(page, zoom - 25)}
              disabled={zoom <= 50}
              title="Zoom Out"
              className="p-1 text-zinc-400 hover:text-zinc-100 disabled:opacity-40 transition"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] text-emerald-400 px-1.5 min-w-[44px] text-center">
              {zoom}%
            </span>
            <button
              onClick={() => applyPdfView(page, zoom + 25)}
              disabled={zoom >= 250}
              title="Zoom In"
              className="p-1 text-zinc-400 hover:text-zinc-100 disabled:opacity-40 transition"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => applyPdfView(page, 100)}
              title="Reset Zoom"
              className="p-1 text-zinc-400 hover:text-zinc-100 transition border-l border-zinc-800 pl-1.5"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Built-in PDF Viewer */}
      <div className="flex-1 w-full bg-zinc-900/60 p-3 overflow-hidden">
        <div className="w-full h-full rounded-lg border border-zinc-800 overflow-hidden bg-zinc-900 shadow-inner">
          <iframe
            key={navVersion}
            src={viewerSrc}
            title="Electrical & Electronics Engineering — Lab Manual"
            className="w-full h-full border-0"
          />
        </div>
      </div>
    </div>
  );
};
