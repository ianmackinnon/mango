-- Indices

create index org_public_idx on org (public);
create index orgalias_public_idx on orgalias (public);
create index event_public_idx on event (public);
create index address_public_idx on address (public);
create index orgtag_public_idx on orgtag (public);
create index eventtag_public_idx on eventtag (public);
create index note_public_idx on note (public);
create index address_latitude_idx on address (latitude);
create index address_longitude_idx on address (longitude);


-- Full text search

drop table note_fts;
create virtual table note_fts using fts3();

-- Version tables

CREATE TABLE org_v (
    org_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    org_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name VARCHAR NOT NULL, 

    FOREIGN KEY(org_id) REFERENCES org (org_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE orgalias_v (
    orgalias_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    orgalias_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    org_id INTEGER NOT NULL, 
    name VARCHAR NOT NULL, 

    FOREIGN KEY(orgalias_id) REFERENCES orgalias (orgalias_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE event_v (
    event_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    event_id INTEGER NOT NULL, 

    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name VARCHAR NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    description VARCHAR, 
    start_time TIME, 
    end_time TIME, 

    FOREIGN KEY(event_id) REFERENCES event (event_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE address_v (
    address_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    address_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN, 
    existence BOOLEAN NOT NULL, --

    postal VARCHAR NOT NULL, 
    source VARCHAR NOT NULL, 
    lookup VARCHAR, 
    manual_longitude FLOAT, 
    manual_latitude FLOAT, 
    longitude FLOAT, 
    latitude FLOAT, 

    FOREIGN KEY(address_id) REFERENCES address (address_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE note_v (
    note_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    note_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN, 
    existence BOOLEAN NOT NULL, --

    text VARCHAR NOT NULL, 
    source VARCHAR NOT NULL, 

    FOREIGN KEY(note_id) REFERENCES note (note_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE orgtag_v (
    orgtag_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    orgtag_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN, 
    existence BOOLEAN NOT NULL, --

    name VARCHAR NOT NULL, 
    short VARCHAR NOT NULL, 

    FOREIGN KEY(orgtag_id) REFERENCES orgtag (orgtag_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE eventtag_v (
    eventtag_v_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, --
    eventtag_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time FLOAT NOT NULL, 
    public BOOLEAN, 
    existence BOOLEAN NOT NULL, --

    name VARCHAR NOT NULL, 
    short VARCHAR NOT NULL, 

    FOREIGN KEY(eventtag_id) REFERENCES eventtag (eventtag_id), --
    FOREIGN KEY(moderation_user_id) REFERENCES user (user_id), 
    CHECK (public IN (0, 1))
);

CREATE TABLE org_address_v (
    org_id INTEGER NOT NULL, 
    address_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
    FOREIGN KEY(address_id) REFERENCES address (address_id)
);

CREATE TABLE event_address_v (
    event_id INTEGER NOT NULL, 
    address_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(event_id) REFERENCES event (event_id), 
    FOREIGN KEY(address_id) REFERENCES address (address_id)
);

CREATE TABLE org_note_v (
    org_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
    FOREIGN KEY(note_id) REFERENCES note (note_id)
);
CREATE TABLE event_note_v (
    event_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(event_id) REFERENCES event (event_id), 
    FOREIGN KEY(note_id) REFERENCES note (note_id)
);
CREATE TABLE org_orgtag_v (
    org_id INTEGER NOT NULL, 
    orgtag_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
    FOREIGN KEY(orgtag_id) REFERENCES orgtag (orgtag_id)
);
CREATE TABLE event_eventtag_v (
    event_id INTEGER NOT NULL, 
    eventtag_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(event_id) REFERENCES event (event_id), 
    FOREIGN KEY(eventtag_id) REFERENCES eventtag (eventtag_id)
);
CREATE TABLE orgtag_note_v (
    orgtag_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(orgtag_id) REFERENCES orgtag (orgtag_id), 
    FOREIGN KEY(note_id) REFERENCES note (note_id)
);
CREATE TABLE eventtag_note_v (
    eventtag_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(eventtag_id) REFERENCES eventtag (eventtag_id), 
    FOREIGN KEY(note_id) REFERENCES note (note_id)
);
CREATE TABLE address_note_v (
    address_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(address_id) REFERENCES address (address_id), 
    FOREIGN KEY(note_id) REFERENCES note (note_id)
);
CREATE TABLE org_event_v (
    org_id INTEGER NOT NULL, 
    event_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
    FOREIGN KEY(event_id) REFERENCES event (event_id)
);



-- Trigger functions

-- session

create trigger session_update_before before update on session
    when old.d_time is not null
begin
    select raise(rollback, "May not update a closed session.");
end;

-- org

create trigger org_insert_after after insert on org
begin
    update org set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_v (
        org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.org_id,
	new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger org_update_after after update on org
when cast(strftime('%s','now') as float) != new.a_time
begin
    update org set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_v (
        org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.org_id,
	new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger org_delete_after after delete on org
begin
    insert into org_v (
        org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	old.org_id,
	old.name,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- orgalias

create trigger orgalias_insert_after after insert on orgalias
begin
    update orgalias set a_time = strftime('%s','now') where orgalias_id = new.orgalias_id;
    insert into orgalias_v (
        orgalias_id, org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.orgalias_id,
	new.org_id, new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger orgalias_update_after after update on orgalias
when cast(strftime('%s','now') as float) != new.a_time
begin
    update orgalias set a_time = strftime('%s','now') where orgalias_id = new.orgalias_id;
    insert into orgalias_v (
        orgalias_id, org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.orgalias_id,
	new.org_id, new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger orgalias_delete_after after delete on orgalias
begin
    insert into orgalias_v (
        orgalias_id, org_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	old.orgalias_id,
        old.org_id, old.name,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- event

create trigger event_insert_after after insert on event
begin
    update event set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_v (
        event_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.event_id,
	new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger event_update_after after update on event
when cast(strftime('%s','now') as float) != new.a_time
begin
    update event set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_v (
        event_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	new.event_id,
	new.name,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger event_delete_after after delete on event
begin
    insert into event_v (
        event_id, name, moderation_user_id, a_time, public,
	existence
        )
        values (
	old.event_id,
	old.name,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- address

create trigger address_insert_after after insert on address
begin
    update address
        set a_time = strftime('%s','now') where address_id = new.address_id;
    insert into address_v (
        address_id,
	moderation_user_id, a_time, public,
	postal, source, lookup,
	manual_longitude, manual_latitude,
	longitude, latitude,
	existence
        )
        values (
        new.address_id,
	new.moderation_user_id, strftime('%s','now'), new.public,
	new.postal, new.source, new.lookup,
	new.manual_longitude, new.manual_latitude,
	new.longitude, new.latitude,
	1
	);
end;

create trigger address_update_after after update on address
when cast(strftime('%s','now') as float) != new.a_time
begin
    update address
        set a_time = strftime('%s','now') where address_id = new.address_id;
    insert into address_v (
        address_id,
	moderation_user_id, a_time, public,
	postal, source, lookup,
	manual_longitude, manual_latitude,
	longitude, latitude,
	existence
        )
        values (
        new.address_id,
	new.moderation_user_id, strftime('%s','now'), new.public,
	new.postal, new.source, new.lookup,
	new.manual_longitude, new.manual_latitude,
	new.longitude, new.latitude,
	1
	);
end;

create trigger address_delete_after after delete on address
begin
    insert into address_v (
        address_id,
	moderation_user_id, a_time, public,
	postal, source, lookup,
	manual_longitude, manual_latitude,
	longitude, latitude,
	existence
        )
        values (
        old.address_id,
	old.moderation_user_id, strftime('%s','now'), old.public,
	old.postal, old.source, old.lookup,
	old.manual_longitude, old.manual_latitude,
	old.longitude, old.latitude,
	0
	);
end;




-- note

create trigger note_insert_after after insert on note
begin
    insert into note_fts (docid, content) values (new.note_id, new.text);
    update note
        set a_time = strftime('%s','now') where note_id = new.note_id;
    insert into note_v (
        note_id,
	text, source,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.note_id,
	new.text, new.source,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger note_update_after after update on note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update note_fts set content = new.text where docid = new.note_id;
    update note
        set a_time = strftime('%s','now') where note_id = new.note_id;
    insert into note_v (
        note_id, 
	text, source,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.note_id,
	new.text, new.source,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger note_delete_after after delete on note
begin
    insert into note_v (
        note_id,
	text, source,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	old.note_id,
	old.text, old.source,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- orgtag


create trigger orgtag_insert_after after insert on orgtag
begin
    update orgtag
        set a_time = strftime('%s','now') where orgtag_id = new.orgtag_id;
    insert into orgtag_v (
        orgtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.orgtag_id,
	new.name, new.short,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger orgtag_update_after after update on orgtag
when cast(strftime('%s','now') as float) != new.a_time
begin
    update orgtag
        set a_time = strftime('%s','now') where orgtag_id = new.orgtag_id;
    insert into orgtag_v (
        orgtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.orgtag_id,
	new.name, new.short,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger orgtag_delete_after after delete on orgtag
begin
    insert into orgtag_v (
        orgtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	old.orgtag_id,
	old.name, old.short,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- eventtag


create trigger eventtag_insert_after after insert on eventtag
begin
    update eventtag
        set a_time = strftime('%s','now') where eventtag_id = new.eventtag_id;
    insert into eventtag_v (
        eventtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.eventtag_id,
	new.name, new.short,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger eventtag_update_after after update on eventtag
when cast(strftime('%s','now') as float) != new.a_time
begin
    update eventtag
        set a_time = strftime('%s','now') where eventtag_id = new.eventtag_id;
    insert into eventtag_v (
        eventtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	new.eventtag_id,
	new.name, new.short,
	new.moderation_user_id, strftime('%s','now'), new.public,
	1
	);
end;

create trigger eventtag_delete_after after delete on eventtag
begin
    insert into eventtag_v (
        eventtag_id,
	name, short,
	moderation_user_id, a_time, public,
	existence
        )
        values (
	old.eventtag_id,
	old.name, old.short,
	old.moderation_user_id, strftime('%s','now'), old.public,
	0
	);
end;



-- org_address


create trigger org_address_insert_after after insert on org_address
begin
    update org_address
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_address_v (org_id, address_id, a_time, existence)
        values (new.org_id, new.address_id, strftime('%s','now'), 1);
end;

create trigger org_address_update_after after update on org_address
when cast(strftime('%s','now') as float) != new.a_time
begin
    update org_address
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_address_v (org_id, address_id, a_time, existence)
        values (new.org_id, new.address_id, strftime('%s','now'), 1);
end;

create trigger org_address_delete_after after delete on org_address
begin
    insert into org_address_v (org_id, address_id, a_time, existence)
        values (old.org_id, old.address_id, strftime('%s','now'), 0);
end;



-- event_address


create trigger event_address_insert_after after insert on event_address
begin
    update event_address
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_address_v (event_id, address_id, a_time, existence)
        values (new.event_id, new.address_id, strftime('%s','now'), 1);
end;

create trigger event_address_update_after after update on event_address
when cast(strftime('%s','now') as float) != new.a_time
begin
    update event_address
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_address_v (event_id, address_id, a_time, existence)
        values (new.event_id, new.address_id, strftime('%s','now'), 1);
end;

create trigger event_address_delete_after after delete on event_address
begin
    insert into event_address_v (event_id, address_id, a_time, existence)
        values (old.event_id, old.address_id, strftime('%s','now'), 0);
end;



-- org_note


create trigger org_note_insert_after after insert on org_note
begin
    update org_note
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_note_v (org_id, note_id, a_time, existence)
        values (new.org_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger org_note_update_after after update on org_note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update org_note
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_note_v (org_id, note_id, a_time, existence)
        values (new.org_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger org_note_delete_after after delete on org_note
begin
    insert into org_note_v (org_id, note_id, a_time, existence)
        values (old.org_id, old.note_id, strftime('%s','now'), 0);
end;



-- event_note


create trigger event_note_insert_after after insert on event_note
begin
    update event_note
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_note_v (event_id, note_id, a_time, existence)
        values (new.event_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger event_note_update_after after update on event_note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update event_note
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_note_v (event_id, note_id, a_time, existence)
        values (new.event_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger event_note_delete_after after delete on event_note
begin
    insert into event_note_v (event_id, note_id, a_time, existence)
        values (old.event_id, old.note_id, strftime('%s','now'), 0);
end;



-- org_orgtag


create trigger org_orgtag_insert_after after insert on org_orgtag
begin
    update org_orgtag
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
        values (new.org_id, new.orgtag_id, strftime('%s','now'), 1);
end;

create trigger org_orgtag_update_after after update on org_orgtag
when cast(strftime('%s','now') as float) != new.a_time
begin
    update org_orgtag
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
        values (new.org_id, new.orgtag_id, strftime('%s','now'), 1);
end;

create trigger org_orgtag_delete_after after delete on org_orgtag
begin
    insert into org_orgtag_v (org_id, orgtag_id, a_time, existence)
        values (old.org_id, old.orgtag_id, strftime('%s','now'), 0);
end;



-- event_eventtag


create trigger event_eventtag_insert_after after insert on event_eventtag
begin
    update event_eventtag
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
        values (new.event_id, new.eventtag_id, strftime('%s','now'), 1);
end;

create trigger event_eventtag_update_after after update on event_eventtag
when cast(strftime('%s','now') as float) != new.a_time
begin
    update event_eventtag
        set a_time = strftime('%s','now') where event_id = new.event_id;
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
        values (new.event_id, new.eventtag_id, strftime('%s','now'), 1);
end;

create trigger event_eventtag_delete_after after delete on event_eventtag
begin
    insert into event_eventtag_v (event_id, eventtag_id, a_time, existence)
        values (old.event_id, old.eventtag_id, strftime('%s','now'), 0);
end;



-- orgtag_note


create trigger orgtag_note_insert_after after insert on orgtag_note
begin
    update orgtag_note
        set a_time = strftime('%s','now') where orgtag_id = new.orgtag_id;
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
        values (new.orgtag_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger orgtag_note_update_after after update on orgtag_note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update orgtag_note
        set a_time = strftime('%s','now') where orgtag_id = new.orgtag_id;
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
        values (new.orgtag_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger orgtag_note_delete_after after delete on orgtag_note
begin
    insert into orgtag_note_v (orgtag_id, note_id, a_time, existence)
        values (old.orgtag_id, old.note_id, strftime('%s','now'), 0);
end;



-- eventtag_note


create trigger eventtag_note_insert_after after insert on eventtag_note
begin
    update eventtag_note
        set a_time = strftime('%s','now') where eventtag_id = new.eventtag_id;
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
        values (new.eventtag_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger eventtag_note_update_after after update on eventtag_note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update eventtag_note
        set a_time = strftime('%s','now') where eventtag_id = new.eventtag_id;
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
        values (new.eventtag_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger eventtag_note_delete_after after delete on eventtag_note
begin
    insert into eventtag_note_v (eventtag_id, note_id, a_time, existence)
        values (old.eventtag_id, old.note_id, strftime('%s','now'), 0);
end;



-- address_note


create trigger address_note_insert_after after insert on address_note
begin
    update address_note
        set a_time = strftime('%s','now') where address_id = new.address_id;
    insert into address_note_v (address_id, note_id, a_time, existence)
        values (new.address_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger address_note_update_after after update on address_note
when cast(strftime('%s','now') as float) != new.a_time
begin
    update address_note
        set a_time = strftime('%s','now') where address_id = new.address_id;
    insert into address_note_v (address_id, note_id, a_time, existence)
        values (new.address_id, new.note_id, strftime('%s','now'), 1);
end;

create trigger address_note_delete_after after delete on address_note
begin
    insert into address_note_v (address_id, note_id, a_time, existence)
        values (old.address_id, old.note_id, strftime('%s','now'), 0);
end;



-- org_event


create trigger org_event_insert_after after insert on org_event
begin
    update org_event
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_event_v (org_id, event_id, a_time, existence)
        values (new.org_id, new.event_id, strftime('%s','now'), 1);
end;

create trigger org_event_update_after after update on org_event
when cast(strftime('%s','now') as float) != new.a_time
begin
    update org_event
        set a_time = strftime('%s','now') where org_id = new.org_id;
    insert into org_event_v (org_id, event_id, a_time, existence)
        values (new.org_id, new.event_id, strftime('%s','now'), 1);
end;

create trigger org_event_delete_after after delete on org_event
begin
    insert into org_event_v (org_id, event_id, a_time, existence)
        values (old.org_id, old.event_id, strftime('%s','now'), 0);
end;





-- System user

insert into auth (auth_id, url, name_hash, gravatar_hash) values (-1, "localhost", "d033e22ae348aeb5660fc2140aec35850c4da997", "a45da96d0bf6575970f2d27af22be28a");
insert into user (user_id, auth_id, name) values (-1, -1, "System");
