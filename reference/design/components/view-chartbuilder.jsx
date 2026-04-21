// View: Chart Builder (custom chart configuration)
const { useState, Fragment } = React;

const CHART_TYPES = ['Line', 'Scatter', 'Area', 'Bar', 'Histogram', 'Box'];
const AGGREGATIONS = ['(none)', 'mean', 'max', 'min', 'sum', 'count'];
const ALL_COLS = ['Time (s)', 'Scaled (m/s2)', 'Load (kN)', 'Velocity (m/s)', 'Disp (m)', 'Fma (kN)', 'Fkx (kN)', 'Total Force (kN)'];
const NUM_COLS = ALL_COLS;

const ChartBuilderView = () => {
  const [chartType, setChartType] = useState('Line');
  const [xCol, setXCol] = useState('Time (s)');
  const [yCols, setYCols] = useState(['Load (kN)']);
  const [agg, setAgg] = useState('(none)');
  const [filterCol, setFilterCol] = useState('(none)');
  const [filterOp, setFilterOp] = useState('(none)');
  const [filterVal, setFilterVal] = useState(0);
  const [maxRows, setMaxRows] = useState(10000);
  const [showSql, setShowSql] = useState(false);

  const toggleYCol = (col) => {
    setYCols(prev => prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]);
  };

  // Build mock SQL
  const buildSql = () => {
    const yParts = yCols.map(c => agg !== '(none)' ? `${agg.toUpperCase()}("${c}")` : `"${c}"`).join(', ');
    const where = filterCol !== '(none)' && filterOp !== '(none)' ? `\nWHERE "${filterCol}" ${filterOp} ${filterVal}` : '';
    const group = agg !== '(none)' ? `\nGROUP BY "${xCol}"` : '';
    return `SELECT "${xCol}", ${yParts}\nFROM rplt_data${where}${group}\nORDER BY "${xCol}"\nLIMIT ${maxRows}`;
  };

  // Map yCols to mock data
  const colDataMap = {
    'Load (kN)': MOCK.load, 'Velocity (m/s)': MOCK.velocity, 'Disp (m)': MOCK.disp,
    'Scaled (m/s2)': MOCK.accel, 'Fma (kN)': MOCK.fma, 'Fkx (kN)': MOCK.fkx,
    'Total Force (kN)': MOCK.totalForce, 'Time (s)': MOCK.time,
  };
  const xDataMap = { 'Time (s)': MOCK.time, 'Disp (m)': MOCK.disp, 'Load (kN)': MOCK.load,
    'Velocity (m/s)': MOCK.velocity, 'Scaled (m/s2)': MOCK.accel, 'Fma (kN)': MOCK.fma,
    'Fkx (kN)': MOCK.fkx, 'Total Force (kN)': MOCK.totalForce };
  const palette = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

  const selectStyle = {
    padding: '8px 10px', fontSize: 12, borderRadius: 7, border: '1px solid var(--border)',
    background: 'white', color: 'var(--text)', fontFamily: 'var(--font)', outline: 'none', width: '100%',
  };
  const labelStyle = { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4, display: 'block' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <PageHeader title="Chart Builder" subtitle="Build custom charts from any column combination">
        <SmallBtn onClick={() => setShowSql(!showSql)} active={showSql}>SQL</SmallBtn>
        <IconBtn icon={ICONS.download} title="Export Chart" />
        <IconBtn icon={ICONS.printer} title="Print" />
      </PageHeader>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, alignItems: 'start' }}>
        {/* Config panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ChartPanel title="Configure">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: '4px 0' }}>
              {/* Chart type */}
              <div>
                <label style={labelStyle}>Chart Type</label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4 }}>
                  {CHART_TYPES.map(t => (
                    <SmallBtn key={t} active={chartType === t} onClick={() => setChartType(t)}
                      style={{ fontSize: 11, padding: '6px 0', textAlign: 'center', width: '100%' }}>{t}</SmallBtn>
                  ))}
                </div>
              </div>

              {/* X axis */}
              <div>
                <label style={labelStyle}>X Axis</label>
                <select value={xCol} onChange={e => setXCol(e.target.value)} style={selectStyle}>
                  {ALL_COLS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>

              {/* Y axis multi-select */}
              <div>
                <label style={labelStyle}>Y Axis (multi)</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 180, overflowY: 'auto' }}>
                  {NUM_COLS.filter(c => c !== xCol).map(c => (
                    <label key={c} style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                      borderRadius: 6, cursor: 'pointer', fontSize: 12,
                      background: yCols.includes(c) ? '#f0fdf4' : 'transparent',
                      border: `1px solid ${yCols.includes(c) ? '#a7f3d0' : 'transparent'}`,
                      transition: 'all 0.1s',
                    }}>
                      <input type="checkbox" checked={yCols.includes(c)} onChange={() => toggleYCol(c)}
                        style={{ accentColor: '#10b981' }} />
                      <span style={{ color: yCols.includes(c) ? 'var(--text)' : 'var(--text-3)' }}>{c}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Aggregation */}
              <div>
                <label style={labelStyle}>Aggregation</label>
                <select value={agg} onChange={e => setAgg(e.target.value)} style={selectStyle}>
                  {AGGREGATIONS.map(a => <option key={a}>{a}</option>)}
                </select>
              </div>
            </div>
          </ChartPanel>

          {/* Filter */}
          <ChartPanel title="Filter">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Column</label>
                <select value={filterCol} onChange={e => setFilterCol(e.target.value)} style={selectStyle}>
                  <option>(none)</option>
                  {NUM_COLS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              {filterCol !== '(none)' && <>
                <div>
                  <label style={labelStyle}>Operator</label>
                  <select value={filterOp} onChange={e => setFilterOp(e.target.value)} style={selectStyle}>
                    {['(none)', '>', '>=', '<', '<=', '='].map(o => <option key={o}>{o}</option>)}
                  </select>
                </div>
                {filterOp !== '(none)' && <div>
                  <label style={labelStyle}>Value</label>
                  <input type="number" value={filterVal} onChange={e => setFilterVal(+e.target.value)}
                    style={{ ...selectStyle, fontFamily: 'var(--mono)' }} />
                </div>}
              </>}
            </div>
          </ChartPanel>

          {/* Sample size */}
          <ChartPanel title="Sample">
            <div style={{ padding: '4px 0' }}>
              <label style={labelStyle}>Max Rows</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="range" min={100} max={50000} step={100} value={maxRows}
                  onChange={e => setMaxRows(+e.target.value)}
                  style={{ flex: 1, accentColor: '#10b981' }} />
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text)', minWidth: 50, textAlign: 'right' }}>
                  {maxRows.toLocaleString()}
                </span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 4 }}>More rows = more detail, slower render</div>
            </div>
          </ChartPanel>
        </div>

        {/* Chart preview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ChartPanel title={`${chartType}: ${yCols.join(', ')} vs ${xCol}`}
            actions={<>
              <Badge>{yCols.length} series</Badge>
              <Badge color="#3b82f6">{maxRows.toLocaleString()} rows</Badge>
            </>}>
            {yCols.length > 0 ? (
              <ChartCanvas
                series={yCols.map((c, i) => ({
                  data: colDataMap[c] || MOCK.load,
                  color: palette[i % palette.length],
                  label: c,
                  filled: chartType === 'Area',
                }))}
                xData={xDataMap[xCol] || MOCK.time}
                height={420}
                xLabel={xCol}
                yLabel={yCols.join(', ')}
              />
            ) : (
              <EmptyState icon={ICONS.chart} title="Select Y-axis columns" subtitle="Pick at least one column to plot" />
            )}
          </ChartPanel>

          {/* SQL preview */}
          {showSql && (
            <div style={{
              background: 'var(--navy)', borderRadius: 10, padding: '16px 20px',
              fontFamily: 'var(--mono)', fontSize: 12, color: '#a3e635',
              lineHeight: 1.7, whiteSpace: 'pre-wrap', position: 'relative',
            }}>
              <div style={{ position: 'absolute', top: 10, right: 14, fontSize: 10, color: '#64748b',
                textTransform: 'uppercase', letterSpacing: '0.06em' }}>Generated SQL</div>
              {buildSql()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { ChartBuilderView });
