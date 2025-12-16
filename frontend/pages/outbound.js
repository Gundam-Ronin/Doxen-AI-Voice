import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';
import { useBusiness } from '../contexts/BusinessContext';

export default function Outbound() {
  const { businessId, selectedBusiness } = useBusiness();
  const [callQueue, setCallQueue] = useState([]);
  const [callTypes, setCallTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scheduling, setScheduling] = useState(false);
  const [formData, setFormData] = useState({
    customer_phone: '',
    customer_name: '',
    call_type: 'missed_call_followup',
    scheduled_time: '',
    priority: 5
  });

  useEffect(() => {
    fetchCallTypes();
  }, []);

  useEffect(() => {
    if (businessId) {
      fetchQueue();
    }
  }, [businessId]);

  const fetchCallTypes = async () => {
    try {
      const res = await fetch('/api/outbound/call-types');
      if (res.ok) {
        const data = await res.json();
        setCallTypes(data.call_types || []);
      }
    } catch (e) {
      console.error('Failed to load call types:', e);
    }
  };

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/outbound/${businessId}/queue`);
      if (res.ok) {
        const data = await res.json();
        setCallQueue(data.queue || []);
      }
    } catch (e) {
      console.error('Failed to load queue:', e);
    } finally {
      setLoading(false);
    }
  };

  const scheduleCall = async () => {
    if (!formData.customer_phone || !formData.customer_name) {
      alert('Please enter customer name and phone number');
      return;
    }
    setScheduling(true);
    try {
      const res = await fetch(`/api/outbound/${businessId}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        fetchQueue();
        setFormData({
          customer_phone: '',
          customer_name: '',
          call_type: 'missed_call_followup',
          scheduled_time: '',
          priority: 5
        });
      } else {
        alert('Failed to schedule call');
      }
    } catch (e) {
      alert('Error scheduling call');
    } finally {
      setScheduling(false);
    }
  };

  const processQueue = async () => {
    try {
      const res = await fetch(`/api/outbound/${businessId}/process-queue`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Processed ${data.processed} calls`);
        fetchQueue();
      }
    } catch (e) {
      alert('Error processing queue');
    }
  };

  const formatCallType = (type) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Outbound Calling</h1>
            <p className="text-white/60">
              AI-powered outbound calls for {selectedBusiness?.name || 'Your Business'}
            </p>
          </div>
          <GlassButton onClick={processQueue} disabled={callQueue.length === 0}>
            Process Queue ({callQueue.length})
          </GlassButton>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold mb-4">Schedule Outbound Call</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-1">Customer Name</label>
                <input
                  type="text"
                  value={formData.customer_name}
                  onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                  placeholder="John Smith"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Phone Number</label>
                <input
                  type="tel"
                  value={formData.customer_phone}
                  onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                  placeholder="+1 555-123-4567"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Call Type</label>
                <select
                  value={formData.call_type}
                  onChange={(e) => setFormData({ ...formData, call_type: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                >
                  {callTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Scheduled Time (optional)</label>
                <input
                  type="datetime-local"
                  value={formData.scheduled_time}
                  onChange={(e) => setFormData({ ...formData, scheduled_time: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Priority (1-10)</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-white/40 text-center">{formData.priority} (higher = more urgent)</p>
              </div>
              <GlassButton
                onClick={scheduleCall}
                disabled={scheduling}
                className="w-full"
              >
                {scheduling ? 'Scheduling...' : 'Schedule Call'}
              </GlassButton>
            </div>
          </GlassCard>

          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold mb-4">Call Queue</h2>
            {loading ? (
              <p className="text-white/50 text-center py-4">Loading queue...</p>
            ) : callQueue.length > 0 ? (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {callQueue.map((call, index) => (
                  <div key={index} className="p-4 bg-white/5 rounded-lg flex justify-between items-start">
                    <div>
                      <p className="font-medium">{call.customer_name}</p>
                      <p className="text-sm text-white/60">{call.customer_phone}</p>
                      <p className="text-xs text-white/40 mt-1">{formatCallType(call.call_type)}</p>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-1 rounded text-xs ${
                        call.priority >= 8 ? 'bg-red-500/20 text-red-400' :
                        call.priority >= 5 ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        Priority {call.priority}
                      </span>
                      {call.scheduled_time && (
                        <p className="text-xs text-white/40 mt-1">
                          {new Date(call.scheduled_time).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-white/50">
                <p className="text-4xl mb-2">📭</p>
                <p>No calls in queue</p>
              </div>
            )}
          </GlassCard>
        </div>

        <GlassCard className="p-6">
          <h2 className="text-xl font-semibold mb-4">Call Type Descriptions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { type: 'Missed Call Followup', desc: 'Follow up with customers who called but didnt connect', icon: '📞' },
              { type: 'Quote Reminder', desc: 'Remind customers about pending quotes', icon: '💰' },
              { type: 'Technician En Route', desc: 'Notify customers their technician is on the way', icon: '🚗' },
              { type: 'Review Request', desc: 'Ask for reviews after service completion', icon: '⭐' },
              { type: 'Appointment Reminder', desc: 'Confirm upcoming appointments', icon: '📅' },
              { type: 'Payment Reminder', desc: 'Remind about outstanding balances', icon: '💳' },
              { type: 'Contract Renewal', desc: 'Offer contract renewals with discounts', icon: '📝' },
              { type: 'Dead Lead Reactivation', desc: 'Re-engage old leads with new offers', icon: '🔄' },
              { type: 'Service Follow Up', desc: 'Check on customer satisfaction after service', icon: '✅' }
            ].map((item, index) => (
              <div key={index} className="p-4 bg-white/5 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{item.icon}</span>
                  <p className="font-medium">{item.type}</p>
                </div>
                <p className="text-sm text-white/60">{item.desc}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </Layout>
  );
}
