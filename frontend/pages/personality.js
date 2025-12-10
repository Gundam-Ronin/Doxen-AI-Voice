import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';

const PERSONALITY_TEMPLATES = [
  { id: 'friendly', name: 'Friendly', icon: '😊', description: 'Warm, enthusiastic, and conversational' },
  { id: 'professional', name: 'Professional', icon: '💼', description: 'Formal, efficient, and business-like' },
  { id: 'empathetic', name: 'Empathetic', icon: '💝', description: 'Understanding and patient' },
  { id: 'energetic', name: 'Energetic', icon: '⚡', description: 'Upbeat, enthusiastic, and positive' },
  { id: 'technical', name: 'Technical', icon: '🔧', description: 'Knowledgeable and detail-oriented' },
];

export default function Personality() {
  const [selectedTemplate, setSelectedTemplate] = useState('friendly');
  const [customRules, setCustomRules] = useState('');
  const [greeting, setGreeting] = useState('Thank you for calling! How can I help you today?');
  const [closing, setClosing] = useState('Thank you for calling! Have a wonderful day.');
  const [saved, setSaved] = useState(false);
  const businessId = 1;

  useEffect(() => {
    fetchPersonality();
  }, []);

  const fetchPersonality = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.ai_personality) {
          setCustomRules(data.ai_personality);
        }
      }
    } catch (e) {
      console.log('Error fetching personality');
    }
  };

  const handleSave = async () => {
    try {
      const res = await fetch(`/api/businesses/${businessId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ai_personality: customRules })
      });
      
      if (res.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (e) {
      console.error('Error saving personality');
    }
  };

  return (
    <Layout title="Personality">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">AI Personality</h1>
        <p className="text-white/60">Customize how Cortana interacts with your customers</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Personality Template</h3>
            <div className="grid grid-cols-2 gap-3">
              {PERSONALITY_TEMPLATES.map((template) => (
                <div
                  key={template.id}
                  onClick={() => setSelectedTemplate(template.id)}
                  className={`glass-panel p-4 cursor-pointer transition-all ${
                    selectedTemplate === template.id 
                      ? 'border-neon-blue bg-neon-blue/10' 
                      : 'hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{template.icon}</span>
                    <span className="font-medium">{template.name}</span>
                  </div>
                  <p className="text-xs text-white/60">{template.description}</p>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Greeting & Closing</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Greeting Message</label>
                <textarea
                  value={greeting}
                  onChange={(e) => setGreeting(e.target.value)}
                  className="glow-input min-h-[80px] resize-none"
                  placeholder="How Cortana greets callers..."
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Closing Message</label>
                <textarea
                  value={closing}
                  onChange={(e) => setClosing(e.target.value)}
                  className="glow-input min-h-[80px] resize-none"
                  placeholder="How Cortana ends calls..."
                />
              </div>
            </div>
          </GlassCard>
        </div>

        <div className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold mb-4">Custom Rules</h3>
            <p className="text-sm text-white/60 mb-4">
              Add specific instructions for how Cortana should behave
            </p>
            <textarea
              value={customRules}
              onChange={(e) => setCustomRules(e.target.value)}
              className="glow-input min-h-[300px] resize-none"
              placeholder="Enter custom personality rules...

Examples:
- Always mention our 24/7 emergency service
- Offer a 10% discount for first-time customers
- Prioritize same-day appointments when available
- Always ask for the customer's address
- If the caller sounds frustrated, offer to escalate to a manager"
            />
          </GlassCard>

          <div className="flex gap-3 justify-end">
            <GlassButton onClick={() => setCustomRules('')}>Reset</GlassButton>
            <GlassButton variant="primary" onClick={handleSave}>
              {saved ? '✓ Saved!' : 'Save Changes'}
            </GlassButton>
          </div>
        </div>
      </div>

      <GlassCard className="mt-6">
        <h3 className="text-lg font-semibold mb-4">Preview</h3>
        <div className="glass-panel p-4 space-y-4">
          <div className="transcript-bubble transcript-cortana">
            <p className="text-xs text-white/50 mb-1">🤖 Cortana</p>
            <p>{greeting}</p>
          </div>
          <div className="transcript-bubble transcript-customer">
            <p className="text-xs text-white/50 mb-1">👤 Customer</p>
            <p>Hi, I need a plumber for a leaky faucet.</p>
          </div>
          <div className="transcript-bubble transcript-cortana">
            <p className="text-xs text-white/50 mb-1">🤖 Cortana</p>
            <p>I'd be happy to help you with that leaky faucet! Let me check our availability for you. Can I get your address to find the best technician in your area?</p>
          </div>
        </div>
      </GlassCard>
    </Layout>
  );
}
