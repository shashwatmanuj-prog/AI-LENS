"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "./language-provider";
import { LanguageSwitch } from "./language-switch";
import { Lens } from "./lens-mark";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const { lang, setLang, t } = useLang();
  const path = usePathname();
  const links = [
    { href: "/", label: t("nav_home") },
    { href: "/saved", label: t("nav_saved") },
    { href: "/community", label: t("nav_community") },
  ];
  return (
    <header className="border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <div className="container flex flex-wrap items-center justify-between gap-3 py-3">
        <Link href="/" className="flex items-center gap-2 font-extrabold tracking-tight text-ink">
          <Lens className="h-7 w-7" />
          <span className="text-lg">CommunityLens</span>
        </Link>
        <nav aria-label="Main" className="order-3 flex w-full gap-1 sm:order-none sm:w-auto">
          {links.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-semibold",
                  active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <LanguageSwitch value={lang} onChange={setLang} label="Interface language" />
      </div>
    </header>
  );
}
