export default function GlassButton({ 
  children, 
  variant = 'default', 
  onClick, 
  disabled = false,
  className = '' 
}) {
  const baseClass = variant === 'primary' ? 'glass-button-primary' : 'glass-button';
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseClass} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
    >
      {children}
    </button>
  );
}
