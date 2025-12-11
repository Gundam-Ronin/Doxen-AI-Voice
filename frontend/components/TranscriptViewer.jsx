import { useState, useEffect, useRef } from 'react';

export default function TranscriptViewer({ businessId }) {
  const [transcripts, setTranscripts] = useState([]);
  const [connected, setConnected] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!businessId || typeof window === 'undefined') return;

    let eventSource = null;
    
    try {
      eventSource = new EventSource(`/api/stream/transcripts/${businessId}`);

      eventSource.onopen = () => {
        setConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'transcript') {
            setTranscripts(prev => [...prev, data]);
          }
        } catch (e) {
          console.log('Parse error:', e);
        }
      };

      eventSource.onerror = () => {
        setConnected(false);
      };
    } catch (e) {
      console.log('SSE connection failed:', e);
      setConnected(false);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [businessId]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcripts]);

  return (
    <div className="glass-card p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Live Transcripts</h3>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></span>
          <span className="text-sm text-white/60">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto space-y-3 min-h-[300px]"
      >
        {transcripts.length === 0 ? (
          <div className="flex items-center justify-center h-full text-white/40">
            <div className="text-center">
              <p className="text-4xl mb-2">📞</p>
              <p>Waiting for calls...</p>
            </div>
          </div>
        ) : (
          transcripts.map((item, index) => (
            <div
              key={index}
              className={`transcript-bubble ${
                item.speaker === 'customer' ? 'transcript-customer' : 'transcript-cortana'
              }`}
            >
              <p className="text-xs text-white/50 mb-1 uppercase">
                {item.speaker === 'customer' ? '👤 Customer' : '🤖 Cortana'}
              </p>
              <p>{item.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
