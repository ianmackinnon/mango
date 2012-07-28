-- Indices

create index org_public_idx on org (public);
create index address_public_idx on address (public);
create index orgtag_public_idx on orgtag (public);
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

CREATE TABLE org_address_v (
    org_id INTEGER NOT NULL, 
    address_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
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
CREATE TABLE org_orgtag_v (
    org_id INTEGER NOT NULL, 
    orgtag_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(org_id) REFERENCES org (org_id), 
    FOREIGN KEY(orgtag_id) REFERENCES orgtag (orgtag_id)
);
CREATE TABLE orgtag_note_v (
    orgtag_id INTEGER NOT NULL, 
    note_id INTEGER NOT NULL, 
    a_time FLOAT, 
    existence BOOLEAN NOT NULL, --
    FOREIGN KEY(orgtag_id) REFERENCES orgtag (orgtag_id), 
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





-- System user

insert into auth (auth_id, url, name_hash, gravatar_hash) values (-1, "localhost", "d033e22ae348aeb5660fc2140aec35850c4da997", "a45da96d0bf6575970f2d27af22be28a");
insert into user (user_id, auth_id, name) values (-1, -1, "System");
