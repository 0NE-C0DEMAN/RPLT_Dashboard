// View: Dashboard (overview)
const DashboardView = () => {
  const kpis = MOCK.kpis;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PageHeader title="Dashboard" subtitle={`${MOCK.project.name} — Pile ${MOCK.project.pile}`}>
        <Badge>3 Cycles</Badge>
        <SmallBtn><Icon d={ICONS.download} size={13} color="currentColor" /> Export</SmallBtn>
      </PageHeader>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12 }}>
        <KpiCard label={kpis.peakLoad.label} value={kpis.peakLoad.value} unit={kpis.peakLoad.unit} accent sparkData={MOCK.load.slice(50,120)} />
        <KpiCard label={kpis.maxDisp.label} value={kpis.maxDisp.value} unit={kpis.maxDisp.unit} sparkData={MOCK.disp.slice(50,120)} delta={-3.2} />
        <KpiCard label={kpis.setDisp.label} value={kpis.setDisp.value} unit={kpis.setDisp.unit} sparkData={MOCK.disp.slice(150,220)} />
        <KpiCard label={kpis.peakVel.label} value={kpis.peakVel.value} unit={kpis.peakVel.unit} sparkData={MOCK.velocity.slice(50,120)} delta={8.1} />
      </div>

      {/* Main charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <ChartPanel title="Load vs Time"
          actions={<><SmallBtn active>kN</SmallBtn><IconBtn icon={ICONS.download} title="Export" /></>}>
          <ChartCanvas
            series={[{ data: MOCK.load, color: '#10b981', label: 'Load (kN)', filled: true }]}
            xData={MOCK.time} height={220} xLabel="Time (s)" yLabel="Load (kN)" />
        </ChartPanel>
        <ChartPanel title="Displacement vs Time"
          actions={<><SmallBtn active>mm</SmallBtn><SmallBtn>μm</SmallBtn><IconBtn icon={ICONS.download} title="Export" /></>}>
          <ChartCanvas
            series={[{ data: MOCK.disp, color: '#3b82f6', label: 'Displacement', filled: true }]}
            xData={MOCK.time} height={220} xLabel="Time (s)" yLabel="Displacement (mm)" />
        </ChartPanel>
      </div>

      {/* Secondary row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <ChartPanel title="Velocity vs Time"
          actions={<IconBtn icon={ICONS.download} title="Export" />}>
          <ChartCanvas
            series={[{ data: MOCK.velocity, color: '#f59e0b', label: 'Velocity (m/s)', filled: true }]}
            xData={MOCK.time} height={180} xLabel="Time (s)" yLabel="Velocity (m/s)" />
        </ChartPanel>
        <ChartPanel title="Acceleration"
          actions={<><SmallBtn active>Smoothed</SmallBtn><SmallBtn>Raw</SmallBtn></>}>
          <ChartCanvas
            series={[
              { data: MOCK.accel, color: '#94a3b8', label: 'Raw', dashed: true },
              { data: MOCK.accelSmoothed, color: '#8b5cf6', label: 'Smoothed' },
            ]}
            xData={MOCK.time} height={180} xLabel="Time (s)" yLabel="Accel (m/s²)" />
        </ChartPanel>
      </div>

      {/* Cycle summary table */}
      <ChartPanel title="Cycle Summary" style={{ overflow: 'visible' }}
        actions={<Badge color="#3b82f6">3 cycles detected</Badge>}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                {['Cycle', 'Peak Load', 'Max Disp', 'Set Disp', 'Peak Vel', 'Duration'].map(h => (
                  <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11,
                    fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK.cycles.map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid #f3f5f9' }}>
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, background: '#f3f5f9',
                      padding: '3px 8px', borderRadius: 5, fontSize: 12 }}>#{c.id}</span>
                  </td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--mono)', fontWeight: 500 }}>{c.peakLoad.toLocaleString()} <span style={{ color: 'var(--text-3)', fontSize: 11 }}>kN</span></td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--mono)', fontWeight: 500 }}>{c.maxDisp} <span style={{ color: 'var(--text-3)', fontSize: 11 }}>mm</span></td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--mono)', fontWeight: 500 }}>{c.setDisp} <span style={{ color: 'var(--text-3)', fontSize: 11 }}>mm</span></td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--mono)', fontWeight: 500 }}>{c.peakVel} <span style={{ color: 'var(--text-3)', fontSize: 11 }}>m/s</span></td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--mono)', fontWeight: 500 }}>{c.duration} <span style={{ color: 'var(--text-3)', fontSize: 11 }}>s</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartPanel>
    </div>
  );
};

Object.assign(window, { DashboardView });
