-- CommunityLens AI schema. Run once in the Supabase SQL editor.
-- The FastAPI backend uses the service-role key; the browser never talks to
-- Supabase directly, so RLS is enabled with no public policies.

create table if not exists public.analyses (
  id             uuid primary key,
  created_at     timestamptz not null default now(),
  file_name      text not null,
  mime_type      text not null,
  file_path      text,
  language       text not null check (language in ('en', 'hi', 'kn')),
  model          text not null check (model like 'gemma-4%'),
  pages_analyzed int not null default 1,
  title          text,
  extraction     jsonb not null,
  verification   jsonb not null,
  translations   jsonb not null default '{}'::jsonb,
  community      text,
  share_slug     text unique,
  is_public      boolean not null default false
);

create index if not exists analyses_community_idx
  on public.analyses (lower(community), created_at desc) where is_public;
create index if not exists analyses_share_slug_idx on public.analyses (share_slug) where is_public;

alter table public.analyses enable row level security;
-- No policies on purpose: only the service role (backend) can read or write.

-- Private bucket for original uploads.
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;
