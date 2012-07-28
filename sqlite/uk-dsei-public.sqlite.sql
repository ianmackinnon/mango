
-- Set DSEI exhibitor with UK addresses to public

update org set public = 1 where exists
       (
       select distinct o2.org_id from address
       join org_address using (address_id)
       join org as o2 using (org_id)
       join org_orgtag on (o2.org_id == org_orgtag.org_id)
       where
       o2.org_id = org.org_id and
       orgtag_id = (select orgtag_id from orgtag where name like "dsei%") and
       -8 < longitude and longitude < 2 and
       49 < latitude and latitude < 59
       );

-- check

select  org.org_id, org.public from address join org_address using (address_id) join org using (org_id) join org_orgtag on (org.org_id == org_orgtag.org_id)
       where
       orgtag_id = (select orgtag_id from orgtag where name like "dsei%") and
       -8 < longitude and longitude < 2 and
       49 < latitude and latitude < 59
;
