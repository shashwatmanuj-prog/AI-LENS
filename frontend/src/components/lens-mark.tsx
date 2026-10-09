export function Lens({ className }: { className?: string }) {
  // A stamp ring with a magnifier handle: "checked" + "looked closely".
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="13.5" cy="13.5" r="10" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="13.5" cy="13.5" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.25" strokeDasharray="2 2" />
      <path d="M21 21l7.5 7.5" stroke="hsl(var(--marigold))" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  );
}
