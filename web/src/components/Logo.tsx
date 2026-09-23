import Link from "next/link";

export function Logo({ href }: { href: string }) {
  return (
    <Link href={href} className="logo" aria-label="Citobazar">
      cito<span>bazar</span>
    </Link>
  );
}
