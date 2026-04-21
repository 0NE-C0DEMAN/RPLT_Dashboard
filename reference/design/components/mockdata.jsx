// Mock data generator for RPLT signals
const generateSignal = (n, fn) => Array.from({length: n}, (_, i) => fn(i, n));

const MOCK = {
  time: generateSignal(300, (i, n) => +(i * 0.37 / n * 0.12).toFixed(5)),
  
  load: generateSignal(300, (i, n) => {
    const t = i / n;
    const impact = Math.exp(-((t - 0.25) ** 2) / 0.003) * 2219;
    const rebound = Math.exp(-((t - 0.55) ** 2) / 0.008) * -380;
    return +(impact + rebound + (Math.random() - 0.5) * 25).toFixed(1);
  }),
  
  disp: generateSignal(300, (i, n) => {
    const t = i / n;
    const d = (1 - Math.exp(-t * 15)) * 7.2 * Math.exp(-((t - 0.4)**2)/0.08) + 
              Math.sin(t * Math.PI * 8) * 0.8 * Math.exp(-t * 6);
    return +(d + (Math.random() - 0.5) * 0.15).toFixed(4);
  }),
  
  velocity: generateSignal(300, (i, n) => {
    const t = i / n;
    const v = Math.cos(t * Math.PI * 8) * 0.32 * Math.exp(-t * 4) + 
              Math.exp(-((t - 0.25)**2)/0.002) * 0.55;
    return +(v + (Math.random() - 0.5) * 0.015).toFixed(4);
  }),
  
  accel: generateSignal(300, (i, n) => {
    const t = i / n;
    return +(-Math.sin(t * Math.PI * 8) * 85 * Math.exp(-t * 4) + 
              Math.exp(-((t - 0.25)**2)/0.001) * 420 + 
              (Math.random() - 0.5) * 8).toFixed(2);
  }),
  
  accelSmoothed: generateSignal(300, (i, n) => {
    const t = i / n;
    return +(-Math.sin(t * Math.PI * 8) * 80 * Math.exp(-t * 4) + 
              Math.exp(-((t - 0.25)**2)/0.0015) * 400).toFixed(2);
  }),
  
  fma: generateSignal(300, (i, n) => {
    const t = i / n;
    return +(Math.exp(-((t - 0.27)**2)/0.004) * 480 + (Math.random()-0.5)*10).toFixed(2);
  }),
  
  fkx: generateSignal(300, (i, n) => {
    const t = i / n;
    return +(Math.exp(-((t - 0.35)**2)/0.01) * 15.8 + (Math.random()-0.5)*2).toFixed(3);
  }),
  
  totalForce: generateSignal(300, (i, n) => {
    const t = i / n;
    return +(Math.exp(-((t - 0.28)**2)/0.005) * 2700 + (Math.random()-0.5)*30).toFixed(1);
  }),
};

// Cycle data (3 test cycles)
MOCK.cycles = [
  { id: 1, peakLoad: 2219, maxDisp: 7.18, setDisp: 1.42, peakVel: 0.55, duration: 0.037 },
  { id: 2, peakLoad: 1876, maxDisp: 5.93, setDisp: 2.85, peakVel: 0.48, duration: 0.034 },
  { id: 3, peakLoad: 2401, maxDisp: 8.21, setDisp: 4.27, peakVel: 0.61, duration: 0.039 },
];

// KPIs
MOCK.kpis = {
  peakLoad: { value: '2,219', unit: 'kN', label: 'Peak Load' },
  maxDisp: { value: '7.18', unit: 'mm', label: 'Max Displacement' },
  setDisp: { value: '1.42', unit: 'mm', label: 'Set Displacement' },
  peakVel: { value: '0.55', unit: 'm/s', label: 'Peak Velocity' },
  samples: { value: '6,315', unit: '', label: 'Samples' },
  duration: { value: '0.037', unit: 's', label: 'Impact Duration' },
};

// Test project info
MOCK.project = {
  name: 'Bridge Foundation B-14',
  file: 'RPLTResults (1).xlsx',
  pile: 'TP-03',
  date: '2024-11-18',
  operator: 'J. Martinez',
  samples: 6315,
  cols: 3,
  mass: '12,000',
  stiffness: '1,397,000',
};

Object.assign(window, { MOCK, generateSignal });
