import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Navigation, NavTab } from './components/Navigation';
import { DashboardPage } from './pages/DashboardPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { ChatPage } from './pages/ChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { VivaPage } from './pages/VivaPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { CircuitPage } from './pages/CircuitPage';
import { SketchPage } from './pages/SketchPage';
import { CodePage } from './pages/CodePage';
import { ReportsPage } from './pages/ReportsPage';
import { LabManualPage } from './pages/LabManualPage';
import { SystemStatus, Experiment } from './types';
import { fetchSystemStatus, fetchExperiments } from './lib/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExpNum, setSelectedExpNum] = useState<number>(1);
  const [chatExpContext, setChatExpContext] = useState<number | null>(null);

  const loadData = () => {
    fetchSystemStatus()
      .then((s) => setStatus(s))
      .catch((err) => console.warn('Backend server not responding yet:', err));

    fetchExperiments()
      .then((exps) => setExperiments(exps))
      .catch((err) => console.warn('Could not fetch experiments:', err));
  };

  useEffect(() => {
    loadData();
    // Poll system status every 10 seconds
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans select-none">
      <Header status={status} onRefreshStatus={loadData} />

      <div className="flex flex-1 overflow-hidden">
        <Navigation currentTab={currentTab} onSelectTab={setCurrentTab} />

        <main className="flex-1 overflow-y-auto bg-zinc-950">
          {currentTab === 'dashboard' && (
            <DashboardPage
              status={status}
              experiments={experiments}
              onSelectTab={setCurrentTab}
              onSelectExperiment={setSelectedExpNum}
            />
          )}

          {currentTab === 'experiments' && (
            <ExperimentsPage
              experiments={experiments}
              selectedExpNum={selectedExpNum}
              onSelectExpNum={setSelectedExpNum}
              onSelectTab={setCurrentTab}
              onSetChatContext={setChatExpContext}
            />
          )}

          {currentTab === 'chat' && (
            <ChatPage
              experiments={experiments}
              selectedExpContext={chatExpContext}
              onSetExpContext={setChatExpContext}
            />
          )}

          {currentTab === 'viva' && <VivaPage experiments={experiments} />}

          {currentTab === 'simulator' && <SimulatorPage experiments={experiments} />}

          {currentTab === 'circuit' && <CircuitPage />}

          {currentTab === 'sketch' && (
            <SketchPage
              onSelectTab={setCurrentTab}
              onSetChatContext={setChatExpContext}
            />
          )}

          {currentTab === 'code' && <CodePage experiments={experiments} />}

          {currentTab === 'reports' && <ReportsPage experiments={experiments} />}

          {currentTab === 'lab-manual' && <LabManualPage experiments={experiments} />}

          {currentTab === 'settings' && (
            <SettingsPage status={status} onRefreshStatus={loadData} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
