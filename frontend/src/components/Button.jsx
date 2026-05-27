const variants = {
  primary: "border-accent bg-accent text-white hover:bg-teal-800",
  secondary: "border-line bg-white text-ink hover:bg-panel",
  danger: "border-danger bg-danger text-white hover:bg-red-800",
  ghost: "border-transparent bg-transparent text-muted hover:bg-panel hover:text-ink",
};

export default function Button({ children, variant = "secondary", className = "", type = "button", ...props }) {
  return (
    <button
      type={type}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-55 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
