"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/language-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function CommunityIndex() {
  const { t } = useLang();
  const router = useRouter();
  const [name, setName] = useState("");
  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("community_search")}</h1>
      <form
        className="mt-6 grid gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) router.push(`/community/${encodeURIComponent(name.trim())}`);
        }}
      >
        <Label htmlFor="cname">{t("nav_community")}</Label>
        <div className="flex gap-2">
          <Input id="cname" value={name} maxLength={60} placeholder={t("community_hint")} onChange={(e) => setName(e.target.value)} />
          <Button type="submit" disabled={!name.trim()}>
            {t("open")}
          </Button>
        </div>
      </form>
    </div>
  );
}
