
-- Trigger functions

create trigger session_update_before before update on session
    when old.d_time is not null
begin
    select raise(rollback, "May not update a closed session.");
end;
