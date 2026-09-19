import Link from "next/link";
import type { ReactNode } from "react";

export function PageHero({ crumbs, title, children }: { crumbs: { name: string; href: string }[]; title: string; children?: ReactNode }) {
  return (
    <section className="page-hero">
      <div className="container">
        <nav className="breadcrumbs" aria-label="breadcrumbs">
          {crumbs.map((c) => (
            <span key={c.href} className="crumb">
              <Link href={c.href}>{c.name}</Link>
              <span aria-hidden>›</span>
            </span>
          ))}
          <span>{title}</span>
        </nav>
        <h1>{title}</h1>
        {children}
      </div>
    </section>
  );
}
