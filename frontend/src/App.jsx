import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShieldAlert, BarChart3, Activity } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import CaseDetail from './pages/CaseDetail';
import Evaluation from './pages/Evaluation';
import SimulationControls from './components/SimulationControls';

function Sidebar() {
  const location = useLocation();
  const links = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/cases', icon: ShieldAlert, label: 'Risk Cases' },
    { path: '/evaluation', icon: BarChart3, label: 'Evaluation' }
  ];

  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col h-screen fixed left-0 top-0">
      <div className="p-4 border-b border-gray-700 flex items-center gap-2">
        <Activity className="text-brand-500" />
        <h1 className="text-xl font-bold text-gray-100 tracking-tight">Sentinel Mesh</h1>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {links.map((link) => {
          const active = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
          return (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                active ? 'bg-brand-600/20 text-brand-500 font-medium' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
              }`}
            >
              <link.icon size={18} />
              {link.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-700">
        <SimulationControls />
      </div>
    </aside>
  );
}

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-gray-900 text-gray-300">
        <Sidebar />
        <main className="flex-1 ml-64 p-8 overflow-y-auto h-screen">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cases" element={<Dashboard />} />
            <Route path="/cases/:caseId" element={<CaseDetail />} />
            <Route path="/evaluation" element={<Evaluation />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;