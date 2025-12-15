import { createContext, useContext, useState, useEffect } from 'react';

const BusinessContext = createContext();

export function BusinessProvider({ children }) {
  const [businesses, setBusinesses] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const savedBusinessId = typeof window !== 'undefined' 
      ? localStorage.getItem('selectedBusinessId') 
      : null;
    fetchBusinesses(savedBusinessId ? parseInt(savedBusinessId) : null);
  }, []);

  const fetchBusinesses = async (savedBusinessId) => {
    try {
      const res = await fetch('/api/business/');
      if (res.ok) {
        const data = await res.json();
        setBusinesses(data);
        if (data.length > 0) {
          const savedBusiness = savedBusinessId 
            ? data.find(b => b.id === savedBusinessId) 
            : null;
          setSelectedBusiness(savedBusiness || data[0]);
        }
        setError(null);
      } else {
        setError('Failed to load businesses');
      }
    } catch (e) {
      console.log('Could not fetch businesses:', e);
      setError('Could not connect to server');
    } finally {
      setLoading(false);
    }
  };

  const selectBusiness = (business) => {
    setSelectedBusiness(business);
    if (typeof window !== 'undefined' && business?.id) {
      localStorage.setItem('selectedBusinessId', business.id.toString());
    }
  };

  return (
    <BusinessContext.Provider value={{
      businesses,
      selectedBusiness,
      selectBusiness,
      loading,
      error,
      businessId: selectedBusiness?.id || null
    }}>
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness() {
  const context = useContext(BusinessContext);
  if (!context) {
    return {
      businesses: [],
      selectedBusiness: null,
      selectBusiness: () => {},
      loading: true,
      error: null,
      businessId: null
    };
  }
  return context;
}
