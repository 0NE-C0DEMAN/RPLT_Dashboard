// View: Settings & Calibration
const { useState } = React;

const SettingsView = () => {
  const [activeTab, setActiveTab] = useState('general');

  const inputStyle = {
    padding: '9px 12px', fontSize: 13, borderRadius: 7, border: '1px solid var(--border)',
    background: 'white', color: 'var(--text)', fontFamily: 'var(--font)', outline: 'none', width: '100%',
  };
  const monoInput = { ...inputStyle, fontFamily: 'var(--mono)', fontSize: 12 };
  const labelStyle = { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4, display: 'block' };

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'processing', label: 'Processing Defaults' },
    { id: 'calibration', label: 'Sensor Calibration' },
    { id: 'export', label: 'Export & Reports' },
    { id: 'gcp', label: 'GCP Connection' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <PageHeader title="Settings" subtitle="Configure defaults, calibration, and cloud connections" />

      <div style={{ display: 'flex', gap: 6, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: '10px 18px', fontSize: 13, fontWeight: activeTab === t.id ? 600 : 400,
            color: activeTab === t.id ? 'var(--text)' : 'var(--text-3)',
            background: 'none', border: 'none', borderBottom: activeTab === t.id ? '2px solid #10b981' : '2px solid transparent',
            cursor: 'pointer', fontFamily: 'var(--font)', transition: 'all 0.15s', marginBottom: -1,
          }}>{t.label}</button>
        ))}
      </div>

      {activeTab === 'general' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <ChartPanel title="Company Information">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              {[
                { label: 'Company Name', value: 'Riyadh Geotechnique & Foundations Co.' },
                { label: 'Division', value: 'Pile Testing' },
                { label: 'Default Engineer', value: 'J. Martinez' },
                { label: 'Report Template', value: 'RGF Standard v2.1' },
              ].map(f => (
                <div key={f.label}>
                  <label style={labelStyle}>{f.label}</label>
                  <input defaultValue={f.value} style={inputStyle} />
                </div>
              ))}
            </div>
          </ChartPanel>
          <ChartPanel title="Display Preferences">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Default Unit System</label>
                <select defaultValue="SI" style={inputStyle}>
                  <option>SI (kN, m, m/s²)</option>
                  <option>Imperial (kip, ft, ft/s²)</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Chart Theme</label>
                <select defaultValue="light" style={inputStyle}>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Number Precision</label>
                <select defaultValue="auto" style={inputStyle}>
                  <option value="auto">Auto</option>
                  <option value="2">2 decimal places</option>
                  <option value="4">4 decimal places</option>
                  <option value="6">6 decimal places</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Date Format</label>
                <select defaultValue="iso" style={inputStyle}>
                  <option value="iso">YYYY-MM-DD</option>
                  <option value="us">MM/DD/YYYY</option>
                  <option value="eu">DD/MM/YYYY</option>
                </select>
              </div>
            </div>
          </ChartPanel>
        </div>
      )}

      {activeTab === 'processing' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <ChartPanel title="Smoothing Defaults">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Apply Smoothing</label>
                <select defaultValue="true" style={inputStyle}>
                  <option value="true">Enabled by default</option>
                  <option value="false">Disabled by default</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Smoothing Window</label>
                <input type="number" defaultValue={120} style={monoInput} />
                <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 3 }}>Range: 2 – 10,000 samples</div>
              </div>
              <div>
                <label style={labelStyle}>Smoothing Weight</label>
                <select defaultValue="linear" style={inputStyle}>
                  <option>linear</option>
                  <option>exponential</option>
                  <option>uniform</option>
                </select>
              </div>
            </div>
          </ChartPanel>
          <ChartPanel title="UPM Defaults">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Default Mass (kg)</label>
                <input type="text" defaultValue="12,000" style={monoInput} />
              </div>
              <div>
                <label style={labelStyle}>Default Stiffness (N/m)</label>
                <input type="text" defaultValue="1,397,000" style={monoInput} />
              </div>
              <div>
                <label style={labelStyle}>Auto Zero-Mean</label>
                <select defaultValue="true" style={inputStyle}>
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Load Input Mode</label>
                <select defaultValue="original" style={inputStyle}>
                  <option value="original">Original (from sensor)</option>
                  <option value="computed">Computed</option>
                </select>
              </div>
            </div>
          </ChartPanel>
          <ChartPanel title="Column Auto-Detection">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.6, padding: '4px 0 8px' }}>
                Column names are matched case-insensitively. Add aliases below to improve auto-detection for your data files.
              </div>
              {[
                { label: 'Time Aliases', value: 'Time (s), Timestamp, T, time_s' },
                { label: 'Acceleration Aliases', value: 'Scaled (m/s2), Accel_raw, Acceleration, A' },
                { label: 'Load Aliases', value: 'Load (kN), Force, LOAD, F' },
              ].map(f => (
                <div key={f.label}>
                  <label style={labelStyle}>{f.label}</label>
                  <input defaultValue={f.value} style={{ ...monoInput, fontSize: 11 }} />
                </div>
              ))}
            </div>
          </ChartPanel>
        </div>
      )}

      {activeTab === 'calibration' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px',
            background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10,
          }}>
            <Icon d={ICONS.info} size={18} color="#f59e0b" />
            <div style={{ fontSize: 13, color: '#92400e' }}>
              Calibration factors are applied during data import. Changing these will not retroactively update already-imported data.
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <ChartPanel title="Accelerometer Calibration">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
                <div>
                  <label style={labelStyle}>Sensor Model</label>
                  <input defaultValue="PCB 352C03" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Sensitivity (mV/g)</label>
                  <input type="text" defaultValue="10.00" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Scale Factor</label>
                  <input type="text" defaultValue="1.0000" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Zero Offset (m/s²)</label>
                  <input type="text" defaultValue="0.000" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Last Calibrated</label>
                  <input type="date" defaultValue="2024-10-15" style={inputStyle} />
                </div>
              </div>
            </ChartPanel>
            <ChartPanel title="Load Cell Calibration">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
                <div>
                  <label style={labelStyle}>Sensor Model</label>
                  <input defaultValue="HBM U10M" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Rated Capacity (kN)</label>
                  <input type="text" defaultValue="5000" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Scale Factor</label>
                  <input type="text" defaultValue="1.0000" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Zero Offset (kN)</label>
                  <input type="text" defaultValue="0.000" style={monoInput} />
                </div>
                <div>
                  <label style={labelStyle}>Last Calibrated</label>
                  <input type="date" defaultValue="2024-09-20" style={inputStyle} />
                </div>
              </div>
            </ChartPanel>
          </div>
        </div>
      )}

      {activeTab === 'export' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <ChartPanel title="PDF Report Defaults">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Page Size</label>
                <select defaultValue="A4" style={inputStyle}>
                  <option>A4</option><option>Letter</option><option>A3</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Orientation</label>
                <select defaultValue="portrait" style={inputStyle}>
                  <option value="portrait">Portrait</option>
                  <option value="landscape">Landscape</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Include Company Logo</label>
                <select defaultValue="true" style={inputStyle}>
                  <option value="true">Yes</option><option value="false">No</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Default Sections</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                  {['Test Summary', 'Load vs Time', 'Displacement', 'Velocity', 'UPM Decomposition', 'Cycle Table', 'Raw Data Appendix'].map(s => (
                    <label key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
                      <input type="checkbox" defaultChecked={s !== 'Raw Data Appendix'} style={{ accentColor: '#10b981' }} />
                      {s}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </ChartPanel>
          <ChartPanel title="Chart Export">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Image Format</label>
                <select defaultValue="png" style={inputStyle}>
                  <option value="png">PNG (high quality)</option>
                  <option value="svg">SVG (vector)</option>
                  <option value="jpg">JPEG (smaller file)</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Resolution Scale</label>
                <select defaultValue="2" style={inputStyle}>
                  <option value="1">1× (standard)</option>
                  <option value="2">2× (retina)</option>
                  <option value="3">3× (print quality)</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>CSV Delimiter</label>
                <select defaultValue="comma" style={inputStyle}>
                  <option value="comma">Comma (,)</option>
                  <option value="tab">Tab</option>
                  <option value="semicolon">Semicolon (;)</option>
                </select>
              </div>
            </div>
          </ChartPanel>
        </div>
      )}

      {activeTab === 'gcp' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <ChartPanel title="Google Cloud Connection">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>GCP Project ID</label>
                <input defaultValue="rgf-geotechnical-prod" style={monoInput} />
              </div>
              <div>
                <label style={labelStyle}>Default Bucket</label>
                <input defaultValue="rgf-rplt-data" style={monoInput} />
              </div>
              <div>
                <label style={labelStyle}>Service Account Key</label>
                <div style={{
                  padding: '12px', borderRadius: 8, border: '1px dashed var(--border)',
                  background: '#fafbfc', textAlign: 'center', cursor: 'pointer',
                }}>
                  <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Drop .json key file or click to upload</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: '#f0fdf4', borderRadius: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: 4, background: '#10b981' }} />
                <span style={{ fontSize: 12, color: '#059669', fontWeight: 500 }}>Connected — last verified 2h ago</span>
              </div>
            </div>
          </ChartPanel>
          <ChartPanel title="Google Sheets Integration">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
              <div>
                <label style={labelStyle}>Authentication</label>
                <select defaultValue="oauth" style={inputStyle}>
                  <option value="oauth">OAuth 2.0 (recommended)</option>
                  <option value="api">API Key</option>
                  <option value="service">Service Account</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Default Sheet Range</label>
                <input defaultValue="A:Z" style={monoInput} />
                <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 3 }}>Leave as A:Z to auto-detect data range</div>
              </div>
              <div>
                <label style={labelStyle}>Header Row</label>
                <select defaultValue="1" style={inputStyle}>
                  <option value="1">Row 1 (default)</option>
                  <option value="2">Row 2</option>
                  <option value="0">No header</option>
                </select>
              </div>
            </div>
          </ChartPanel>
        </div>
      )}

      {/* Save button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 8 }}>
        <SmallBtn>Reset to Defaults</SmallBtn>
        <button style={{
          padding: '9px 24px', fontSize: 13, fontWeight: 600, borderRadius: 8,
          background: 'linear-gradient(135deg, #10b981, #059669)', color: 'white',
          border: 'none', cursor: 'pointer', fontFamily: 'var(--font)',
          boxShadow: '0 1px 4px rgba(16,185,129,0.3)',
        }}>Save Settings</button>
      </div>
    </div>
  );
};

Object.assign(window, { SettingsView });
