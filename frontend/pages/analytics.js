import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import { useBusiness } from '../contexts/BusinessContext';

export default function Analytics() {
  const { businessId, selectedBusiness } = useBusiness();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState(30);

  useEffect(() => {
    if (businessId) {
      fetchAnalytics();
    }
  }, [businessId, dateRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/analytics/${businessId}/dashboard?days=${dateRange}`);
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
        setError(null);
      } else {
        setError('Failed to load analytics');
      }
    } catch (e) {
      setError('Could not connect to server');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value || 0);
  };

  const formatPercent = (value) => {
    return `${(value || 0).toFixed(1)}%`;
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Analytics</h1>
            <p className="text-white/60">
              Business Intelligence for {selectedBusiness?.name || 'Your Business'}
            </p>
          </div>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(parseInt(e.target.value))}
            className="glass-card px-4 py-2 bg-white/5 border border-white/20 rounded-lg"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-pulse text-white/60">Loading analytics...</div>
          </div>
        ) : error ? (
          <GlassCard className="p-6 text-center">
            <p className="text-red-400">{error}</p>
            <button onClick={fetchAnalytics} className="mt-4 px-4 py-2 bg-neon-blue/20 rounded-lg">
              Retry
            </button>
          </GlassCard>
        ) : dashboard ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <GlassCard className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white/60 text-sm">Total Calls</p>
                    <p className="text-3xl font-bold">{dashboard.metrics?.total_calls || 0}</p>
                    <p className="text-xs text-white/40">
                      {dashboard.metrics?.missed_calls || 0} missed
                    </p>
                  </div>
                  <span className="text-4xl">📞</span>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white/60 text-sm">Conversion Rate</p>
                    <p className="text-3xl font-bold text-neon-green">
                      {formatPercent(dashboard.metrics?.conversion_rate)}
                    </p>
                    <p className="text-xs text-white/40">
                      {dashboard.metrics?.appointments_booked || 0} appointments
                    </p>
                  </div>
                  <span className="text-4xl">📈</span>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white/60 text-sm">Revenue</p>
                    <p className="text-3xl font-bold text-neon-blue">
                      {formatCurrency(dashboard.metrics?.revenue)}
                    </p>
                    <p className="text-xs text-white/40">
                      Avg ticket: {formatCurrency(dashboard.metrics?.avg_ticket)}
                    </p>
                  </div>
                  <span className="text-4xl">💰</span>
                </div>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white/60 text-sm">Satisfaction</p>
                    <p className="text-3xl font-bold text-neon-purple">
                      {(dashboard.metrics?.customer_satisfaction || 0).toFixed(1)} / 5
                    </p>
                    <p className="text-xs text-white/40">
                      {dashboard.metrics?.appointments_completed || 0} completed jobs
                    </p>
                  </div>
                  <span className="text-4xl">⭐</span>
                </div>
              </GlassCard>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <GlassCard className="p-6">
                <h2 className="text-xl font-semibold mb-4">Technician Performance</h2>
                {dashboard.technician_performance?.length > 0 ? (
                  <div className="space-y-3">
                    {dashboard.technician_performance.map((tech, index) => (
                      <div key={tech.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            index === 0 ? 'bg-yellow-500/20' : 'bg-white/10'
                          }`}>
                            {index === 0 ? '🏆' : index + 1}
                          </div>
                          <div>
                            <p className="font-medium">{tech.name}</p>
                            <p className="text-xs text-white/50">{tech.jobs} jobs</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-neon-green">{formatCurrency(tech.revenue)}</p>
                          <p className="text-xs text-white/50">
                            {tech.rating?.toFixed(1) || 'N/A'} rating | {tech.on_time_rate?.toFixed(0) || 100}% on-time
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-white/50 text-center py-4">No technician data available</p>
                )}
              </GlassCard>

              <GlassCard className="p-6">
                <h2 className="text-xl font-semibold mb-4">Call Patterns</h2>
                {dashboard.call_patterns ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-white/60 text-sm">Peak Time</p>
                      <p className="text-xl font-semibold">{dashboard.call_patterns.busiest_period || 'N/A'}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-white/60 text-sm">Most Common Outcome</p>
                        <p className="font-medium">
                          {Object.entries(dashboard.call_patterns.calls_by_outcome || {})
                            .sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'}
                        </p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-white/60 text-sm">Top Service</p>
                        <p className="font-medium">
                          {Object.entries(dashboard.call_patterns.calls_by_service || {})
                            .sort((a, b) => b[1] - a[1])[0]?.[0] || 'General'}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-white/50 text-center py-4">No call pattern data available</p>
                )}
              </GlassCard>
            </div>

            <GlassCard className="p-6">
              <h2 className="text-xl font-semibold mb-4">AI Insights & Recommendations</h2>
              {dashboard.insights?.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {dashboard.insights.map((insight, index) => (
                    <div key={index} className={`p-4 rounded-lg ${
                      insight.priority === 1 ? 'bg-red-500/10 border border-red-500/30' :
                      insight.priority === 2 ? 'bg-yellow-500/10 border border-yellow-500/30' :
                      'bg-white/5 border border-white/10'
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-xs px-2 py-1 rounded ${
                          insight.category === 'operations' ? 'bg-blue-500/20' :
                          insight.category === 'team' ? 'bg-purple-500/20' :
                          insight.category === 'sales' ? 'bg-green-500/20' :
                          'bg-white/10'
                        }`}>
                          {insight.category}
                        </span>
                        {insight.priority === 1 && <span className="text-red-400 text-xs">High Priority</span>}
                      </div>
                      <h3 className="font-semibold mb-1">{insight.title}</h3>
                      <p className="text-sm text-white/60 mb-3">{insight.description}</p>
                      <ul className="text-xs text-white/50 space-y-1">
                        {insight.actions?.slice(0, 2).map((action, i) => (
                          <li key={i}>• {action}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-4">
                  More insights will appear as you receive more calls
                </p>
              )}
            </GlassCard>
          </>
        ) : null}
      </div>
    </Layout>
  );
}
