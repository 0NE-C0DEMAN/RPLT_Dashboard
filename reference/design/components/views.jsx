// View: Import Data
const ImportView = () => {
  const [files, setFiles] = useState([
    { name: 'RPLTResults (1).xlsx', size: '534 KB', date: '2024-11-18', rows: 6315, cols: 3, status: 'active', source: 'upload' },
    { name: '20241118_145534_sourceGraph.txt', size: '23 MB', date: '2024-11-18', rows: 12420, cols: 5, status: 'imported', source: 'upload' },
    { name: 'Pile TP-04 Field Data', size: '1.2 MB', date: '2024-12-02', rows: 8740, cols: 5, status: 'imported', source: 'gsheet' },
  ]);
  const [dragOver, setDragOver] = useState(false);
  const [importTab, setImportTab] = useState('upload');
  const [sheetUrl, setSheetUrl] = useState('');
  const [gcpPath, setGcpPath] = useState('');
  const [connecting, setConnecting] = useState(false);

  const sourceIcons = { upload: ICONS.upload, gsheet: ICONS.layers, gcp: ICONS.layers };
  const sourceLabels = { upload: 'File', gsheet: 'Sheets', gcp: 'GCS' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PageHeader title="Import Data" subtitle="Upload files, connect Google Sheets, or pull from GCP Storage" />

      {/* Import source tabs */}
      <div style={{ display: 'flex', gap: 6 }}>
        {[
          { id: 'upload', label: 'File Upload', icon: ICONS.upload },
          { id: 'gsheet', label: 'Google Sheets', icon: ICONS.table },
          { id: 'gcp', label: 'GCP Storage', icon: ICONS.layers },
        ].map(tab => (
          <button key={tab.id} onClick={() => setImportTab(tab.id)} style={{
            display: 'flex', alignItems: 'center', gap: 7, padding: '10px 18px',
            fontSize: 13, fontWeight: importTab === tab.id ? 600 : 400, fontFamily: 'var(--font)',
            background: importTab === tab.id ? 'white' : 'transparent',
            border: importTab === tab.id ? '1px solid var(--border)' : '1px solid transparent',
            borderRadius: 8, cursor: 'pointer',
            color: importTab === tab.id ? 'var(--text)' : 'var(--text-3)',
            boxShadow: importTab === tab.id ? '0 1px 3px rgba(0,0,0,0.04)' : 'none',
            transition: 'all 0.15s',
          }}>
            <Icon d={tab.icon} size={15} color={importTab === tab.id ? '#10b981' : '#94a3b8'} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* File upload zone */}
      {importTab === 'upload' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={() => setDragOver(false)}
          style={{
            border: `2px dashed ${dragOver ? '#10b981' : 'var(--border)'}`,
            borderRadius: 12, padding: '48px 20px', textAlign: 'center',
            background: dragOver ? '#f0fdf4' : 'white', transition: 'all 0.2s', cursor: 'pointer',
          }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: '#f0fdf4',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
            <Icon d={ICONS.upload} size={24} color="#10b981" />
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
            Drop files here or click to browse
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
            Supports .xlsx, .csv, .txt sensor data — files up to 50 MB
          </div>
        </div>
      )}

      {/* Google Sheets */}
      {importTab === 'gsheet' && (
        <div style={{ background: 'white', borderRadius: 12, border: '1px solid var(--border)', padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#e8f5e9',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="2" stroke="#34a853" strokeWidth="1.8"/>
                <line x1="3" y1="9" x2="21" y2="9" stroke="#34a853" strokeWidth="1.5"/>
                <line x1="3" y1="15" x2="21" y2="15" stroke="#34a853" strokeWidth="1.5"/>
                <line x1="9" y1="3" x2="9" y2="21" stroke="#34a853" strokeWidth="1.5"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>Connect Google Sheet</div>
              <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Paste a shared Google Sheets URL to import data directly</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              value={sheetUrl} onChange={e => setSheetUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              style={{
                flex: 1, padding: '10px 14px', fontSize: 13, borderRadius: 8,
                border: '1px solid var(--border)', background: '#fafbfc', fontFamily: 'var(--font)',
                outline: 'none', color: 'var(--text)',
              }} />
            <button onClick={() => setConnecting(true)} style={{
              padding: '10px 20px', fontSize: 13, fontWeight: 600, borderRadius: 8,
              background: '#34a853', color: 'white', border: 'none', cursor: 'pointer',
              fontFamily: 'var(--font)', whiteSpace: 'nowrap',
            }}>Import Sheet</button>
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 16 }}>
            {['Sheet must be shared (view access)', 'First row used as column headers', 'Auto-detects numeric columns'].map(tip => (
              <div key={tip} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
                <Icon d={ICONS.info} size={12} color="#94a3b8" />
                {tip}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GCP Storage */}
      {importTab === 'gcp' && (
        <div style={{ background: 'white', borderRadius: 12, border: '1px solid var(--border)', padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#e3f2fd',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#4285f4" strokeWidth="1.8" strokeLinejoin="round"/>
                <path d="M2 17l10 5 10-5" stroke="#4285f4" strokeWidth="1.8" strokeLinejoin="round"/>
                <path d="M2 12l10 5 10-5" stroke="#4285f4" strokeWidth="1.8" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>Google Cloud Storage</div>
              <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Browse or enter a GCS bucket path to import sensor files</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <label style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>GCP Project</label>
                <input defaultValue="rgf-geotechnical-prod" style={{
                  padding: '9px 12px', fontSize: 13, borderRadius: 7, border: '1px solid var(--border)',
                  fontFamily: 'var(--mono)', fontSize: 12, outline: 'none', color: 'var(--text)', background: '#fafbfc',
                }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <label style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Bucket</label>
                <input defaultValue="rgf-rplt-data" style={{
                  padding: '9px 12px', fontSize: 13, borderRadius: 7, border: '1px solid var(--border)',
                  fontFamily: 'var(--mono)', fontSize: 12, outline: 'none', color: 'var(--text)', background: '#fafbfc',
                }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <input
                value={gcpPath} onChange={e => setGcpPath(e.target.value)}
                placeholder="path/to/sensor-data/ or gs://bucket/file.csv"
                style={{
                  flex: 1, padding: '10px 14px', fontSize: 13, borderRadius: 8,
                  border: '1px solid var(--border)', background: '#fafbfc', fontFamily: 'var(--mono)', fontSize: 12,
                  outline: 'none', color: 'var(--text)',
                }} />
              <button style={{
                padding: '10px 20px', fontSize: 13, fontWeight: 600, borderRadius: 8,
                background: '#4285f4', color: 'white', border: 'none', cursor: 'pointer',
                fontFamily: 'var(--font)', whiteSpace: 'nowrap',
              }}>Browse Bucket</button>
            </div>

            {/* Mock file browser */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', marginTop: 4 }}>
              <div style={{ padding: '8px 12px', background: '#f8f9fb', borderBottom: '1px solid var(--border)',
                fontSize: 11, fontWeight: 600, color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>
                gs://rgf-rplt-data/2024/
              </div>
              {[
                { name: '2024-11-18_TP03/', type: 'folder', size: '—' },
                { name: '2024-12-02_TP04/', type: 'folder', size: '—' },
                { name: '20241118_145534_sourceGraph.txt', type: 'file', size: '23 MB' },
                { name: 'calibration_data.csv', type: 'file', size: '145 KB' },
              ].map((item, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
                  borderBottom: i < 3 ? '1px solid #f3f5f9' : 'none', cursor: 'pointer',
                  fontSize: 13, transition: 'background 0.1s',
                }}>
                  <Icon d={item.type === 'folder' ? ICONS.chevRight : ICONS.report} size={14}
                    color={item.type === 'folder' ? '#f59e0b' : '#64748b'} />
                  <span style={{ flex: 1, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text)' }}>{item.name}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>{item.size}</span>
                  {item.type === 'file' && <SmallBtn style={{ padding: '3px 8px', fontSize: 10 }}>Import</SmallBtn>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Column Mapping */}
      <ChartPanel title="Column Mapping" actions={<Badge color="#f59e0b">Auto-detected</Badge>}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, padding: '8px 0' }}>
          {[
            { label: 'Time Column', value: 'Time (s)', options: ['Time (s)', 'Timestamp', 'T'] },
            { label: 'Acceleration Column', value: 'Scaled (m/s2)', options: ['Scaled (m/s2)', 'Accel_raw', 'A'] },
            { label: 'Load Column', value: 'Load (kN)', options: ['Load (kN)', 'Force', 'F'] },
          ].map(col => (
            <div key={col.label} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{col.label}</label>
              <select defaultValue={col.value} style={{
                padding: '8px 10px', fontSize: 13, borderRadius: 7, border: '1px solid var(--border)',
                background: 'white', color: 'var(--text)', fontFamily: 'var(--mono)', fontSize: 12, outline: 'none',
              }}>
                {col.options.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
      </ChartPanel>

      {/* File list */}
      <ChartPanel title="Imported Files" actions={<SmallBtn>Clear All</SmallBtn>}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {files.map((f, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 14, padding: '12px 6px',
              borderBottom: i < files.length - 1 ? '1px solid #f5f6f8' : 'none',
            }}>
              <div style={{ width: 38, height: 38, borderRadius: 9,
                background: f.source === 'gsheet' ? '#e8f5e9' : f.source === 'gcp' ? '#e3f2fd' : '#f3f5f9',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon d={f.source === 'gsheet' ? ICONS.table : f.source === 'gcp' ? ICONS.layers : ICONS.report} size={18}
                  color={f.source === 'gsheet' ? '#34a853' : f.source === 'gcp' ? '#4285f4' : '#64748b'} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{f.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>
                  {f.size} · {f.rows.toLocaleString()} rows · {f.cols} cols · {f.date}
                  <span style={{ marginLeft: 6, padding: '1px 5px', borderRadius: 3, background: '#f3f5f9',
                    fontSize: 10, fontWeight: 500, color: '#64748b' }}>{sourceLabels[f.source]}</span>
                </div>
              </div>
              <Badge color={f.status === 'active' ? '#10b981' : '#64748b'}>
                {f.status === 'active' ? 'Active' : 'Imported'}
              </Badge>
            </div>
          ))}
        </div>
      </ChartPanel>

      {/* Data preview */}
      <ChartPanel title="Data Preview" actions={<span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>Showing first 8 rows</span>}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--mono)', fontSize: 12 }}>
            <thead>
              <tr>{['#', 'Time (s)', 'Scaled (m/s²)', 'Load (kN)'].map(h => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 10, fontWeight: 600,
                  color: 'var(--text-3)', borderBottom: '2px solid var(--border)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {Array.from({length: 8}, (_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f5f6f8' }}>
                  <td style={{ padding: '7px 12px', color: 'var(--text-3)' }}>{i + 1}</td>
                  <td style={{ padding: '7px 12px' }}>{MOCK.time[i]}</td>
                  <td style={{ padding: '7px 12px' }}>{MOCK.accel[i]}</td>
                  <td style={{ padding: '7px 12px' }}>{MOCK.load[i]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartPanel>
    </div>
  );
};

// View: Standard Analysis
const StandardView = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <PageHeader title="Standard Analysis" subtitle="Load, displacement, and velocity from processed sensor data">
      <SmallBtn active>All Signals</SmallBtn>
      <SmallBtn>Load Only</SmallBtn>
    </PageHeader>
    <ProcessingToolbar />
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <ChartPanel title="Load vs Time" actions={<IconBtn icon={ICONS.download} />}>
        <ChartCanvas series={[{ data: MOCK.load, color: '#10b981', label: 'Load (kN)', filled: true }]}
          xData={MOCK.time} height={240} xLabel="Time (s)" yLabel="Load (kN)" />
      </ChartPanel>
      <ChartPanel title="Displacement vs Time" actions={<IconBtn icon={ICONS.download} />}>
        <ChartCanvas series={[{ data: MOCK.disp, color: '#3b82f6', label: 'Displacement (mm)', filled: true }]}
          xData={MOCK.time} height={240} xLabel="Time (s)" yLabel="Displacement (mm)" />
      </ChartPanel>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <ChartPanel title="Velocity vs Time" actions={<IconBtn icon={ICONS.download} />}>
        <ChartCanvas series={[{ data: MOCK.velocity, color: '#f59e0b', label: 'Velocity (m/s)', filled: true }]}
          xData={MOCK.time} height={200} xLabel="Time (s)" yLabel="Velocity (m/s)" />
      </ChartPanel>
      <ChartPanel title="Acceleration — Raw vs Smoothed"
        actions={<><SmallBtn active>Overlay</SmallBtn><SmallBtn>Split</SmallBtn></>}>
        <ChartCanvas series={[
          { data: MOCK.accel, color: '#cbd5e1', label: 'Raw', dashed: true },
          { data: MOCK.accelSmoothed, color: '#8b5cf6', label: 'Smoothed' },
        ]} xData={MOCK.time} height={200} xLabel="Time (s)" yLabel="Accel (m/s²)" />
      </ChartPanel>
    </div>
  </div>
);

// View: UPM Analysis
const UPMView = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <PageHeader title="UPM Analysis" subtitle="Unloading Point Method — force decomposition">
      <Badge color="#8b5cf6">UPM</Badge>
    </PageHeader>
    <ProcessingToolbar />
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <ChartPanel title="Force Components vs Time"
        actions={<><SmallBtn active>Overlay</SmallBtn><SmallBtn>Stacked</SmallBtn></>}>
        <ChartCanvas series={[
          { data: MOCK.load, color: '#10b981', label: 'Total Load' },
          { data: MOCK.fma, color: '#3b82f6', label: 'F=ma (Inertia)' },
          { data: MOCK.fkx, color: '#f59e0b', label: 'F=kx (Spring)' },
        ]} xData={MOCK.time} height={260} xLabel="Time (s)" yLabel="Force (kN)" />
      </ChartPanel>
      <ChartPanel title="Total Force vs Time" actions={<IconBtn icon={ICONS.download} />}>
        <ChartCanvas series={[{ data: MOCK.totalForce, color: '#8b5cf6', label: 'Total Force (kN)', filled: true }]}
          xData={MOCK.time} height={260} xLabel="Time (s)" yLabel="Total Force (kN)" />
      </ChartPanel>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <ChartPanel title="Load vs Displacement" actions={<IconBtn icon={ICONS.download} />}>
        <ChartCanvas series={[{ data: MOCK.load, color: '#10b981', label: 'Load (kN)' }]}
          xData={MOCK.disp} height={220} xLabel="Displacement (mm)" yLabel="Load (kN)" />
      </ChartPanel>
      <ChartPanel title="UPM Parameters" style={{ overflow: 'visible' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, padding: '8px 0' }}>
          {[
            { label: 'Mass', value: MOCK.project.mass, unit: 'kg' },
            { label: 'Stiffness', value: MOCK.project.stiffness, unit: 'N/m' },
            { label: 'UPM Capacity', value: '2,487', unit: 'kN' },
            { label: 'Mobilized Resistance', value: '1,893', unit: 'kN' },
          ].map(p => (
            <div key={p.label} style={{ padding: '12px 14px', background: '#f8f9fb', borderRadius: 8 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>{p.label}</div>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>{p.value}</span>
              <span style={{ fontSize: 12, color: 'var(--text-3)', marginLeft: 4 }}>{p.unit}</span>
            </div>
          ))}
        </div>
      </ChartPanel>
    </div>
  </div>
);

// View: Cycle Analysis (NEW)
const CycleView = () => {
  const [activeCycle, setActiveCycle] = useState(0);
  const cycle = MOCK.cycles[activeCycle];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <PageHeader title="Cycle Analysis" subtitle="Compare individual impact cycles side by side">
        <div style={{ display: 'flex', gap: 4 }}>
          {MOCK.cycles.map((c, i) => (
            <SmallBtn key={i} active={activeCycle === i} onClick={() => setActiveCycle(i)}>Cycle {c.id}</SmallBtn>
          ))}
        </div>
      </PageHeader>

      {/* Cycle KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <KpiCard label="Peak Load" value={cycle.peakLoad.toLocaleString()} unit="kN" accent />
        <KpiCard label="Max Displacement" value={cycle.maxDisp.toString()} unit="mm" />
        <KpiCard label="Set Displacement" value={cycle.setDisp.toString()} unit="mm" />
        <KpiCard label="Peak Velocity" value={cycle.peakVel.toString()} unit="m/s" />
        <KpiCard label="Duration" value={cycle.duration.toString()} unit="s" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <ChartPanel title={`Cycle ${cycle.id} — Load vs Time`}>
          <ChartCanvas series={[{ data: MOCK.load.slice(activeCycle*80, activeCycle*80+100), color: '#10b981', label: 'Load', filled: true }]}
            xData={MOCK.time.slice(0, 100)} height={240} xLabel="Time (s)" yLabel="Load (kN)" />
        </ChartPanel>
        <ChartPanel title={`Cycle ${cycle.id} — Displacement vs Time`}>
          <ChartCanvas series={[{ data: MOCK.disp.slice(activeCycle*80, activeCycle*80+100), color: '#3b82f6', label: 'Disp', filled: true }]}
            xData={MOCK.time.slice(0, 100)} height={240} xLabel="Time (s)" yLabel="Disp (mm)" />
        </ChartPanel>
      </div>

      {/* Overlay comparison */}
      <ChartPanel title="Cycle Overlay — Load Comparison"
        actions={<Badge color="#06b6d4">All cycles</Badge>}>
        <ChartCanvas series={MOCK.cycles.map((c, i) => ({
          data: MOCK.load.slice(i*80, i*80+100).map(v => v * (0.85 + i*0.15)),
          color: ['#10b981','#3b82f6','#f59e0b'][i], label: `Cycle ${c.id}`,
        }))} xData={MOCK.time.slice(0, 100)} height={260} xLabel="Time (s)" yLabel="Load (kN)" />
      </ChartPanel>
    </div>
  );
};

// View: Report Builder (NEW)
const ReportView = () => {
  const [sections, setSections] = useState([
    { id: 1, title: 'Test Summary', type: 'summary', included: true },
    { id: 2, title: 'Load vs Time Chart', type: 'chart', included: true },
    { id: 3, title: 'Displacement Chart', type: 'chart', included: true },
    { id: 4, title: 'UPM Force Decomposition', type: 'chart', included: true },
    { id: 5, title: 'Cycle Comparison Table', type: 'table', included: true },
    { id: 6, title: 'Raw Data Appendix', type: 'data', included: false },
  ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <PageHeader title="Report Builder" subtitle="Compose and export a client-ready report">
        <SmallBtn style={{ background: 'linear-gradient(135deg,#10b981,#059669)', color: 'white', border: 'none', padding: '8px 18px', fontWeight: 600 }}>
          Generate PDF
        </SmallBtn>
      </PageHeader>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16 }}>
        {/* Section picker */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <ChartPanel title="Report Sections" actions={<SmallBtn>+ Add</SmallBtn>}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '4px 0' }}>
              {sections.map(s => (
                <div key={s.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '10px 8px',
                  borderRadius: 7, cursor: 'pointer', transition: 'background 0.1s',
                  background: s.included ? '#f0fdf4' : 'transparent',
                }}>
                  <button onClick={() => setSections(prev => prev.map(p => p.id === s.id ? {...p, included: !p.included} : p))}
                    style={{
                      width: 20, height: 20, borderRadius: 5, border: `2px solid ${s.included ? '#10b981' : 'var(--border)'}`,
                      background: s.included ? '#10b981' : 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      cursor: 'pointer', flexShrink: 0, transition: 'all 0.15s',
                    }}>
                    {s.included && <Icon d={ICONS.check} size={12} color="white" />}
                  </button>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>{s.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.type}</div>
                  </div>
                  <Icon d={ICONS.grip} size={14} color="#cbd5e1" />
                </div>
              ))}
            </div>
          </ChartPanel>

          <ChartPanel title="Report Settings">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              {[
                { label: 'Project Name', value: MOCK.project.name },
                { label: 'Client', value: 'Apex Infrastructure' },
                { label: 'Pile Reference', value: MOCK.project.pile },
                { label: 'Test Date', value: MOCK.project.date },
                { label: 'Engineer', value: MOCK.project.operator },
              ].map(f => (
                <div key={f.label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <label style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{f.label}</label>
                  <input defaultValue={f.value} style={{
                    padding: '7px 10px', fontSize: 13, borderRadius: 6, border: '1px solid var(--border)',
                    background: 'white', color: 'var(--text)', fontFamily: 'var(--font)', outline: 'none',
                  }} />
                </div>
              ))}
            </div>
          </ChartPanel>
        </div>

        {/* Report preview */}
        <div style={{
          background: 'white', borderRadius: 10, border: '1px solid var(--border)', padding: '40px',
          minHeight: 500, boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
        }}>
          <div style={{ maxWidth: 640, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 36, paddingBottom: 24, borderBottom: '2px solid var(--border)' }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
                Rapid Plate Load Test Report
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
                {MOCK.project.name}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 8 }}>
                Pile {MOCK.project.pile} · {MOCK.project.date} · {MOCK.project.operator}
              </div>
            </div>

            <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text-2)' }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>Test Summary</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 24 }}>
                {Object.values(MOCK.kpis).map(k => (
                  <div key={k.label} style={{ padding: '10px 14px', background: '#f8f9fb', borderRadius: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-3)', fontSize: 12 }}>{k.label}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, fontSize: 13 }}>{k.value} {k.unit}</span>
                  </div>
                ))}
              </div>

              <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>Load vs Time</h3>
              <div style={{ background: '#f8f9fb', borderRadius: 8, padding: 12, marginBottom: 24 }}>
                <ChartCanvas series={[{ data: MOCK.load, color: '#10b981', filled: true, label: 'Load' }]}
                  xData={MOCK.time} height={180} xLabel="Time (s)" yLabel="Load (kN)" showLegend={false} />
              </div>

              <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>Displacement</h3>
              <div style={{ background: '#f8f9fb', borderRadius: 8, padding: 12 }}>
                <ChartCanvas series={[{ data: MOCK.disp, color: '#3b82f6', filled: true, label: 'Disp' }]}
                  xData={MOCK.time} height={180} xLabel="Time (s)" yLabel="Disp (mm)" showLegend={false} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// View: Raw Data
const RawDataView = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <PageHeader title="Raw Data" subtitle="Full sample table with search and export">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 7,
        border: '1px solid var(--border)', background: 'white' }}>
        <Icon d={ICONS.search} size={14} color="#94a3b8" />
        <input placeholder="Search samples..." style={{ border: 'none', outline: 'none', fontSize: 13,
          fontFamily: 'var(--font)', color: 'var(--text)', background: 'transparent', width: 160 }} />
      </div>
      <IconBtn icon={ICONS.filter} title="Filter" />
      <IconBtn icon={ICONS.download} title="Export CSV" />
    </PageHeader>

    <ChartPanel title="Sample Data" style={{ overflow: 'visible' }}
      actions={<span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>6,315 rows</span>}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--mono)', fontSize: 12 }}>
          <thead>
            <tr>{['#', 'Time (s)', 'Accel (m/s²)', 'Accel Smoothed', 'Load (kN)', 'Velocity (m/s)', 'Disp (mm)', 'F=ma (kN)', 'F=kx (kN)'].map(h => (
              <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 10, fontWeight: 600,
                color: 'var(--text-3)', borderBottom: '2px solid var(--border)', textTransform: 'uppercase',
                letterSpacing: '0.03em', whiteSpace: 'nowrap', position: 'sticky', top: 0, background: 'white' }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {Array.from({length: 20}, (_, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #f5f6f8', background: i % 2 === 0 ? 'white' : '#fafbfc' }}>
                <td style={{ padding: '7px 12px', color: 'var(--text-3)' }}>{i + 1}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.time[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.accel[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.accelSmoothed[i]}</td>
                <td style={{ padding: '7px 12px', color: '#10b981', fontWeight: 500 }}>{MOCK.load[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.velocity[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.disp[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.fma[i]}</td>
                <td style={{ padding: '7px 12px' }}>{MOCK.fkx[i]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0 4px', borderTop: '1px solid var(--border)', marginTop: 8 }}>
        <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Showing 1–20 of 6,315</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <SmallBtn>Prev</SmallBtn>
          <SmallBtn active>1</SmallBtn>
          <SmallBtn>2</SmallBtn>
          <SmallBtn>3</SmallBtn>
          <SmallBtn>…</SmallBtn>
          <SmallBtn>316</SmallBtn>
          <SmallBtn>Next</SmallBtn>
        </div>
      </div>
    </ChartPanel>
  </div>
);

Object.assign(window, { ImportView, StandardView, UPMView, CycleView, ReportView, RawDataView });
