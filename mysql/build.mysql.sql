-- Indices

-- Full text search

alter table note_fts engine = myisam;
alter table note_fts add fulltext(content);



-- Version Tables

CREATE TABLE org_v (
    org_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    org_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time DOUBLE NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    name LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT org_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE orgalias_v (
    orgalias_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    orgalias_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time DOUBLE NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --
 
    org_id INTEGER NOT NULL, 
    name LONGTEXT NOT NULL, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT orgalias_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE event_v (
    event_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    event_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time DOUBLE NOT NULL, 
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
    a_time DOUBLE NOT NULL, 
    public BOOLEAN,
    existence BOOLEAN NOT NULL, --

    postal LONGTEXT NOT NULL, 
    source LONGTEXT NOT NULL, 
    lookup LONGTEXT, 
    manual_longitude DOUBLE, 
    manual_latitude DOUBLE, 
    longitude DOUBLE, 
    latitude DOUBLE, 

    KEY moderation_user_id (moderation_user_id),
    CONSTRAINT address_v_c2 FOREIGN KEY (moderation_user_id)
      REFERENCES user (user_id)
) DEFAULT CHARSET=utf8;

CREATE TABLE note_v (
    note_v_id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, --
    note_id INTEGER NOT NULL, 
    moderation_user_id INTEGER, 
    a_time DOUBLE NOT NULL, 
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
    a_time DOUBLE NOT NULL, 
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
    a_time DOUBLE NOT NULL, 
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
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE org_note_v (
    org_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE org_orgtag_v (
    org_id INTEGER NOT NULL,
    orgtag_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE orgtag_note_v (
    orgtag_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_address_v (
    event_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_note_v (
    event_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE event_eventtag_v (
    event_id INTEGER NOT NULL,
    eventtag_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE eventtag_note_v (
    eventtag_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE address_note_v (
    address_id INTEGER NOT NULL,
    note_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;

CREATE TABLE org_event_v (
    org_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL, 
    a_time DOUBLE NOT NULL, 
    existence BOOLEAN NOT NULL --
) DEFAULT CHARSET=utf8;
