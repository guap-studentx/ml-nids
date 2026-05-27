export default function PageHeader({ title, description, actions }) {
  return (
    <div className="flex flex-col gap-3 border-b border-line bg-white px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        {description ? <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
