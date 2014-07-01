-- Trigger functions

delimiter $$

-- session

create trigger session_update_before before update on session
for each row begin
    declare dummy int;
    if old.d_time is not null
    then
        select "May not update a closed session." into dummy
          from session where session_id = new.session_id;
    end if;
end $$



-- org

create trigger org_insert_before before insert on org
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_v_insert_before before insert on org_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_insert_after after insert on org
for each row begin
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name, description, end_date
        )
        values (
	new.org_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.description, new.end_date
	);
end $$

create trigger org_update_before before update on org
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name, description, end_date
        )
        values (
	new.org_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.description, new.end_date
	);
end $$

create trigger org_delete_before before delete on org
for each row begin
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name, description, end_date
        )
        values (
	old.org_id,
	old.moderation_user_id, 0, old.public, 0,
	old.name, old.description, old.end_date
	);
end $$



-- orgalias

create trigger orgalias_insert_before before insert on orgalias
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgalias_v_insert_before before insert on orgalias_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgalias_insert_after after insert on orgalias
for each row begin
    insert into orgalias_v (
        orgalias_id,
	org_id,
        moderation_user_id, a_time, public, existence,
        name
        )
        values (
	new.orgalias_id,
	new.org_id,
	new.moderation_user_id, 0, new.public, 1,
        new.name
	);
end $$

create trigger orgalias_update_before before update on orgalias
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into orgalias_v (
        orgalias_id,
	org_id,
        moderation_user_id, a_time, public, existence,
        name
        )
        values (
	new.orgalias_id,
	new.org_id,
	new.moderation_user_id, 0, new.public, 1,
        new.name
	);
end $$

create trigger orgalias_delete_before before delete on orgalias
for each row begin
    insert into orgalias_v (
        orgalias_id,
        org_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	old.orgalias_id,
	old.org_id,
	old.moderation_user_id, 0, old.public, 0,
        old.name
	);
end $$



-- event

create trigger event_insert_before before insert on event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_v_insert_before before insert on event_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_insert_after after insert on event
for each row begin
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name, start_date, end_date,
        description, start_time, end_time
        )
        values (
	new.event_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.start_date, new.end_date,
        new.description, new.start_time, new.end_time
	);
end $$

create trigger event_update_before before update on event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name, start_date, end_date,
        description, start_time, end_time
        )
        values (
	new.event_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.start_date, new.end_date,
        new.description, new.start_time, new.end_time
	);
end $$

create trigger event_delete_before before delete on event
for each row begin
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name, start_date, end_date,
        description, start_time, end_time
        )
        values (
	old.event_id,
	old.moderation_user_id, 0, old.public, 0,
	old.name, old.start_date, old.end_date,
        old.description, old.start_time, old.end_time
	);
end $$

-- address

create trigger address_insert_before before insert on address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger address_v_insert_before before insert on address_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger address_insert_after after insert on address
for each row begin
    insert into address_v (
        address_id,
        moderation_user_id, a_time, public, existence,
	postal, source, lookup,
        manual_longitude, manual_latitude,
        longitude, latitude
        )
        values (
	new.address_id,
	new.moderation_user_id, 0, new.public, 1,
	new.postal, new.source, new.lookup,
	new.manual_longitude, new.manual_latitude,
	new.longitude, new.latitude
	);
end $$

create trigger address_update_before before update on address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into address_v (
        address_id,
        moderation_user_id, a_time, public, existence,
	postal, source, lookup,
        manual_longitude, manual_latitude,
        longitude, latitude
        )
        values (
	new.address_id,
	new.moderation_user_id, 0, new.public, 1,
	new.postal, new.source, new.lookup,
	new.manual_longitude, new.manual_latitude,
	new.longitude, new.latitude
	);
end $$

create trigger address_delete_before before delete on address
for each row begin
    insert into address_v (
        address_id,
        moderation_user_id, a_time, public, existence,
	postal, source, lookup,
        manual_longitude, manual_latitude,
        longitude, latitude
        )
        values (
	old.address_id,
	old.moderation_user_id, 0, old.public, 0,
	old.postal, old.source, old.lookup,
	old.manual_longitude, old.manual_latitude,
	old.longitude, old.latitude
	);
end $$

-- note

create trigger note_insert_before before insert on note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$
    
create trigger note_v_insert_before before insert on note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$
    
create trigger note_insert_after after insert on note
for each row begin
    insert into note_fts (docid, content) values (new.note_id, new.text);

    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	new.note_id,
	new.moderation_user_id, 0, new.public, 1,
	new.text, new.source
	);
end $$

create trigger note_update_before before update on note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    update note_fts set content = new.text where docid = new.note_id;

    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	new.note_id,
	new.moderation_user_id, 0, new.public, 1,
	new.text, new.source
	);
end $$

create trigger note_delete_before before delete on note
for each row begin

    delete from note_fts where docid = old.note_id;

    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	old.note_id,
	old.moderation_user_id, 0, old.public, 0,
	old.text, old.source
	);
end $$

-- orgtag

create trigger orgtag_insert_before before insert on orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgtag_v_insert_before before insert on orgtag_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgtag_insert_after after insert on orgtag
for each row begin
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	new.orgtag_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.name_short, new.base, new.base_short, new.path, new.path_short, description, virtual
	);
end $$

create trigger orgtag_update_before before update on orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	new.orgtag_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.name_short, new.base, new.base_short, new.path, new.path_short, description, virtual
	);
end $$

create trigger orgtag_delete_before before delete on orgtag
for each row begin
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	old.orgtag_id,
	old.moderation_user_id, 0, old.public, 0,
	old.name, old.name_short, old.base, old.base_short, old.path, old.path_short, description, virtual
	);
end $$

-- eventtag

create trigger eventtag_insert_before before insert on eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger eventtag_v_insert_before before insert on eventtag_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger eventtag_insert_after after insert on eventtag
for each row begin
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	new.eventtag_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.name_short, new.base, new.base_short, new.path, new.path_short, description, virtual
	);
end $$

create trigger eventtag_update_before before update on eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	new.eventtag_id,
	new.moderation_user_id, 0, new.public, 1,
	new.name, new.name_short, new.base, new.base_short, new.path, new.path_short, description, virtual
	);
end $$

create trigger eventtag_delete_before before delete on eventtag
for each row begin
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, name_short, base, base_short, path, path_short, description, virtual
        )
        values (
	old.eventtag_id,
	old.moderation_user_id, 0, old.public, 0,
	old.name, old.name_short, old.base, old.base_short, old.path, old.path_short, description, virtual
	);
end $$

-- contact

create trigger contact_insert_before before insert on contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger contact_v_insert_before before insert on contact_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger contact_insert_after after insert on contact
for each row begin
    insert into contact_v (
        contact_id,
        medium_id,
        moderation_user_id, a_time, public, existence,
	text, description, source
        )
        values (
	new.contact_id,
	new.medium_id,
	new.moderation_user_id, 0, new.public, 1,
	new.text, new.description, new.source
	);
end $$

create trigger contact_update_before before update on contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into contact_v (
        contact_id,
        medium_id,
        moderation_user_id, a_time, public, existence,
	text, description, source
        )
        values (
	new.contact_id,
	new.medium_id,
	new.moderation_user_id, 0, new.public, 1,
	new.text, new.description, new.source
	);
end $$

create trigger contact_delete_before before delete on contact
for each row begin
    insert into contact_v (
        contact_id,
        medium_id,
        moderation_user_id, a_time, public, existence,
	text, description, source
        )
        values (
	old.contact_id,
        old.medium_id,
	old.moderation_user_id, 0, old.public, 0,
	old.text, old.description, old.source
	);
end $$



-- org_address

create trigger org_address_insert_before before insert on org_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_address_v_insert_before before insert on org_address_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_address_insert_after after insert on org_address
for each row begin
    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	new.org_id, new.address_id, 0, 1);
end $$

create trigger org_address_update_before before update on org_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	new.org_id, new.address_id, 0, 1);
end $$

create trigger org_address_delete_before before delete on org_address
for each row begin
    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	old.org_id, old.address_id, 0, 0);
end $$

-- org_note

create trigger org_note_insert_before before insert on org_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_note_v_insert_before before insert on org_note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_note_insert_after after insert on org_note
for each row begin
    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	new.org_id, new.note_id, 0, 1);
end $$

create trigger org_note_update_before before update on org_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	new.org_id, new.note_id, 0, 1);
end $$

create trigger org_note_delete_before before delete on org_note
for each row begin
    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	old.org_id, old.note_id, 0, 0);
end $$

-- org_orgtag

create trigger org_orgtag_insert_before before insert on org_orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_orgtag_v_insert_before before insert on org_orgtag_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_orgtag_insert_after after insert on org_orgtag
for each row begin
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	new.org_id, new.orgtag_id, 0, 1);
end $$

create trigger org_orgtag_update_before before update on org_orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	new.org_id, new.orgtag_id, 0, 1);
end $$

create trigger org_orgtag_delete_before before delete on org_orgtag
for each row begin
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	old.org_id, old.orgtag_id, 0, 0);
end $$

-- orgtag_note

create trigger orgtag_note_insert_before before insert on orgtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgtag_note_v_insert_before before insert on orgtag_note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger orgtag_note_insert_after after insert on orgtag_note
for each row begin
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	new.orgtag_id, new.note_id, 0, 1);
end $$

create trigger orgtag_note_update_before before update on orgtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	new.orgtag_id, new.note_id, 0, 1);
end $$

create trigger orgtag_note_delete_before before delete on orgtag_note
for each row begin
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	old.orgtag_id, old.note_id, 0, 0);
end $$

-- event_address

create trigger event_address_insert_before before insert on event_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_address_v_insert_before before insert on event_address_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_address_insert_after after insert on event_address
for each row begin
    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	new.event_id, new.address_id, 0, 1);
end $$

create trigger event_address_update_before before update on event_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	new.event_id, new.address_id, 0, 1);
end $$

create trigger event_address_delete_before before delete on event_address
for each row begin
    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	old.event_id, old.address_id, 0, 0);
end $$

-- event_note

create trigger event_note_insert_before before insert on event_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_note_v_insert_before before insert on event_note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_note_insert_after after insert on event_note
for each row begin
    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	new.event_id, new.note_id, 0, 1);
end $$

create trigger event_note_update_before before update on event_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	new.event_id, new.note_id, 0, 1);
end $$

create trigger event_note_delete_before before delete on event_note
for each row begin
    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	old.event_id, old.note_id, 0, 0);
end $$

-- event_eventtag

create trigger event_eventtag_insert_before before insert on event_eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_eventtag_v_insert_before before insert on event_eventtag_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_eventtag_insert_after after insert on event_eventtag
for each row begin
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	new.event_id, new.eventtag_id, 0, 1);
end $$

create trigger event_eventtag_update_before before update on event_eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	new.event_id, new.eventtag_id, 0, 1);
end $$

create trigger event_eventtag_delete_before before delete on event_eventtag
for each row begin
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	old.event_id, old.eventtag_id, 0, 0);
end $$

-- eventtag_note

create trigger eventtag_note_insert_before before insert on eventtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger eventtag_note_v_insert_before before insert on eventtag_note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger eventtag_note_insert_after after insert on eventtag_note
for each row begin
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	new.eventtag_id, new.note_id, 0, 1);
end $$

create trigger eventtag_note_update_before before update on eventtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	new.eventtag_id, new.note_id, 0, 1);
end $$

create trigger eventtag_note_delete_before before delete on eventtag_note
for each row begin
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	old.eventtag_id, old.note_id, 0, 0);
end $$

-- address_note

create trigger address_note_insert_before before insert on address_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger address_note_v_insert_before before insert on address_note_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger address_note_insert_after after insert on address_note
for each row begin
    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	new.address_id, new.note_id, 0, 1);
end $$

create trigger address_note_update_before before update on address_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	new.address_id, new.note_id, 0, 1);
end $$

create trigger address_note_delete_before before delete on address_note
for each row begin
    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	old.address_id, old.note_id, 0, 0);
end $$

-- org_event

create trigger org_event_insert_before before insert on org_event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_event_v_insert_before before insert on org_event_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_event_insert_after after insert on org_event
for each row begin
    insert into org_event_v (org_id, event_id, a_time, existence)
      values (
	new.org_id, new.event_id, 0, 1);
end $$

create trigger org_event_update_before before update on org_event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_event_v (org_id, event_id, a_time, existence)
      values (
	new.org_id, new.event_id, 0, 1);
end $$

create trigger org_event_delete_before before delete on org_event
for each row begin
    insert into org_event_v (org_id, event_id, a_time, existence)
      values (
	old.org_id, old.event_id, 0, 0);
end $$

-- org_contact

create trigger org_contact_insert_before before insert on org_contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_contact_v_insert_before before insert on org_contact_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger org_contact_insert_after after insert on org_contact
for each row begin
    insert into org_contact_v (org_id, contact_id, a_time, existence)
      values (
	new.org_id, new.contact_id, 0, 1);
end $$

create trigger org_contact_update_before before update on org_contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_contact_v (org_id, contact_id, a_time, existence)
      values (
	new.org_id, new.contact_id, 0, 1);
end $$

create trigger org_contact_delete_before before delete on org_contact
for each row begin
    insert into org_contact_v (org_id, contact_id, a_time, existence)
      values (
	old.org_id, old.contact_id, 0, 0);
end $$


-- event_contact

create trigger event_contact_insert_before before insert on event_contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_contact_v_insert_before before insert on event_contact_v
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
end $$

create trigger event_contact_insert_after after insert on event_contact
for each row begin
    insert into event_contact_v (event_id, contact_id, a_time, existence)
      values (
	new.event_id, new.contact_id, 0, 1);
end $$

create trigger event_contact_update_before before update on event_contact
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_contact_v (event_id, contact_id, a_time, existence)
      values (
	new.event_id, new.contact_id, 0, 1);
end $$

create trigger event_contact_delete_before before delete on event_contact
for each row begin
    insert into event_contact_v (event_id, contact_id, a_time, existence)
      values (
	old.event_id, old.contact_id, 0, 0);
end $$


delimiter ;

