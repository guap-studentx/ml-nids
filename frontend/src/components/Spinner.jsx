export default function Spinner({ label = "Загрузка" }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      <span>{label}</span>
    </div>
  );
}
