import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';
import GlowInput from '../components/GlowInput';

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

export default function Settings() {
  const [business, setBusiness] = useState({
    name: '',
    phone_number: '',
    location: '',
    services: [],
    pricing: {},
    hours: {}
  });
  const [newService, setNewService] = useState('');
  const [saved, setSaved] = useState(false);
  const businessId = 1;

  useEffect(() => {
    fetchBusiness();
  }, []);

  const fetchBusiness = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}`);
      if (res.ok) {
        const data = await res.json();
        setBusiness({
          name: data.name || '',
          phone_number: data.phone_number || '',
          location: data.location || '',
          services: data.services || [],
          pricing: data.pricing || {},
          hours: data.hours || {}
        });
      }
    } catch (e) {
      console.log('Error fetching business');
    }
  };

  const handleSave = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(business)
      });
      
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (e) {
      console.error('Error saving settings');
    }
  };

  const addService = () => {
    if (newService.trim()) {
      setBusiness({
        ...business,
        services: [...business.services, newService.trim()]
      });
      setNewService('');
    }
  };

  const removeService = (index) => {
    setBusiness({
      ...business,
      services: business.services.filter((_, i) => i !== index)
    });
  };

  const updateHours = (day, field, value) => {
    setBusiness({
      ...business,
      hours: {
        ...business.hours,
        [day]: {
          ...business.hours[day],
          [field]: value
        }
      }
    });
  };

  const toggleDay = (day) => {
    if (business.hours[day]) {
      const newHours = { ...business.hours };
      delete newHours[day];
      setBusiness({ ...business, hours: newHours });
    } else {
      setBusiness({
        ...business,
        hours: {
          ...business.hours,
          [day]: { open: '09:00', close: '17:00' }
        }
      });
    }
  };

  return (
    <Layout title="Settings">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Business Settings</h1>
        <p className="text-white/60">Configure your business information</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Business Information</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Business Name</label>
                <GlowInput
                  value={business.name}
                  onChange={(e) => setBusiness({...business, name: e.target.value})}
                  placeholder="Your Business Name"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Phone Number</label>
                <GlowInput
                  value={business.phone_number}
                  onChange={(e) => setBusiness({...business, phone_number: e.target.value})}
                  placeholder="+1 (555) 123-4567"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Location / Service Area</label>
                <GlowInput
                  value={business.location}
                  onChange={(e) => setBusiness({...business, location: e.target.value})}
                  placeholder="City, State or Service Area"
                />
              </div>
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Services Offered</h3>
            <div className="flex gap-2 mb-4">
              <GlowInput
                value={newService}
                onChange={(e) => setNewService(e.target.value)}
                placeholder="Add a service..."
                onKeyPress={(e) => e.key === 'Enter' && addService()}
              />
              <GlassButton onClick={addService}>Add</GlassButton>
            </div>
            <div className="flex flex-wrap gap-2">
              {business.services.map((service, index) => (
                <span 
                  key={index}
                  className="px-3 py-1 bg-neon-blue/20 text-neon-blue rounded-full text-sm flex items-center gap-2"
                >
                  {service}
                  <button 
                    onClick={() => removeService(index)}
                    className="text-white/60 hover:text-white"
                  >
                    ×
                  </button>
                </span>
              ))}
              {business.services.length === 0 && (
                <p className="text-white/40 text-sm">No services added yet</p>
              )}
            </div>
          </GlassCard>
        </div>

        <div className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Business Hours</h3>
            <div className="space-y-3">
              {DAYS.map((day) => (
                <div key={day} className="flex items-center gap-4">
                  <label className="flex items-center gap-2 w-28">
                    <input
                      type="checkbox"
                      checked={!!business.hours[day]}
                      onChange={() => toggleDay(day)}
                      className="w-4 h-4 rounded"
                    />
                    <span className="capitalize text-sm">{day}</span>
                  </label>
                  {business.hours[day] ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="time"
                        value={business.hours[day]?.open || '09:00'}
                        onChange={(e) => updateHours(day, 'open', e.target.value)}
                        className="glow-input !py-1 !px-2 w-28"
                      />
                      <span className="text-white/60">to</span>
                      <input
                        type="time"
                        value={business.hours[day]?.close || '17:00'}
                        onChange={(e) => updateHours(day, 'close', e.target.value)}
                        className="glow-input !py-1 !px-2 w-28"
                      />
                    </div>
                  ) : (
                    <span className="text-white/40 text-sm">Closed</span>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Subscription</h3>
            <div className="glass-panel p-4 mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Pro Plan</p>
                  <p className="text-sm text-white/60">Unlimited calls, all features</p>
                </div>
                <span className="text-neon-teal font-bold">Active</span>
              </div>
            </div>
            <GlassButton className="w-full">Manage Subscription</GlassButton>
          </GlassCard>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <GlassButton variant="primary" onClick={handleSave}>
          {saved ? '✓ Saved!' : 'Save All Changes'}
        </GlassButton>
      </div>
    </Layout>
  );
}
