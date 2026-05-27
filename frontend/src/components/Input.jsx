export default function Input({ label, error, className = "", ...props }) {
  return (
    <label className="grid gap-1.5 text-sm text-ink">
      <span className="font-medium">{label}</span>
      <input
        className={`h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-2 focus:ring-teal-100 ${className}`}
        {...props}
      />
      {error ? <span className="text-xs text-danger">{error}</span> : null}
    </label>
  );
}
