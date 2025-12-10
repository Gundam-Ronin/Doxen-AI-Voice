import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';
import GlowInput from '../components/GlowInput';

export default function Technicians() {
  const [technicians, setTechnicians] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingTech, setEditingTech] = useState(null);
  const [formData, setFormData] = useState({ name: '', phone: '', role: 'technician', skills: '' });
  const businessId = 1;

  useEffect(() => {
    fetchTechnicians();
  }, []);

  const fetchTechnicians = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}/technicians`);
      if (res.ok) {
        const data = await res.json();
        setTechnicians(data);
      }
    } catch (e) {
      console.log('Error fetching technicians');
    }
  };

  const handleSave = async () => {
    try {
      const skills = formData.skills.split(',').map(s => s.trim()).filter(Boolean);
      const payload = { ...formData, skills };
      
      const url = editingTech 
        ? `/api/technicians/${editingTech.id}`
        : `/api/businesses/${businessId}/technicians`;
      
      const res = await fetch(url, {
        method: editingTech ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        fetchTechnicians();
        closeForm();
      }
    } catch (e) {
      console.error('Error saving technician');
    }
  };

  const handleDelete = async (techId) => {
    if (!confirm('Are you sure you want to remove this technician?')) return;
    
    try {
      const res = await fetch(`/api/technicians/${techId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchTechnicians();
      }
    } catch (e) {
      console.error('Error deleting technician');
    }
  };

  const toggleAvailability = async (tech) => {
    try {
      await fetch(`/api/technicians/${tech.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_available: !tech.is_available })
      });
      fetchTechnicians();
    } catch (e) {
      console.error('Error updating availability');
    }
  };

  const openForm = (tech = null) => {
    if (tech) {
      setEditingTech(tech);
      setFormData({
        name: tech.name,
        phone: tech.phone,
        role: tech.role,
        skills: (tech.skills || []).join(', ')
      });
    } else {
      setEditingTech(null);
      setFormData({ name: '', phone: '', role: 'technician', skills: '' });
    }
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingTech(null);
    setFormData({ name: '', phone: '', role: 'technician', skills: '' });
  };

  return (
    <Layout title="Technicians">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">Technicians</h1>
          <p className="text-white/60">Manage your service team</p>
        </div>
        <GlassButton variant="primary" onClick={() => openForm()}>
          + Add Technician
        </GlassButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {technicians.length === 0 ? (
          <div className="col-span-full">
            <GlassCard className="text-center py-12">
              <p className="text-4xl mb-4">👷</p>
              <p className="text-white/60">No technicians yet. Add your first team member.</p>
            </GlassCard>
          </div>
        ) : (
          technicians.map((tech) => (
            <GlassCard key={tech.id}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-r from-neon-blue to-neon-purple flex items-center justify-center text-xl">
                    👷
                  </div>
                  <div>
                    <h3 className="font-semibold">{tech.name}</h3>
                    <p className="text-sm text-white/60 capitalize">{tech.role}</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleAvailability(tech)}
                  className={`px-3 py-1 rounded-full text-xs ${
                    tech.is_available 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {tech.is_available ? 'Available' : 'Unavailable'}
                </button>
              </div>

              <div className="glass-panel p-3 mb-4">
                <p className="text-xs text-white/50 mb-1">Phone</p>
                <p className="font-medium">{tech.phone}</p>
              </div>

              {tech.skills && tech.skills.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {tech.skills.map((skill, i) => (
                    <span key={i} className="text-xs px-2 py-1 bg-neon-teal/20 text-neon-teal rounded">
                      {skill}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <button 
                  onClick={() => openForm(tech)}
                  className="text-sm text-neon-blue hover:underline"
                >
                  Edit
                </button>
                <button 
                  onClick={() => handleDelete(tech.id)}
                  className="text-sm text-red-400 hover:underline"
                >
                  Remove
                </button>
              </div>
            </GlassCard>
          ))
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">
              {editingTech ? 'Edit Technician' : 'Add Technician'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Name</label>
                <GlowInput
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Phone</label>
                <GlowInput
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  placeholder="+1 (555) 123-4567"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="glow-input"
                >
                  <option value="technician">Technician</option>
                  <option value="senior_technician">Senior Technician</option>
                  <option value="manager">Manager</option>
                  <option value="dispatcher">Dispatcher</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Skills (comma-separated)</label>
                <GlowInput
                  value={formData.skills}
                  onChange={(e) => setFormData({...formData, skills: e.target.value})}
                  placeholder="Plumbing, HVAC, Electrical"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <GlassButton onClick={closeForm}>Cancel</GlassButton>
                <GlassButton variant="primary" onClick={handleSave}>Save</GlassButton>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
