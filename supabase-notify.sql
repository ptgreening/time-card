-- ════════════════════════════════════════════════════════════
--  Missed punch email notifications
--  Already applied to the live project — kept here for reference
--  and so the setup can be rebuilt from scratch if ever needed.
-- ════════════════════════════════════════════════════════════

create extension if not exists pg_net;

-- Secrets live in Vault, never in the app's source. Set them once:
--   select vault.create_secret('<resend api key>', 'resend_api_key');
--   select vault.create_secret('<recipient address>', 'notify_email');
-- Change the recipient later with:
--   select vault.update_secret(
--     (select id from vault.secrets where name='notify_email'),
--     'new@address.com');

create or replace function notify_punch_request()
returns trigger
language plpgsql
security definer
set search_path = public, vault, net
as $$
declare
  api_key   text;
  recipient text;
  label     text;
  when_txt  text;
begin
  select decrypted_secret into api_key   from vault.decrypted_secrets where name = 'resend_api_key' limit 1;
  select decrypted_secret into recipient from vault.decrypted_secrets where name = 'notify_email'   limit 1;
  if api_key is null or recipient is null then
    return new;
  end if;

  label := case new.punch_type
             when 'in'    then 'Clock in'
             when 'lunch' then 'Lunch'
             when 'out'   then 'Clock out'
             else new.punch_type
           end;
  when_txt := to_char(new.punch_date, 'FMDay, FMMonth FMDD') ||
              ' at ' || to_char(new.punch_time, 'FMHH12:MI AM');

  perform net.http_post(
    url     := 'https://api.resend.com/emails',
    headers := jsonb_build_object(
                 'Authorization', 'Bearer ' || api_key,
                 'Content-Type',  'application/json'),
    body    := jsonb_build_object(
      'from',    'Haunted Trail Time Clock <onboarding@resend.dev>',
      'to',      jsonb_build_array(recipient),
      'subject', 'Missed punch: ' || new.employee_name || ' — ' || label,
      'text',    new.employee_name || ' reported a missed punch.' || chr(10) || chr(10) ||
                 'Punch:  ' || label     || chr(10) ||
                 'Should have been:  ' || when_txt || chr(10) ||
                 coalesce('What happened:  ' || new.note || chr(10), '') || chr(10) ||
                 'Open the Requests tab to review it.' || chr(10) ||
                 'https://hauntedtrailtimecard.netlify.app'
    )
  );
  return new;
exception when others then
  return new;   -- a notification failure must never block a report
end $$;

drop trigger if exists tr_notify_punch_request on tc_punch_requests;
create trigger tr_notify_punch_request
  after insert on tc_punch_requests
  for each row execute function notify_punch_request();

-- ── General notes ────────────────────────────────────────────
-- Same pattern, different subject. See the notify_note() function and the
-- tr_notify_note trigger on tc_notes in the live project.

-- Check delivery after a report:
--   select status_code, content, created from net._http_response order by created desc limit 5;
