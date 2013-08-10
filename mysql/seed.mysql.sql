

-- System user

insert into auth (auth_id, url, name_hash, gravatar_hash) values (-1, "localhost", "d033e22ae348aeb5660fc2140aec35850c4da997", "a45da96d0bf6575970f2d27af22be28a");
insert into user (user_id, auth_id, name) values (-1, -1, "System");

insert into medium (medium_id, name) values (1, "Telephone"), (2, "Email"), (3, "Website"), (4, "Twitter");