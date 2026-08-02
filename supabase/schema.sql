create table if not exists public.people (
  id bigint generated always as identity primary key,
  entity_type text not null default 'person',
  name text not null,
  role text not null default '',
  organization text not null default '',
  address text not null default '',
  zip_code text not null default '',
  city text not null default '',
  age text not null default '',
  country text not null default '',
  email text not null default '',
  phone text not null default '',
  website text not null default '',
  profile_url text not null default '',
  source text not null default 'manual',
  notes text not null default '',
  tags text not null default '',
  consent_basis text not null default '',
  collected_at text not null default '',
  inserted_at timestamptz not null default now()
);

create index if not exists idx_people_name on public.people (name);
create index if not exists idx_people_city on public.people (city);
create index if not exists idx_people_zip_code on public.people (zip_code);
create index if not exists idx_people_org on public.people (organization);
create index if not exists idx_people_profile_url on public.people (profile_url);

create unique index if not exists idx_people_unique_profile_url
on public.people (lower(profile_url))
where profile_url <> '';

create unique index if not exists idx_people_unique_company_identity
on public.people (lower(entity_type), lower(name), lower(zip_code), lower(city))
where profile_url = '';

alter table public.people enable row level security;
