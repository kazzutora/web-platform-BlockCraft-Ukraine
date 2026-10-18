const swatches = [
  { name: "--bg", className: "bg-bg" },
  { name: "--surface", className: "bg-surface" },
  { name: "--text", className: "bg-text" },
  { name: "--text-muted", className: "bg-muted" },
  { name: "--line", className: "bg-line" },
  { name: "--accent", className: "bg-accent" },
  { name: "--primary-bg", className: "bg-primary-bg" },
  { name: "--danger", className: "bg-danger" },
  { name: "--tag-mods", className: "bg-tag-mods" },
  { name: "--tag-packs", className: "bg-tag-packs" },
  { name: "--tag-skins", className: "bg-tag-skins" },
  { name: "--tag-servers", className: "bg-tag-servers" },
  { name: "--tag-moments", className: "bg-tag-moments" },
];

export function TokenSwatches() {
  return (
    <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
      {swatches.map((swatch) => (
        <li key={swatch.name} className="flex flex-col gap-2">
          <span className={`aspect-square border border-line ${swatch.className}`} />
          <code className="text-meta text-muted">{swatch.name}</code>
        </li>
      ))}
    </ul>
  );
}
