export default function GlassCard({ children, className = '', hover = true }) {
  return (
    <div className={`glass-card p-6 ${hover ? '' : 'hover:scale-100'} ${className}`}>
      {children}
    </div>
  );
}
