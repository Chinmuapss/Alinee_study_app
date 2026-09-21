-- iBantay production schema. Run this entire file in Supabase SQL Editor.
create extension if not exists pgcrypto;

create type public.app_role as enum ('REPORTER', 'RESPONDER', 'ADMIN');
create type public.report_status as enum ('PENDING', 'RECEIVED', 'ASSIGNED', 'RESPONDER_ON_WAY', 'ARRIVED', 'RESOLVED', 'CANCELLED');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (char_length(trim(full_name)) between 2 and 120),
  role public.app_role not null default 'REPORTER',
  created_at timestamptz not null default now()
);
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  report_id text unique not null,
  user_id uuid not null references auth.users(id) on delete restrict,
  incident_type text not null check (incident_type in ('Robbery','Theft','Shooting','Fire','Accident','Medical Emergency','Other Emergency')),
  description text not null check (char_length(trim(description)) between 3 and 2000),
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  location_accuracy double precision check (location_accuracy >= 0),
  photo_path text,
  created_at timestamptz not null default now(),
  received_at timestamptz not null default now(),
  resolved_at timestamptz,
  status public.report_status not null default 'PENDING'
);
create table public.report_status_history (
  id bigint generated always as identity primary key,
  report_id uuid not null references public.reports(id) on delete cascade,
  old_status public.report_status,
  new_status public.report_status not null,
  changed_by uuid references auth.users(id),
  changed_at timestamptz not null default now()
);
create index reports_user_created_idx on public.reports(user_id, created_at desc);
create index reports_status_created_idx on public.reports(status, created_at desc);

create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path = public as $$
begin insert into public.profiles(id, full_name) values (new.id, coalesce(new.raw_user_meta_data->>'full_name', 'Community member')); return new; end; $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();
create or replace function public.set_report_id() returns trigger language plpgsql as $$
begin if new.report_id is null or new.report_id = '' then new.report_id := 'IB-' || lpad(nextval('public.report_number_seq')::text, 6, '0'); end if; return new; end; $$;
create sequence public.report_number_seq start 1;
create trigger set_report_identifier before insert on public.reports for each row execute function public.set_report_id();
create or replace function public.log_report_status() returns trigger language plpgsql security definer set search_path = public as $$
begin if tg_op = 'INSERT' then insert into public.report_status_history(report_id,new_status,changed_by) values(new.id,new.status,auth.uid()); elsif old.status is distinct from new.status then insert into public.report_status_history(report_id,old_status,new_status,changed_by) values(new.id,old.status,new.status,auth.uid()); if new.status = 'RESOLVED' then new.resolved_at := now(); end if; end if; return new; end; $$;
create trigger log_status before insert or update on public.reports for each row execute function public.log_report_status();

alter table public.profiles enable row level security; alter table public.reports enable row level security; alter table public.report_status_history enable row level security;
create function public.is_responder() returns boolean language sql stable security definer set search_path=public as $$ select exists(select 1 from public.profiles where id=auth.uid() and role in ('RESPONDER','ADMIN')) $$;
create policy "view own profile" on public.profiles for select using (id=auth.uid() or public.is_responder());
create policy "update own profile" on public.profiles for update using (id=auth.uid()) with check (id=auth.uid() and role='REPORTER');
create policy "reporters insert own reports" on public.reports for insert with check (user_id=auth.uid() and status='PENDING');
create policy "reporters view own reports; responders view all" on public.reports for select using (user_id=auth.uid() or public.is_responder());
create policy "responders update reports" on public.reports for update using (public.is_responder()) with check (public.is_responder());
create policy "view related status history" on public.report_status_history for select using (exists(select 1 from public.reports r where r.id=report_id and (r.user_id=auth.uid() or public.is_responder())));

-- Storage: create a private bucket named report-photos in Storage UI, then run:
insert into storage.buckets(id,name,public) values ('report-photos','report-photos',false) on conflict (id) do nothing;
create policy "users upload own report photos" on storage.objects for insert to authenticated with check (bucket_id='report-photos' and (storage.foldername(name))[1]=auth.uid()::text);
create policy "owners and responders read report photos" on storage.objects for select to authenticated using (bucket_id='report-photos' and ((storage.foldername(name))[1]=auth.uid()::text or public.is_responder()));

-- Promote approved accounts manually; never expose a service-role key in Flutter:
-- update public.profiles set role = 'RESPONDER' where id = '<AUTH_USER_UUID>';
