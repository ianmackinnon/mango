
-- Trigger functions

create trigger session_update_before before update on session
    when old.d_time is not null
begin
    select raise(rollback, "May not update a closed session.");
end;

create trigger organisation_insert_after after insert on organisation
    when new.organisation_e is null
begin
    update organisation set organisation_e =
        (
        select max(organisation_e) + 1 from
            (
            select organisation_e from organisation union all select 0 as organisation_e
            )
        )
        where organisation_id = new.organisation_id;
end;

create trigger address_insert_after after insert on address
    when new.address_e is null
begin
    update address set address_e =
        (
        select max(address_e) + 1 from
            (
            select address_e from address union all select 0 as address_e
            )
        )
        where address_id = new.address_id;
end;

create trigger note_insert_after after insert on note
    when new.note_e is null
begin
    update note set note_e =
        (
        select max(note_e) + 1 from
            (
            select note_e from note union all select 0 as note_e
            )
        )
        where note_id = new.note_id;
end;

create trigger organisation_tag_insert_after after insert on organisation_tag
    when new.organisation_tag_e is null
begin
    update organisation_tag set organisation_tag_e =
        (
        select max(organisation_tag_e) + 1 from
            (
            select organisation_tag_e from organisation_tag union all select 0 as organisation_tag_e
            )
        )
        where organisation_tag_id = new.organisation_tag_id;
end;

insert into auth (auth_id, url, name_hash) values (-1, "localhost", "d033e22ae348aeb5660fc2140aec35850c4da997");
insert into user (user_id, auth_id, name) values (-1, -1, "System");