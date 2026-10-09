-- Multi-cabinets : abonnement et quota au niveau du cabinet, données cloisonnées par cabinet, invitations
-- 1. Cabinet : abonnement Stripe et quota mensuel partagé
alter table public.smd_cabinets
  add column if not exists stripe_customer_id text default '',
  add column if not exists stripe_subscription_id text default '',
  add column if not exists quota_used_month integer default 0,
  add column if not exists quota_month text default '',
  add column if not exists updated_at timestamptz default now();
alter table public.smd_cabinets alter column plan set default 'free';

-- 2. Rattachement des utilisateurs, dossiers clients et analyses à un cabinet
alter table public.users drop constraint if exists users_tenant_id_fkey;
alter table public.users add constraint users_tenant_id_fkey
  foreign key (tenant_id) references public.smd_cabinets(id) on delete set null;
alter table public.clients  add column if not exists tenant_id uuid references public.smd_cabinets(id) on delete cascade;
alter table public.analyses add column if not exists tenant_id uuid references public.smd_cabinets(id) on delete cascade;
create index if not exists users_tenant_id_idx    on public.users(tenant_id);
create index if not exists clients_tenant_id_idx  on public.clients(tenant_id);
create index if not exists analyses_tenant_id_idx on public.analyses(tenant_id);

-- 3. Invitations des collaborateurs
create table if not exists public.smd_invitations (
  id          uuid primary key default extensions.uuid_generate_v4(),
  tenant_id   uuid not null references public.smd_cabinets(id) on delete cascade,
  email       text not null,
  role        text not null default 'collaborateur' check (role in ('collaborateur')),
  invited_by  text default '',
  created_at  timestamptz default now(),
  expires_at  timestamptz default now() + interval '30 days',
  accepted_at timestamptz
);
create unique index if not exists smd_invitations_email_attente_idx
  on public.smd_invitations (lower(email)) where accepted_at is null;
create index if not exists smd_invitations_tenant_id_idx on public.smd_invitations(tenant_id);
alter table public.smd_invitations enable row level security;

-- 4. Reprise de l'existant : un cabinet par utilisateur, avec son plan, son abonnement et son quota
do $$
declare u record; cid uuid;
begin
  for u in select * from public.users where tenant_id is null loop
    insert into public.smd_cabinets (nom, pays, plan, email_admin, stripe_customer_id, stripe_subscription_id,
                                     quota_used_month, quota_month)
    values (coalesce(nullif(u.cabinet, ''), nullif(u.company, ''), split_part(u.email, '@', 1)),
            coalesce(nullif(u.pays, ''), 'FR'), coalesce(nullif(u.plan, ''), 'free'), u.email,
            coalesce(u.stripe_customer_id, ''), coalesce(u.stripe_subscription_id, ''),
            coalesce(u.quota_used_month, 0), coalesce(u.quota_month, ''))
    returning id into cid;
    update public.users    set tenant_id = cid where id = u.id;
    update public.analyses set tenant_id = cid where user_email = u.email and tenant_id is null;
    update public.clients  set tenant_id = cid where user_email = u.email and tenant_id is null;
  end loop;
end $$;
