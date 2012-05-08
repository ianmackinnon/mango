
-- Trigger functions

create trigger session_update_before before update on session
    when old.d_time is not null
begin
    select raise(rollback, "May not update a closed session.");
end;

create trigger organisation_insert_after after insert on organisation
    when new.organisation_e is null
begin
    update organisation set organisation_e = (select max(organisation_e) + 1 from organisation) where organisation_id = new.organisation_id;
end;
