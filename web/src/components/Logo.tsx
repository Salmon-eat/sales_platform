import Link from "next/link";

export function Logo({ href }: { href: string }) {
  return (
    <Link href={href} className="logo" aria-label="Citobazar">
      {/* the same mark as the tab icon (app/icon.svg) */}
      <svg className="logo__mark" viewBox="12 10 41 44" width="1.21em" height="1.27em" aria-hidden>
        <path d="M47.4 21.5A17 17 0 1 0 47.4 42.5" fill="none" stroke="var(--accent)" strokeWidth="9" strokeLinecap="round" />
        <circle cx="34.5" cy="32" r="5" fill="currentColor" />
      </svg>
      cito<span>bazar</span>
    </Link>
  );
}
