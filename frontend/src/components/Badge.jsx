const tones = {
  neutral: "border-slate-300 bg-slate-100 text-slate-700",
  green: "border-emerald-200 bg-emerald-50 text-emerald-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  red: "border-red-200 bg-red-50 text-red-700",
  blue: "border-sky-200 bg-sky-50 text-sky-700",
};

export default function Badge({ children, tone = "neutral" }) {
  return (
    <span className={`inline-flex min-h-6 items-center rounded border px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
