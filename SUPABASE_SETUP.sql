-- Run this in your Supabase SQL editor

create table if not exists profiles (
  id uuid primary key,
  username text unique not null,
  password_hash text not null,
  created_at timestamptz default now()
);

create table if not exists audio_records (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  title text not null,
  original_filename text,
  transcript text,
  translation text,
  audio_base64 text,
  edits jsonb,
  created_at timestamptz default now()
);

create index if not exists audio_records_user_id_created_at_idx
on audio_records (user_id, created_at desc);
