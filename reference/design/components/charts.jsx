// Canvas-based chart component with zoom, pan, fullscreen, tooltip, reset
const { useRef, useEffect, useState, useCallback, useMemo } = React;

// ─── Fullscreen Modal ────────────────────────────────────────────────
const ChartModal = ({ open, onClose, children }) => {
  if (!open) return null;
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);
  return ReactDOM.createPortal(
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div style={{
        background: 'white', borderRadius: 14, width: '92vw', maxWidth: 1400,
        maxHeight: '90vh', overflow: 'hidden', boxShadow: '0 24px 64px rgba(0,0,0,0.2)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '10px 14px 0' }}>
          <button onClick={onClose} style={{
            width: 32, height: 32, borderRadius: 8, border: '1px solid var(--border)',
            background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Icon d={ICONS.x} size={16} color="var(--text-3)" /></button>
        </div>
        <div style={{ padding: '8px 24px 24px' }}>{children}</div>
      </div>
    </div>,
    document.body
  );
};

// ─── Chart Toolbar ───────────────────────────────────────────────────
const ChartToolbar = ({ onZoomIn, onZoomOut, onReset, onPanLeft, onPanRight, onFullscreen, zoomLevel }) => {
  const btnStyle = {
    width: 30, height: 26, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'white', border: '1px solid var(--border)', cursor: 'pointer',
    color: 'var(--text-3)', transition: 'all 0.12s', fontSize: 13,
  };
  return (
    <div style={{ display: 'flex', gap: 0, borderRadius: 7, overflow: 'hidden', border: '1px solid var(--border)' }}>
      <button onClick={onPanLeft} style={{ ...btnStyle, borderRight: 'none', borderRadius: '7px 0 0 7px', border: 'none' }} title="Pan left">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
      <button onClick={onZoomIn} style={{ ...btnStyle, border: 'none', borderLeft: '1px solid var(--border)' }} title="Zoom in">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
      </button>
      <span style={{ padding: '0 8px', fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-3)',
        display: 'flex', alignItems: 'center', background: '#f8f9fb', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        {Math.round(zoomLevel * 100)}%
      </span>
      <button onClick={onZoomOut} style={{ ...btnStyle, border: 'none', borderRight: '1px solid var(--border)' }} title="Zoom out">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14"/></svg>
      </button>
      <button onClick={onPanRight} style={{ ...btnStyle, border: 'none', borderLeft: '1px solid var(--border)' }} title="Pan right">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
      </button>
      <div style={{ width: 1, background: 'var(--border)' }} />
      <button onClick={onReset} style={{ ...btnStyle, border: 'none', padding: '0 8px', width: 'auto', fontSize: 10, fontFamily: 'var(--font)', fontWeight: 500 }} title="Reset zoom">
        Reset
      </button>
      <div style={{ width: 1, background: 'var(--border)' }} />
      <button onClick={onFullscreen} style={{ ...btnStyle, border: 'none', borderRadius: '0 7px 7px 0' }} title="Fullscreen">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
        </svg>
      </button>
    </div>
  );
};

// ─── Main Chart ──────────────────────────────────────────────────────
const ChartCanvas = ({
  series = [],
  xData,
  width = 400,
  height = 200,
  xLabel = '',
  yLabel = '',
  showGrid = true,
  showLegend = true,
  interactive = true,
  showToolbar = true,
}) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ w: width, h: height });
  const [hover, setHover] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [fullscreen, setFullscreen] = useState(false);

  // Zoom/pan state
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState(0); // 0-1 normalized
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [selectionBox, setSelectionBox] = useState(null); // {start, end} normalized for box zoom

  const zoomIn = () => setZoom(z => Math.min(z * 1.5, 20));
  const zoomOut = () => { setZoom(z => { const nz = Math.max(z / 1.5, 1); if (nz === 1) setPanOffset(0); return nz; }); };
  const resetView = () => { setZoom(1); setPanOffset(0); };
  const panLeft = () => setPanOffset(p => Math.max(p - 0.1 / zoom, 0));
  const panRight = () => setPanOffset(p => Math.min(p + 0.1 / zoom, 1 - 1 / zoom));

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(entries => {
      const { width: w } = entries[0].contentRect;
      setDims({ w, h: height });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [height]);

  // Compute visible range based on zoom/pan
  const visibleRange = useMemo(() => {
    const windowSize = 1 / zoom;
    const start = Math.max(0, Math.min(panOffset, 1 - windowSize));
    return { start, end: start + windowSize };
  }, [zoom, panOffset]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !series.length) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const { w, h } = dims;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const pad = { l: 56, r: 16, t: 12, b: 32 };
    const cw = w - pad.l - pad.r;
    const ch = h - pad.t - pad.b;

    const x = xData || series[0].data.map((_, i) => i);
    const totalLen = x.length;
    const startIdx = Math.floor(visibleRange.start * totalLen);
    const endIdx = Math.min(Math.ceil(visibleRange.end * totalLen), totalLen - 1);
    const visX = x.slice(startIdx, endIdx + 1);
    const visSeries = series.map(s => ({ ...s, data: s.data.slice(startIdx, endIdx + 1) }));

    // Compute Y range for visible data
    let yMin = Infinity, yMax = -Infinity;
    visSeries.forEach(s => {
      s.data.forEach(v => { if (v < yMin) yMin = v; if (v > yMax) yMax = v; });
    });
    const yRange = yMax - yMin || 1;
    const yPad = yRange * 0.08;
    yMin -= yPad; yMax += yPad;
    const finalRange = yMax - yMin;

    const xMin = visX[0], xMax = visX[visX.length - 1];
    const xRange = xMax - xMin || 1;

    const toX = v => pad.l + ((v - xMin) / xRange) * cw;
    const toY = v => pad.t + ch - ((v - yMin) / finalRange) * ch;

    // Grid
    if (showGrid) {
      ctx.strokeStyle = 'rgba(148,163,184,0.1)';
      ctx.lineWidth = 0.5;
      for (let i = 0; i <= 8; i++) {
        const y = pad.t + (ch / 8) * i;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + cw, y); ctx.stroke();
      }
      for (let i = 0; i <= 10; i++) {
        const xp = pad.l + (cw / 10) * i;
        ctx.beginPath(); ctx.moveTo(xp, pad.t); ctx.lineTo(xp, pad.t + ch); ctx.stroke();
      }
    }

    // Axes
    ctx.strokeStyle = '#dfe2e8';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + ch); ctx.lineTo(pad.l + cw, pad.t + ch);
    ctx.stroke();

    // Y ticks
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const val = yMin + (finalRange / 4) * (4 - i);
      const y = pad.t + (ch / 4) * i;
      const fmt = Math.abs(val) >= 100 ? val.toFixed(0) : Math.abs(val) >= 1 ? val.toFixed(1) : val.toFixed(3);
      ctx.fillText(fmt, pad.l - 6, y + 3);
    }

    // X ticks
    ctx.textAlign = 'center';
    for (let i = 0; i <= 5; i++) {
      const val = xMin + (xRange / 5) * i;
      const xp = toX(val);
      const precision = xRange < 0.01 ? 5 : xRange < 1 ? 4 : xRange < 10 ? 3 : 1;
      ctx.fillText(val.toFixed(precision), xp, pad.t + ch + 18);
    }

    // Axis labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px DM Sans, sans-serif';
    if (xLabel) { ctx.textAlign = 'center'; ctx.fillText(xLabel, pad.l + cw / 2, h - 2); }
    if (yLabel) {
      ctx.save(); ctx.translate(12, pad.t + ch / 2); ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center'; ctx.fillText(yLabel, 0, 0); ctx.restore();
    }

    // Series
    visSeries.forEach(s => {
      if (s.filled) {
        ctx.beginPath();
        ctx.moveTo(toX(visX[0]), pad.t + ch);
        s.data.forEach((v, i) => ctx.lineTo(toX(visX[i]), toY(v)));
        ctx.lineTo(toX(visX[visX.length - 1]), pad.t + ch);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ch);
        grad.addColorStop(0, s.color + '25');
        grad.addColorStop(1, s.color + '03');
        ctx.fillStyle = grad;
        ctx.fill();
      }
      ctx.beginPath();
      s.data.forEach((v, i) => i === 0 ? ctx.moveTo(toX(visX[i]), toY(v)) : ctx.lineTo(toX(visX[i]), toY(v)));
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.dashed ? 1.2 : 1.6;
      ctx.lineJoin = 'round';
      if (s.dashed) ctx.setLineDash([4, 3]);
      else ctx.setLineDash([]);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Hover crosshair + tooltip data
    if (hover !== null && interactive) {
      const idx = Math.min(Math.round(hover * (visX.length - 1)), visX.length - 1);
      const xp = toX(visX[idx]);

      // Crosshair
      ctx.strokeStyle = 'rgba(148,163,184,0.2)';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(xp, pad.t); ctx.lineTo(xp, pad.t + ch); ctx.stroke();
      ctx.setLineDash([]);

      // Horizontal guide for first series
      const yp0 = toY(visSeries[0].data[idx]);
      ctx.strokeStyle = 'rgba(148,163,184,0.12)';
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(pad.l, yp0); ctx.lineTo(pad.l + cw, yp0); ctx.stroke();
      ctx.setLineDash([]);

      // Data points
      visSeries.forEach(s => {
        const yp = toY(s.data[idx]);
        ctx.beginPath(); ctx.arc(xp, yp, 4, 0, Math.PI * 2);
        ctx.fillStyle = s.color; ctx.fill();
        ctx.strokeStyle = 'white'; ctx.lineWidth = 2; ctx.stroke();
      });

      // Set tooltip state
      const ttData = visSeries.map(s => ({ label: s.label, value: s.data[idx], color: s.color }));
      const ttX = (xp / w) * 100;
      setTooltip({ x: xp, xVal: visX[idx], data: ttData, left: ttX < 70 });
    } else {
      setTooltip(null);
    }

    // Selection box for box-zoom
    if (selectionBox) {
      const sx = pad.l + selectionBox.start * cw;
      const ex = pad.l + selectionBox.end * cw;
      ctx.fillStyle = 'rgba(16,185,129,0.08)';
      ctx.fillRect(sx, pad.t, ex - sx, ch);
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 2]);
      ctx.strokeRect(sx, pad.t, ex - sx, ch);
      ctx.setLineDash([]);
    }
  }, [series, xData, dims, hover, showGrid, visibleRange, selectionBox]);

  const padLeft = 56, padRight = 16;
  const getNorm = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const cw = rect.width - padLeft - padRight;
    return Math.max(0, Math.min(1, (px - padLeft) / cw));
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (!interactive || e.button !== 0) return;
    const norm = getNorm(e);
    setIsDragging(true);
    setDragStart(norm);
    setSelectionBox(null);
  }, [interactive, getNorm]);

  const handleMouseMove = useCallback((e) => {
    if (!interactive) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const cw = rect.width - padLeft - padRight;
    const norm = Math.max(0, Math.min(1, (px - padLeft) / cw));

    if (isDragging && dragStart !== null) {
      const dist = Math.abs(norm - dragStart);
      if (dist > 0.02) {
        setSelectionBox({ start: Math.min(dragStart, norm), end: Math.max(dragStart, norm) });
      }
      setHover(norm);
    } else {
      if (px >= padLeft && px <= rect.width - padRight) setHover(norm);
      else setHover(null);
    }
  }, [interactive, isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    if (selectionBox && (selectionBox.end - selectionBox.start) > 0.02) {
      // Box zoom: map selection to new zoom/pan
      const windowSize = visibleRange.end - visibleRange.start;
      const newStart = visibleRange.start + selectionBox.start * windowSize;
      const newEnd = visibleRange.start + selectionBox.end * windowSize;
      const newWindow = newEnd - newStart;
      setZoom(1 / newWindow);
      setPanOffset(newStart);
    }
    setIsDragging(false);
    setDragStart(null);
    setSelectionBox(null);
  }, [selectionBox, visibleRange]);

  const handleWheel = useCallback((e) => {
    if (!interactive) return;
    e.preventDefault();
    const norm = getNorm(e);
    if (e.deltaY < 0) {
      // Zoom in toward cursor
      setZoom(z => {
        const nz = Math.min(z * 1.3, 20);
        const windowBefore = 1 / z;
        const windowAfter = 1 / nz;
        const cursorInData = visibleRange.start + norm * windowBefore;
        const newPan = cursorInData - norm * windowAfter;
        setPanOffset(Math.max(0, Math.min(newPan, 1 - windowAfter)));
        return nz;
      });
    } else {
      setZoom(z => {
        const nz = Math.max(z / 1.3, 1);
        if (nz === 1) { setPanOffset(0); return 1; }
        const windowBefore = 1 / z;
        const windowAfter = 1 / nz;
        const cursorInData = visibleRange.start + norm * windowBefore;
        const newPan = cursorInData - norm * windowAfter;
        setPanOffset(Math.max(0, Math.min(newPan, 1 - windowAfter)));
        return nz;
      });
    }
  }, [interactive, getNorm, visibleRange]);

  // Double click to reset
  const handleDblClick = useCallback(() => { resetView(); }, []);

  const chartContent = (chartHeight) => (
    <div ref={containerRef} style={{ width: '100%', position: 'relative' }}
      onMouseDown={handleMouseDown} onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp} onMouseLeave={() => { setHover(null); setIsDragging(false); setSelectionBox(null); }}
      onWheel={handleWheel} onDoubleClick={handleDblClick}>
      
      {/* Toolbar */}
      {showToolbar && interactive && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6, gap: 6 }}>
          <ChartToolbar
            onZoomIn={zoomIn} onZoomOut={zoomOut} onReset={resetView}
            onPanLeft={panLeft} onPanRight={panRight}
            onFullscreen={() => setFullscreen(true)} zoomLevel={zoom}
          />
        </div>
      )}

      <canvas ref={canvasRef} style={{
        width: dims.w, height: chartHeight || dims.h, display: 'block',
        cursor: isDragging ? 'col-resize' : interactive ? 'crosshair' : 'default',
      }} />

      {/* Tooltip */}
      {tooltip && interactive && (
        <div style={{
          position: 'absolute', top: 20,
          left: tooltip.left ? tooltip.x + 12 : undefined,
          right: tooltip.left ? undefined : (dims.w - tooltip.x + 12),
          background: 'var(--navy)', borderRadius: 9, padding: '10px 14px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.25)', pointerEvents: 'none',
          zIndex: 10, minWidth: 140,
        }}>
          <div style={{ fontSize: 10, color: '#64748b', fontFamily: 'var(--mono)', marginBottom: 6 }}>
            {xLabel || 'x'}: {typeof tooltip.xVal === 'number' ? tooltip.xVal.toFixed(5) : tooltip.xVal}
          </div>
          {tooltip.data.map(d => (
            <div key={d.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: d.color, flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: '#94a3b8', flex: 1 }}>{d.label}</span>
              <span style={{ fontSize: 12, color: 'white', fontFamily: 'var(--mono)', fontWeight: 600 }}>
                {typeof d.value === 'number' ? (Math.abs(d.value) >= 100 ? d.value.toFixed(1) : d.value.toFixed(4)) : d.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Zoom indicator */}
      {zoom > 1 && (
        <div style={{
          position: 'absolute', bottom: 36, left: 56, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {/* Mini range bar */}
          <div style={{ width: 80, height: 4, background: '#e2e6ee', borderRadius: 2, position: 'relative' }}>
            <div style={{
              position: 'absolute', top: 0, left: `${visibleRange.start * 100}%`,
              width: `${(visibleRange.end - visibleRange.start) * 100}%`,
              height: '100%', background: '#10b981', borderRadius: 2,
            }} />
          </div>
          <span style={{ fontSize: 9, color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>
            {Math.round(visibleRange.start * 100)}–{Math.round(visibleRange.end * 100)}%
          </span>
        </div>
      )}

      {showLegend && series.length > 1 && (
        <div style={{ display: 'flex', gap: 14, padding: '6px 0 0 56px' }}>
          {series.map(s => (
            <span key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#64748b' }}>
              <span style={{ width: 14, height: 2, background: s.color, borderRadius: 1, display: 'inline-block', opacity: s.dashed ? 0.6 : 1 }} />
              {s.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <>
      {chartContent(dims.h)}
      <ChartModal open={fullscreen} onClose={() => setFullscreen(false)}>
        <ChartCanvas
          series={series} xData={xData} height={520}
          xLabel={xLabel} yLabel={yLabel} showGrid={showGrid}
          showLegend={showLegend} interactive={true} showToolbar={true}
        />
      </ChartModal>
    </>
  );
};

// Sparkline (tiny inline chart)
const Spark = ({ data, width = 100, height = 28, color = '#10b981' }) => {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current; if (!c || !data.length) return;
    const ctx = c.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    c.width = width * dpr; c.height = height * dpr;
    ctx.scale(dpr, dpr); ctx.clearRect(0, 0, width, height);
    const min = Math.min(...data), max = Math.max(...data), range = max - min || 1;
    const p = 3;
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = p + (i / (data.length - 1)) * (width - p * 2);
      const y = p + (height - p * 2) - ((v - min) / range) * (height - p * 2);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.lineJoin = 'round'; ctx.stroke();
    const lastX = p + (width - p * 2);
    ctx.lineTo(lastX, height - p); ctx.lineTo(p, height - p); ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, color + '20'); grad.addColorStop(1, color + '02');
    ctx.fillStyle = grad; ctx.fill();
  }, [data, width, height, color]);
  return <canvas ref={ref} style={{ width, height, display: 'block' }} />;
};

Object.assign(window, { ChartCanvas, ChartModal, ChartToolbar, Spark });
