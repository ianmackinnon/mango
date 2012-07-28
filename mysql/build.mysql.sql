-- Indices

-- Full text search

alter table note_fts engine = myisam;
alter table note_fts add fulltext(content);



-- Version Tables

CREATE TABLE org_v (
    org_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    org_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT org_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE event_v (
    event_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    event_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name LONGTEXT NOT NULL, 
    start_date date NOT NULL,
    end_date date NOT NULL,
    description longtext,
    start_time time DEFAULT NULL,
    end_time time DEFAULT NULL,

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT event_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE address_v (
    address_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    address_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    postal LONGTEXT NOT NULL, 
    source LONGTEXT NOT NULL, 
    lookup LONGTEXT, 
    manual_longitude FLOAT, 
    manual_latitude FLOAT, 
    longitude FLOAT, 
    latitude FLOAT, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT address_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE note_v (
    note_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    note_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    text LONGTEXT NOT NULL, 
    source LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT note_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE orgtag_v (
    orgtag_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    orgtag_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name LONGTEXT NOT NULL, 
    short LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT orgtag_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE eventtag_v (
    eventtag_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    eventtag_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name LONGTEXT NOT NULL, 
    short LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT eventtag_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE org_address_v (
    org_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE org_note_v (
    org_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE org_orgtag_v (
    org_id INTEGER NOT NULL,
    orgtag_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE orgtag_note_v (
    orgtag_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_address_v (
    event_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_note_v (
    event_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_eventtag_v (
    event_id INTEGER NOT NULL,
    eventtag_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE eventtag_note_v (
    eventtag_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE address_note_v (
    address_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time FLOAT NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;


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
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	new.org_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name
	);
end $$

create trigger org_update_before before update on org
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	new.org_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name
	);
end $$

create trigger org_delete_before before delete on org
for each row begin
    insert into org_v (
        org_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	old.org_id,
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.name
	);
end $$

-- event

create trigger event_insert_before before insert on event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	new.event_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name
	);
end $$

create trigger event_update_before before update on event
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	new.event_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name
	);
end $$

create trigger event_delete_before before delete on event
for each row begin
    insert into event_v (
        event_id,
        moderation_user_id, a_time, public, existence,
	name
        )
        values (
	old.event_id,
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.name
	);
end $$

-- address

create trigger address_insert_before before insert on address
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
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
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
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
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
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.postal, old.source, old.lookup,
	old.manual_longitude, old.manual_latitude,
	old.longitude, old.latitude
	);
end $$

-- note

create trigger note_insert_before before insert on note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	new.note_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.text, new.source
	);
end $$

create trigger note_update_before before update on note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	new.note_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.text, new.source
	);
end $$

create trigger note_delete_before before delete on note
for each row begin
    insert into note_v (
        note_id,
        moderation_user_id, a_time, public, existence,
	text, source
        )
        values (
	old.note_id,
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.text, old.source
	);
end $$

-- orgtag

create trigger orgtag_insert_before before insert on orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	new.orgtag_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name, new.short
	);
end $$

create trigger orgtag_update_before before update on orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	new.orgtag_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name, new.short
	);
end $$

create trigger orgtag_delete_before before delete on orgtag
for each row begin
    insert into orgtag_v (
        orgtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	old.orgtag_id,
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.name, old.short
	);
end $$

-- eventtag

create trigger eventtag_insert_before before insert on eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	new.eventtag_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name, new.short
	);
end $$

create trigger eventtag_update_before before update on eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	new.eventtag_id,
	new.moderation_user_id, UNIX_TIMESTAMP(), new.public, 1,
	new.name, new.short
	);
end $$

create trigger eventtag_delete_before before delete on eventtag
for each row begin
    insert into eventtag_v (
        eventtag_id,
        moderation_user_id, a_time, public, existence,
	name, short
        )
        values (
	old.eventtag_id,
	old.moderation_user_id, UNIX_TIMESTAMP(), old.public, 0,
	old.name, old.short
	);
end $$

-- org_address

create trigger org_address_insert_before before insert on org_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	new.org_id, new.address_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_address_update_before before update on org_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	new.org_id, new.address_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_address_delete_before before delete on org_address
for each row begin
    insert into org_address_v (org_id, address_id, a_time, existence)
      values (
	old.org_id, old.address_id, UNIX_TIMESTAMP(), 1);
end $$

-- org_note

create trigger org_note_insert_before before insert on org_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	new.org_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_note_update_before before update on org_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	new.org_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_note_delete_before before delete on org_note
for each row begin
    insert into org_note_v (org_id, note_id, a_time, existence)
      values (
	old.org_id, old.note_id, UNIX_TIMESTAMP(), 1);
end $$

-- org_orgtag

create trigger org_orgtag_insert_before before insert on org_orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	new.org_id, new.orgtag_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_orgtag_update_before before update on org_orgtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	new.org_id, new.orgtag_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger org_orgtag_delete_before before delete on org_orgtag
for each row begin
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
      values (
	old.org_id, old.orgtag_id, UNIX_TIMESTAMP(), 1);
end $$

-- orgtag_note

create trigger orgtag_note_insert_before before insert on orgtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	new.orgtag_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger orgtag_note_update_before before update on orgtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	new.orgtag_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger orgtag_note_delete_before before delete on orgtag_note
for each row begin
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
      values (
	old.orgtag_id, old.note_id, UNIX_TIMESTAMP(), 1);
end $$

-- event_address

create trigger event_address_insert_before before insert on event_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	new.event_id, new.address_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_address_update_before before update on event_address
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	new.event_id, new.address_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_address_delete_before before delete on event_address
for each row begin
    insert into event_address_v (event_id, address_id, a_time, existence)
      values (
	old.event_id, old.address_id, UNIX_TIMESTAMP(), 1);
end $$

-- event_note

create trigger event_note_insert_before before insert on event_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	new.event_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_note_update_before before update on event_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	new.event_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_note_delete_before before delete on event_note
for each row begin
    insert into event_note_v (event_id, note_id, a_time, existence)
      values (
	old.event_id, old.note_id, UNIX_TIMESTAMP(), 1);
end $$

-- event_eventtag

create trigger event_eventtag_insert_before before insert on event_eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	new.event_id, new.eventtag_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_eventtag_update_before before update on event_eventtag
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	new.event_id, new.eventtag_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger event_eventtag_delete_before before delete on event_eventtag
for each row begin
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
      values (
	old.event_id, old.eventtag_id, UNIX_TIMESTAMP(), 1);
end $$

-- eventtag_note

create trigger eventtag_note_insert_before before insert on eventtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	new.eventtag_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger eventtag_note_update_before before update on eventtag_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	new.eventtag_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger eventtag_note_delete_before before delete on eventtag_note
for each row begin
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
      values (
	old.eventtag_id, old.note_id, UNIX_TIMESTAMP(), 1);
end $$

-- address_note

create trigger address_note_insert_before before insert on address_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	new.address_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger address_note_update_before before update on address_note
for each row begin
    set new.a_time = UNIX_TIMESTAMP();

    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	new.address_id, new.note_id, UNIX_TIMESTAMP(), 1);
end $$

create trigger address_note_delete_before before delete on address_note
for each row begin
    insert into address_note_v (address_id, note_id, a_time, existence)
      values (
	old.address_id, old.note_id, UNIX_TIMESTAMP(), 1);
end $$

delimiter ;


-- System user

insert into auth (auth_id, url, name_hash, gravatar_hash) values (-1, "localhost", "d033e22ae348aeb5660fc2140aec35850c4da997", "a45da96d0bf6575970f2d27af22be28a");
insert into user (user_id, auth_id, name) values (-1, -1, "System");
