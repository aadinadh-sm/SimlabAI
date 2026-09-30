import React, { useState } from 'react';
import {
  FileText,
  Download,
  Copy,
  Check,
  Printer,
  Sparkles,
  BookOpen
} from 'lucide-react';
import { Experiment } from '../types';

interface ReportsPageProps {
  experiments: Experiment[];
}

export const ReportsPage: React.FC<ReportsPageProps> = ({ experiments }) => {
  const [selectedExp, setSelectedExp] = useState<number>(1);
  const [studentName, setStudentName] = useState<string>('Student');
  const [registerNum, setRegisterNum] = useState<string>('23EEP001');
  const [copied, setCopied] = useState<boolean>(false);

  const expData = experiments.find((e) => e.exp_number === selectedExp);

  const reportMarkdown = `# EXPERIMENT RECORD: EXP-${selectedExp}
## ${expData?.title || 'Simulation Lab Experiment'}

**Institution:** APJ Abdul Kalam Technological University (Affiliated)
**Department:** Electrical & Electronics Engineering
**Course:** 23EEP20B - Simulation Lab
**Student Name:** ${studentName}
**Register Number:** ${registerNum}
**Date:** ${new Date().toLocaleDateString()}

---

### 1. AIM
${expData?.aim || 'To simulate the circuit according to specifications.'}

### 2. APPARATUS / SOFTWARE REQUIRED
${expData?.software || 'PySpice, Ngspice, Python 3.x, Multisim'}

### 3. THEORY & PRINCIPLES
${expData?.tags.join(', ') || 'Circuit Simulation Principles'}
The circuit operation is analyzed using nodal analysis, time-domain transient differential equations, and semiconductor physical models per standard syllabus guidelines.

### 4. DOCUMENTED PROCEDURE
${expData?.procedure || 'Follow standard lab procedure as outlined in manual.'}

### 5. SIMULATION PARAMETERS & CODE
\`\`\`python
${expData?.code_sample || '# Circuit simulation parameters initialized per manual'}
\`\`\`

### 6. OBSERVATION & RESULT
${expData?.result || 'The circuit was simulated and observed in accordance with theoretical principles.'}

---
*Generated offline by SIMLAB AI - Your Offline Simulation Lab Copilot*
`;

  const handleCopy = () => {
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Exp_${selectedExp}_Lab_Record.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 select-text">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <FileText className="w-5 h-5 text-emerald-400" />
            <span>Lab Record & Report Generator</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Export complete academic experiment records with Aim, Theory, Procedure, Circuit Parameters, and Results.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs font-mono border border-zinc-800 transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center space-x-1 px-3.5 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-xs font-mono transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .MD</span>
          </button>
        </div>
      </div>

      {/* Inputs */}
      <div className="p-4 rounded-lg bg-zinc-900/70 border border-zinc-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div>
          <label className="text-zinc-500 block mb-1">SELECT EXPERIMENT:</label>
          <select
            value={selectedExp}
            onChange={(e) => setSelectedExp(parseInt(e.target.value))}
            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-700"
          >
            {experiments.map((e) => (
              <option key={e.exp_number} value={e.exp_number}>
                Exp {e.exp_number}: {e.title.slice(0, 30)}...
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-zinc-500 block mb-1">STUDENT NAME:</label>
          <input
            type="text"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-700 font-sans"
          />
        </div>

        <div>
          <label className="text-zinc-500 block mb-1">REGISTER NUMBER:</label>
          <input
            type="text"
            value={registerNum}
            onChange={(e) => setRegisterNum(e.target.value)}
            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-700"
          />
        </div>
      </div>

      {/* Report Preview */}
      <div className="p-6 rounded-lg bg-zinc-900/40 border border-zinc-800 text-xs font-mono text-zinc-300 space-y-4 whitespace-pre-wrap leading-relaxed shadow-sm">
        {reportMarkdown}
      </div>
    </div>
  );
};
