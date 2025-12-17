import { useState, useEffect } from 'react';
import Layout from '../components/Layout';

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [hoveredPlan, setHoveredPlan] = useState(null);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const res = await fetch('/api/billing/plans');
      if (res.ok) {
        const data = await res.json();
        setPlans(data.plans || []);
      }
    } catch (e) {
      console.error('Failed to load plans:', e);
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (plan) => {
    if (billingCycle === 'annual') {
      return plan.annual_monthly_price;
    }
    return plan.monthly_price;
  };

  const getPlanGradient = (tier) => {
    const gradients = {
      starter: 'from-blue-500/20 via-cyan-500/10 to-transparent',
      pro: 'from-purple-500/20 via-pink-500/10 to-transparent',
      elite: 'from-amber-500/20 via-orange-500/10 to-transparent',
      enterprise: 'from-emerald-500/20 via-teal-500/10 to-transparent'
    };
    return gradients[tier] || gradients.starter;
  };

  const getPlanBorder = (tier) => {
    const borders = {
      starter: 'border-blue-500/30 hover:border-blue-400/60',
      pro: 'border-purple-500/30 hover:border-purple-400/60',
      elite: 'border-amber-500/30 hover:border-amber-400/60',
      enterprise: 'border-emerald-500/30 hover:border-emerald-400/60'
    };
    return borders[tier] || borders.starter;
  };

  const getPlanAccent = (tier) => {
    const accents = {
      starter: 'text-blue-400',
      pro: 'text-purple-400',
      elite: 'text-amber-400',
      enterprise: 'text-emerald-400'
    };
    return accents[tier] || accents.starter;
  };

  return (
    <Layout>
      <div className="min-h-screen py-12 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{animationDelay: '1s'}} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl animate-pulse" style={{animationDelay: '2s'}} />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent animate-gradient">
              Enterprise AI for Home Services
            </h1>
            <p className="text-xl text-white/60 max-w-2xl mx-auto mb-8">
              Replace your $4,000/month receptionist. Never miss a call. Convert 35% more leads.
            </p>

            <div className="inline-flex items-center gap-4 p-1 bg-white/5 backdrop-blur-xl rounded-full border border-white/10">
              <button
                onClick={() => setBillingCycle('monthly')}
                className={`px-6 py-2 rounded-full transition-all duration-300 ${
                  billingCycle === 'monthly' 
                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-purple-500/25' 
                    : 'text-white/60 hover:text-white'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingCycle('annual')}
                className={`px-6 py-2 rounded-full transition-all duration-300 flex items-center gap-2 ${
                  billingCycle === 'annual' 
                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-purple-500/25' 
                    : 'text-white/60 hover:text-white'
                }`}
              >
                Annual
                <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                  Save 17%
                </span>
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {plans.map((plan, index) => (
                <div
                  key={plan.tier}
                  className={`relative group transition-all duration-500 ${
                    hoveredPlan === plan.tier ? 'scale-105 z-10' : 'scale-100'
                  }`}
                  onMouseEnter={() => setHoveredPlan(plan.tier)}
                  onMouseLeave={() => setHoveredPlan(null)}
                  style={{animationDelay: `${index * 100}ms`}}
                >
                  {plan.tier === 'pro' && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full text-sm font-medium text-white shadow-lg shadow-purple-500/30 z-20">
                      Most Popular
                    </div>
                  )}

                  <div className={`relative h-full p-6 rounded-2xl border backdrop-blur-xl bg-white/5 ${getPlanBorder(plan.tier)} transition-all duration-300 overflow-hidden`}>
                    <div className={`absolute inset-0 bg-gradient-to-b ${getPlanGradient(plan.tier)} opacity-50 group-hover:opacity-100 transition-opacity duration-300`} />
                    
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-white/50 to-transparent animate-shimmer" />
                    </div>

                    <div className="relative z-10">
                      <h3 className={`text-2xl font-bold mb-2 ${getPlanAccent(plan.tier)}`}>
                        {plan.name}
                      </h3>
                      
                      <div className="flex items-baseline gap-1 mb-4">
                        <span className="text-4xl font-bold text-white">
                          ${formatPrice(plan).toLocaleString()}
                        </span>
                        <span className="text-white/40">/mo</span>
                      </div>

                      {billingCycle === 'annual' && (
                        <p className="text-sm text-green-400 mb-4">
                          Save ${plan.annual_savings?.toLocaleString()}/year
                        </p>
                      )}

                      <p className="text-sm text-white/60 mb-6 min-h-[40px]">
                        {plan.description}
                      </p>

                      <button className={`w-full py-3 rounded-xl font-medium transition-all duration-300 ${
                        plan.tier === 'pro'
                          ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50'
                          : 'bg-white/10 text-white hover:bg-white/20 border border-white/10'
                      }`}>
                        {plan.tier === 'enterprise' ? 'Contact Sales' : 'Get Started'}
                      </button>

                      <div className="mt-6 space-y-3">
                        {plan.features?.slice(0, 8).map((feature, i) => (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <svg className={`w-5 h-5 ${getPlanAccent(plan.tier)} flex-shrink-0 mt-0.5`} fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                            <span className="text-white/70">{feature}</span>
                          </div>
                        ))}
                      </div>

                      <div className="mt-6 pt-6 border-t border-white/10">
                        <p className="text-xs text-white/40 mb-2">Usage Limits</p>
                        <div className="space-y-2 text-xs">
                          <div className="flex justify-between text-white/60">
                            <span>Monthly Minutes</span>
                            <span className="font-medium text-white/80">
                              {plan.limits?.monthly_minutes === -1 ? 'Unlimited' : plan.limits?.monthly_minutes?.toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between text-white/60">
                            <span>Locations</span>
                            <span className="font-medium text-white/80">
                              {plan.limits?.locations === -1 ? 'Unlimited' : plan.limits?.locations}
                            </span>
                          </div>
                          <div className="flex justify-between text-white/60">
                            <span>Technicians</span>
                            <span className="font-medium text-white/80">
                              {plan.limits?.technicians === -1 ? 'Unlimited' : plan.limits?.technicians}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-16 text-center">
            <div className="inline-flex flex-wrap justify-center gap-6 px-8 py-4 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10">
              {[
                { icon: '🏆', text: 'Replace $4K/mo employee' },
                { icon: '📈', text: '35% more conversions' },
                { icon: '📞', text: 'Zero missed calls' },
                { icon: '⚡', text: 'Instant AI quotes' },
                { icon: '🔄', text: 'Automated follow-ups' }
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-white/70">
                  <span className="text-xl">{item.icon}</span>
                  <span className="text-sm">{item.text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-16 max-w-3xl mx-auto">
            <div className="p-8 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 backdrop-blur-xl rounded-2xl border border-white/10">
              <h3 className="text-2xl font-bold text-center mb-6">ROI Calculator</h3>
              <div className="grid grid-cols-3 gap-6 text-center">
                <div>
                  <p className="text-4xl font-bold text-green-400">$1,750</p>
                  <p className="text-sm text-white/60 mt-1">Avg Monthly Revenue Recovered</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-blue-400">340%</p>
                  <p className="text-sm text-white/60 mt-1">Average ROI</p>
                </div>
                <div>
                  <p className="text-4xl font-bold text-purple-400">21 days</p>
                  <p className="text-sm text-white/60 mt-1">Average Payback Period</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
      `}</style>
    </Layout>
  );
}
