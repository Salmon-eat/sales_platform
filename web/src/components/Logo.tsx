import Link from "next/link";

export function Logo({ href }: { href: string }) {
  return (
    <Link href={href} className="logo" aria-label="Bazarcito">
      bazar<span>cito</span>
    </Link>
  );
}
