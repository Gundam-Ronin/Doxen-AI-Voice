import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';
import { useBusiness } from '../contexts/BusinessContext';

export default function Quotes() {
  const { businessId, selectedBusiness } = useBusiness();
  const [catalog, setCatalog] = useState(null);
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_phone: '',
    service_type: '',
    is_emergency: false,
    promo_code: ''
  });

  useEffect(() => {
    if (businessId) {
      fetchCatalog();
    }
  }, [businessId]);

  const fetchCatalog = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/quotes/${businessId}/pricing-catalog`);
      if (res.ok) {
        const data = await res.json();
        setCatalog(data);
      }
    } catch (e) {
      console.error('Failed to load catalog:', e);
    } finally {
      setLoading(false);
    }
  };

  const generateQuote = async () => {
    if (!formData.customer_name || !formData.service_type) {
      alert('Please enter customer name and service type');
      return;
    }
    setGenerating(true);
    try {
      const res = await fetch(`/api/quotes/${businessId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        const data = await res.json();
        setQuote(data);
      } else {
        alert('Failed to generate quote');
      }
    } catch (e) {
      alert('Error generating quote');
    } finally {
      setGenerating(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value || 0);
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Quote Generator</h1>
          <p className="text-white/60">
            AI-powered quotes for {selectedBusiness?.name || 'Your Business'}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold mb-4">Generate Quote</h2>
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
                  placeholder="(555) 123-4567"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Service Type</label>
                <select
                  value={formData.service_type}
                  onChange={(e) => setFormData({ ...formData, service_type: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                >
                  <option value="">Select a service...</option>
                  {catalog?.services?.map((service, index) => (
                    <option key={index} value={service.service}>
                      {service.service} ({formatCurrency(service.base_price)})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="emergency"
                  checked={formData.is_emergency}
                  onChange={(e) => setFormData({ ...formData, is_emergency: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="emergency" className="text-sm text-white/60">Emergency Service</label>
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-1">Promo Code (optional)</label>
                <input
                  type="text"
                  value={formData.promo_code}
                  onChange={(e) => setFormData({ ...formData, promo_code: e.target.value })}
                  className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg focus:border-neon-blue focus:outline-none"
                  placeholder="SAVE10"
                />
              </div>
              <GlassButton
                onClick={generateQuote}
                disabled={generating}
                className="w-full"
              >
                {generating ? 'Generating...' : 'Generate Quote'}
              </GlassButton>
            </div>
          </GlassCard>

          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold mb-4">Quote Result</h2>
            {quote ? (
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-white/60">Quote #{quote.quote_id}</p>
                    <p className="font-medium">{quote.customer_name}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs ${
                    quote.quote_type === 'instant' ? 'bg-green-500/20 text-green-400' :
                    quote.quote_type === 'range' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>
                    {quote.quote_type.replace('_', ' ').toUpperCase()}
                  </span>
                </div>

                <div className="border-t border-white/10 pt-4">
                  <p className="text-lg font-semibold mb-2">{quote.service_type}</p>
                  <div className="space-y-2">
                    {quote.line_items?.map((item, index) => (
                      <div key={index} className={`flex justify-between text-sm ${item.is_optional ? 'text-white/50' : ''}`}>
                        <span>{item.description} {item.is_optional && '(optional)'}</span>
                        <span>{formatCurrency(item.total)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-white/10 pt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Subtotal</span>
                    <span>{formatCurrency(quote.subtotal)}</span>
                  </div>
                  {quote.discount > 0 && (
                    <div className="flex justify-between text-sm text-green-400">
                      <span>Discount</span>
                      <span>-{formatCurrency(quote.discount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm">
                    <span>Tax</span>
                    <span>{formatCurrency(quote.tax)}</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t border-white/10 pt-2">
                    <span>Total</span>
                    <span className="text-neon-green">{formatCurrency(quote.total)}</span>
                  </div>
                </div>

                {quote.low_estimate && quote.high_estimate && (
                  <div className="p-3 bg-white/5 rounded-lg text-sm">
                    <p className="text-white/60">Price Range: {formatCurrency(quote.low_estimate)} - {formatCurrency(quote.high_estimate)}</p>
                  </div>
                )}

                <div className="p-3 bg-neon-blue/10 rounded-lg border border-neon-blue/30">
                  <p className="text-sm font-medium">Voice Response:</p>
                  <p className="text-sm text-white/80 mt-1">{quote.voice_response}</p>
                </div>

                <p className="text-xs text-white/40">{quote.notes}</p>
                <p className="text-xs text-white/40">{quote.terms}</p>
              </div>
            ) : (
              <div className="text-center py-12 text-white/50">
                <p>Fill out the form to generate a quote</p>
              </div>
            )}
          </GlassCard>
        </div>

        <GlassCard className="p-6">
          <h2 className="text-xl font-semibold mb-4">Pricing Catalog - {catalog?.industry?.toUpperCase() || 'Loading...'}</h2>
          {loading ? (
            <p className="text-white/50 text-center py-4">Loading catalog...</p>
          ) : catalog?.services?.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {catalog.services.map((service, index) => (
                <div key={index} className="p-4 bg-white/5 rounded-lg">
                  <p className="font-medium">{service.service}</p>
                  <p className="text-2xl font-bold text-neon-blue">{formatCurrency(service.base_price)}</p>
                  <p className="text-xs text-white/50">
                    Range: {formatCurrency(service.low_estimate)} - {formatCurrency(service.high_estimate)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-white/50 text-center py-4">No pricing data available</p>
          )}
        </GlassCard>
      </div>
    </Layout>
  );
}
