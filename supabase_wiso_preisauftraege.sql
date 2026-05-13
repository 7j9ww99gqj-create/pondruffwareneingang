create table if not exists wiso_preisauftraege (
  uuid uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default now(),
  order_id text,
  customer text,
  purchase_order text,
  order_data jsonb
);

alter table wiso_preisauftraege enable row level security;

drop policy if exists "allow authenticated read wiso orders" on wiso_preisauftraege;
drop policy if exists "allow authenticated insert wiso orders" on wiso_preisauftraege;

create policy "allow authenticated read wiso orders"
on wiso_preisauftraege for select
to authenticated
using (true);

create policy "allow authenticated insert wiso orders"
on wiso_preisauftraege for insert
to authenticated
with check (true);
