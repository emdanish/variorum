import { cn } from "@/lib/utils";

export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={cn("h-6 w-6", className)} aria-hidden>
      <rect width="32" height="32" rx="7" fill="#0B0B12" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="6.5" stroke="#26263a" />
      <path
        d="M8.5 9 L16 17 L23.5 9"
        stroke="#54506b"
        strokeWidth="2.3"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8.5 15 L16 23.5 L23.5 15"
        stroke="hsl(var(--primary))"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Logo({ withText = true, className }: { withText?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <Mark />
      {withText && (
        <span className="text-[15px] font-semibold tracking-tight text-foreground">Variorum</span>
      )}
    </span>
  );
}
