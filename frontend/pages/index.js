import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import GlassCard from '../components/GlassCard';
import TranscriptViewer from '../components/TranscriptViewer';
import { useBusiness } from '../contexts/BusinessContext';

export default function Dashboard() {
  const { businessId, selectedBusiness, loading: businessLoading } = useBusiness();
  const [stats, setStats] = useState({
    total_calls: 0,
    weekly_calls: 0,
    monthly_calls: 0,
    appointments_booked: 0,
    emergencies: 0,
    conversion_rate: 0
  });
  const [recentCalls, setRecentCalls] = useState([]);

  useEffect(() => {
    if (businessId) {
      fetchStats();
      fetchRecentCalls();
    }
  }, [businessId]);

  const fetchStats = async () => {
    try {
      const res = await fetch(`/api/stats/${businessId}`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.log('Stats not available yet');
    }
  };

  const fetchRecentCalls = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}/calls?limit=5`);
      if (res.ok) {
        const data = await res.json();
        setRecentCalls(data);
      }
    } catch (e) {
      console.log('Calls not available yet');
    }
  };

  return (
    <Layout title="Dashboard">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-white/60">
          {businessLoading ? 'Loading...' : (
            selectedBusiness ? `Viewing: ${selectedBusiness.name}` : 'Welcome to Cortana AI Voice System'
          )}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard 
          title="Total Calls" 
          value={stats.total_calls} 
          icon="📞"
        />
        <StatCard 
          title="This Week" 
          value={stats.weekly_calls} 
          change="+12% from last week"
          trend="up"
          icon="📈"
        />
        <StatCard 
          title="Appointments" 
          value={stats.appointments_booked} 
          icon="📅"
        />
        <StatCard 
          title="Conversion Rate" 
          value={`${stats.conversion_rate}%`} 
          change="+3.2%"
          trend="up"
          icon="🎯"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TranscriptViewer businessId={businessId} />

        <GlassCard>
          <h3 className="text-lg font-semibold mb-4">Recent Calls</h3>
          <div className="space-y-3">
            {recentCalls.length === 0 ? (
              <p className="text-white/40 text-center py-8">No calls yet</p>
            ) : (
              recentCalls.map((call, index) => (
                <div key={index} className="glass-panel p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{call.caller_number || 'Unknown'}</p>
                    <p className="text-sm text-white/50">
                      {call.timestamp ? new Date(call.timestamp).toLocaleString() : 'N/A'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      call.sentiment === 'positive' ? 'bg-green-500/20 text-green-400' :
                      call.sentiment === 'negative' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {call.sentiment || 'neutral'}
                    </span>
                    {call.booked_appointment && (
                      <span className="px-2 py-1 rounded-full text-xs bg-neon-blue/20 text-neon-blue">
                        Booked
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </Layout>
  );
}
