// Shared UI components: KPI cards, sidebar, header, panels
const { useState, useRef, useEffect, Fragment } = React;

// ─── KPI Card ────────────────────────────────────────────────────────
const KpiCard = ({ label, value, unit, accent, sparkData, delta, icon }) => (
  <div style={{
    background: accent ? 'var(--navy)' : 'white',
    borderRadius: 10, border: accent ? 'none' : '1px solid var(--border)',
    padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 6,
    flex: 1, minWidth: 0,
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: accent ? '#10b981' : 'var(--text-3)',
        textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      {delta && <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
        background: delta > 0 ? '#dcfce7' : '#fee2e2', color: delta > 0 ? '#16a34a' : '#dc2626',
      }}>{delta > 0 ? '↑' : '↓'} {Math.abs(delta)}%</span>}
    </div>
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 28, fontWeight: 600,
        color: accent ? 'white' : 'var(--text)', letterSpacing: '-0.02em' }}>{value}</span>
      {unit && <span style={{ fontSize: 13, color: accent ? '#64748b' : 'var(--text-3)', fontWeight: 500 }}>{unit}</span>}
    </div>
    {sparkData && <div style={{ marginTop: 2 }}><Spark data={sparkData} width={120} height={24}
      color={accent ? '#10b981' : '#cbd5e1'} /></div>}
  </div>
);

// ─── Chart Panel wrapper ─────────────────────────────────────────────
const ChartPanelStyles = {
  container: {
    background: 'white', borderRadius: 10, border: '1px solid var(--border)',
    padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '14px 18px 0', gap: 8,
  },
  title: { fontSize: 13, fontWeight: 600, color: 'var(--text)' },
  body: { padding: '8px 12px 12px' },
};

const ChartPanel = ({ title, children, actions, style }) => (
  <div style={{ ...ChartPanelStyles.container, ...style }}>
    <div style={ChartPanelStyles.header}>
      <span style={ChartPanelStyles.title}>{title}</span>
      <div style={{ display: 'flex', gap: 4 }}>{actions}</div>
    </div>
    <div style={ChartPanelStyles.body}>{children}</div>
  </div>
);

// ─── Small button ────────────────────────────────────────────────────
const SmallBtn = ({ children, active, onClick, style }) => (
  <button onClick={onClick} style={{
    padding: '4px 10px', fontSize: 11, fontWeight: active ? 600 : 400,
    background: active ? 'var(--navy)' : 'transparent', color: active ? 'white' : 'var(--text-3)',
    border: active ? 'none' : '1px solid var(--border)', borderRadius: 6,
    cursor: 'pointer', fontFamily: 'var(--font)', transition: 'all 0.15s', ...style,
  }}>{children}</button>
);

// ─── Icon Button ─────────────────────────────────────────────────────
const IconBtn = ({ icon, size = 14, onClick, title }) => (
  <button onClick={onClick} title={title} style={{
    width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'none', border: '1px solid var(--border)', borderRadius: 6,
    cursor: 'pointer', color: 'var(--text-3)', transition: 'all 0.15s',
  }}><Icon d={icon} size={size} color="var(--text-3)" /></button>
);

// ─── Sidebar ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: 'dashboard', icon: ICONS.dashboard, label: 'Dashboard' },
  { id: 'import', icon: ICONS.upload, label: 'Import Data' },
  { id: 'standard', icon: ICONS.chart, label: 'Standard Analysis' },
  { id: 'upm', icon: ICONS.wave, label: 'UPM Analysis' },
  { id: 'cycles', icon: ICONS.cycle, label: 'Cycle Analysis' },
  { id: 'builder', icon: ICONS.layers, label: 'Chart Builder' },
  { id: 'report', icon: ICONS.report, label: 'Report Builder' },
  { id: 'data', icon: ICONS.table, label: 'Raw Data' },
  { id: 'settings', icon: ICONS.settings, label: 'Settings' },
];

const Sidebar = ({ active, onNav }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredItem, setHoveredItem] = useState(null);

  return (
    <div style={{
      width: collapsed ? 64 : 240, height: '100vh', background: 'var(--navy)',
      display: 'flex', flexDirection: 'column', transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)',
      flexShrink: 0, overflow: 'visible', position: 'relative', zIndex: 20,
    }}>
      {/* Logo */}
      <div onClick={() => setCollapsed(!collapsed)} style={{
        padding: collapsed ? '20px 15px' : '20px', display: 'flex', alignItems: 'center', gap: 12,
        justifyContent: collapsed ? 'center' : 'flex-start',
        borderBottom: '1px solid rgba(255,255,255,0.06)', minHeight: 68, cursor: 'pointer',
        transition: 'padding 0.25s ease',
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg, #10b981, #059669)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 13, color: 'white', flexShrink: 0,
          boxShadow: '0 2px 8px rgba(16,185,129,0.3)',
        }}>RP</div>
        <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto', transition: 'opacity 0.2s ease, width 0.25s ease' }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: 'white', letterSpacing: '-0.02em' }}>RPLT</div>
          <div style={{ fontSize: 10, color: '#64748b', letterSpacing: '0.06em', textTransform: 'uppercase' }}>RGF Geotechnical</div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, padding: '14px 8px', display: 'flex', flexDirection: 'column', gap: 2, overflowX: 'visible' }}>
        {NAV_ITEMS.map(item => {
          const isActive = active === item.id;
          const isHovered = hoveredItem === item.id;
          return (
            <div key={item.id} style={{ position: 'relative' }}
              onMouseEnter={() => setHoveredItem(item.id)}
              onMouseLeave={() => setHoveredItem(null)}>
              <button onClick={() => onNav(item.id)} style={{
                display: 'flex', alignItems: 'center', gap: 11,
                padding: collapsed ? '11px 0' : '11px 14px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: isActive ? 'rgba(16,185,129,0.1)' : isHovered ? 'rgba(255,255,255,0.04)' : 'transparent',
                border: 'none', borderRadius: 8, cursor: 'pointer',
                color: isActive ? '#10b981' : '#7a8599',
                transition: 'all 0.15s', width: '100%', fontSize: 13,
                fontWeight: isActive ? 600 : 400, fontFamily: 'var(--font)',
                position: 'relative',
              }}>
                {isActive && <div style={{
                  position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                  width: 3, height: 20, borderRadius: '0 3px 3px 0', background: '#10b981',
                }} />}
                <Icon d={item.icon} size={18} color={isActive ? '#10b981' : '#566378'} />
                <span style={{ overflow: 'hidden', whiteSpace: 'nowrap', opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto', transition: 'opacity 0.15s ease' }}>{item.label}</span>
              </button>
              {/* Tooltip when collapsed */}
              {collapsed && isHovered && (
                <div style={{
                  position: 'absolute', left: '100%', top: '50%', transform: 'translateY(-50%)',
                  marginLeft: 10, padding: '6px 12px', borderRadius: 7,
                  background: 'var(--navy)', color: 'white', fontSize: 12, fontWeight: 500,
                  whiteSpace: 'nowrap', boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.08)', zIndex: 100, pointerEvents: 'none',
                }}>
                  {item.label}
                  <div style={{
                    position: 'absolute', left: -4, top: '50%', transform: 'translateY(-50%) rotate(45deg)',
                    width: 8, height: 8, background: 'var(--navy)', border: '1px solid rgba(255,255,255,0.08)',
                    borderRight: 'none', borderTop: 'none',
                  }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Active test footer */}
      <div style={{
        padding: collapsed ? '14px 8px' : '16px 20px', borderTop: '1px solid rgba(255,255,255,0.06)',
        background: 'rgba(255,255,255,0.02)', transition: 'padding 0.25s ease',
        overflow: 'hidden',
      }}>
        {collapsed ? (
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{ width: 28, height: 28, borderRadius: 7, background: 'rgba(16,185,129,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700, color: '#10b981' }}>03</div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 10, color: '#566378', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Active Test</div>
            <div style={{ fontSize: 13, color: 'white', fontWeight: 500 }}>{MOCK.project.pile} — {MOCK.project.name}</div>
            <div style={{ fontSize: 11, color: '#566378', marginTop: 3 }}>
              {MOCK.project.samples.toLocaleString()} samples · {MOCK.project.date}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ─── Page Header ─────────────────────────────────────────────────────
const PageHeader = ({ title, subtitle, children }) => (
  <div style={{
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    marginBottom: 20, flexWrap: 'wrap', gap: 12,
  }}>
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em', margin: 0 }}>{title}</h1>
      {subtitle && <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '4px 0 0', fontWeight: 400 }}>{subtitle}</p>}
    </div>
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{children}</div>
  </div>
);

// ─── Processing Toolbar ──────────────────────────────────────────────
const ProcessingToolbar = () => {
  const [smooth, setSmooth] = useState(true);
  const [win, setWin] = useState(120);
  const [weight, setWeight] = useState('linear');
  
  const selectStyle = {
    padding: '5px 8px', fontSize: 12, borderRadius: 6, border: '1px solid var(--border)',
    background: 'white', color: 'var(--text)', fontFamily: 'var(--font)', outline: 'none',
  };
  const labelStyle = { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' };
  
  return (
    <div style={{
      display: 'flex', gap: 20, alignItems: 'flex-end', padding: '12px 18px',
      background: 'white', borderRadius: 10, border: '1px solid var(--border)', flexWrap: 'wrap',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 4 }}>
        <Icon d={ICONS.settings} size={14} color="#10b981" />
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>Processing</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <label style={labelStyle}>Smoothing</label>
        <button onClick={() => setSmooth(!smooth)} style={{
          ...selectStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          background: smooth ? '#f0fdf4' : 'white', borderColor: smooth ? '#a7f3d0' : 'var(--border)',
        }}>
          <span style={{ width: 8, height: 8, borderRadius: 4, background: smooth ? '#10b981' : '#cbd5e1' }} />
          {smooth ? 'On' : 'Off'}
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <label style={labelStyle}>Window</label>
        <input type="number" value={win} onChange={e => setWin(+e.target.value)}
          style={{ ...selectStyle, width: 70, fontFamily: 'var(--mono)' }} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <label style={labelStyle}>Weight</label>
        <select value={weight} onChange={e => setWeight(e.target.value)} style={selectStyle}>
          <option>linear</option><option>exponential</option><option>uniform</option>
        </select>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <label style={labelStyle}>Mass (kg)</label>
        <input type="text" defaultValue="12,000" style={{ ...selectStyle, width: 80, fontFamily: 'var(--mono)' }} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <label style={labelStyle}>Stiffness (N/m)</label>
        <input type="text" defaultValue="1,397,000" style={{ ...selectStyle, width: 100, fontFamily: 'var(--mono)' }} />
      </div>
      <div style={{ flex: 1 }} />
      <button style={{
        padding: '7px 16px', fontSize: 12, fontWeight: 600, borderRadius: 7,
        background: 'linear-gradient(135deg, #10b981, #059669)', color: 'white',
        border: 'none', cursor: 'pointer', fontFamily: 'var(--font)',
        boxShadow: '0 1px 3px rgba(16,185,129,0.3)',
      }}>Reprocess</button>
    </div>
  );
};

// ─── Badge ───────────────────────────────────────────────────────────
const Badge = ({ children, color = '#10b981' }) => (
  <span style={{
    padding: '3px 8px', fontSize: 10, fontWeight: 600, borderRadius: 5,
    background: color + '18', color: color, letterSpacing: '0.03em',
  }}>{children}</span>
);

// ─── Empty state ─────────────────────────────────────────────────────
const EmptyState = ({ icon, title, subtitle }) => (
  <div style={{
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    padding: '60px 20px', color: 'var(--text-3)', gap: 12,
  }}>
    <div style={{ width: 56, height: 56, borderRadius: 16, background: '#f3f5f9',
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Icon d={icon} size={24} color="#94a3b8" />
    </div>
    <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>{title}</div>
    {subtitle && <div style={{ fontSize: 13, color: 'var(--text-3)', maxWidth: 340, textAlign: 'center' }}>{subtitle}</div>}
  </div>
);

Object.assign(window, { KpiCard, ChartPanel, SmallBtn, IconBtn, Sidebar, PageHeader, ProcessingToolbar, Badge, EmptyState, NAV_ITEMS });
