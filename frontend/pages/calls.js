import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import TranscriptViewer from '../components/TranscriptViewer';
import { useBusiness } from '../contexts/BusinessContext';

export default function Calls() {
  const { selectedBusiness } = useBusiness();
  const [calls, setCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [activeCalls, setActiveCalls] = useState([]);
  const businessId = selectedBusiness?.id || 1;

  useEffect(() => {
    fetchCalls();
    fetchActiveCalls();
    const interval = setInterval(fetchActiveCalls, 5000);
    return () => clearInterval(interval);
  }, [businessId]);

  const fetchCalls = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}/calls?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setCalls(data);
      }
    } catch (e) {
      console.log('Error fetching calls');
    }
  };

  const fetchActiveCalls = async () => {
    try {
      const res = await fetch(`/api/stream/active-calls/${businessId}`);
      if (res.ok) {
        const data = await res.json();
        setActiveCalls(data.active_calls || []);
      }
    } catch (e) {
      console.log('Error fetching active calls');
    }
  };

  return (
    <Layout title="Calls">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Call Center</h1>
        <p className="text-white/60">Monitor live and historical calls</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TranscriptViewer businessId={businessId} />
        </div>

        <div className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              Active Calls ({activeCalls.length})
            </h3>
            <div className="space-y-3">
              {activeCalls.length === 0 ? (
                <p className="text-white/40 text-center py-4">No active calls</p>
              ) : (
                activeCalls.map((call, index) => (
                  <div key={index} className="glass-panel p-3">
                    <p className="font-medium">{call.caller_number}</p>
                    <p className="text-xs text-white/50">
                      Started: {new Date(call.started_at).toLocaleTimeString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Call History</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {calls.map((call, index) => (
                <div 
                  key={index} 
                  className="glass-panel p-3 cursor-pointer hover:bg-white/10"
                  onClick={() => setSelectedCall(call)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-sm">{call.caller_number || 'Unknown'}</p>
                      <p className="text-xs text-white/50">
                        {call.timestamp ? new Date(call.timestamp).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      {call.is_emergency && (
                        <span className="text-xs px-2 py-1 bg-red-500/20 text-red-400 rounded">🚨</span>
                      )}
                      {call.booked_appointment && (
                        <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded">📅</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      {selectedCall && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold">Call Details</h2>
              <button 
                onClick={() => setSelectedCall(null)}
                className="text-white/60 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-panel p-3">
                  <p className="text-xs text-white/50">Caller</p>
                  <p className="font-medium">{selectedCall.caller_number}</p>
                </div>
                <div className="glass-panel p-3">
                  <p className="text-xs text-white/50">Time</p>
                  <p className="font-medium">{new Date(selectedCall.timestamp).toLocaleString()}</p>
                </div>
                <div className="glass-panel p-3">
                  <p className="text-xs text-white/50">Sentiment</p>
                  <p className="font-medium capitalize">{selectedCall.sentiment || 'N/A'}</p>
                </div>
                <div className="glass-panel p-3">
                  <p className="text-xs text-white/50">Disposition</p>
                  <p className="font-medium capitalize">{selectedCall.disposition || 'N/A'}</p>
                </div>
              </div>
              {selectedCall.summary && (
                <div className="glass-panel p-4">
                  <p className="text-xs text-white/50 mb-2">Summary</p>
                  <p>{selectedCall.summary}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
