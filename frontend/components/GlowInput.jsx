export default function GlowInput({
  type = 'text',
  placeholder = '',
  value,
  onChange,
  className = '',
  ...props
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={`glow-input ${className}`}
      {...props}
    />
  );
}
