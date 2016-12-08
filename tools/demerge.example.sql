-- Demerge Hewlett-Packard and Hewlett-Packard Enterprise.

select * from org where name = "Hewlett-Packard";

SET @org1 = 4074;

select * from orgalias where org_id = @org1;

-- Org 2 aliases are:
-- HP ENTERPRISE SERVICES DEFENCE & SECURITY UK LTD
-- Hewlett Packard Enterprise

-- See if any addresses were created at the same time

select address_id, address.a_time from address
  join org_address using (address_id)
  join org using (org_id)
  where org_id = @org1
  order by address.a_time;

SET @org2address1 = 11792;


-- See if any addresses were created at the same time

select contact_id, contact.a_time from contact
  join org_contact using (contact_id)
  join org using (org_id)
  where org_id = @org1
  order by contact.a_time;

SET @org2contact1 = 1461;



-- Search caat-directory for aliases
-- hits in eco (company-country-rating)
-- and security-and-policing-2016



-- Create HPE

insert into org (name, moderation_user_id) values ("Hewlett Packard Enterprise", -1);
select * from org where name = "Hewlett Packard Enterprise";
SET @org2 = 13881;

-- Move aliases

update orgalias set org_id = @org2 where org_id = @org1 and orgalias_id in (2784, 5408);

-- Move addresses

update org_address set org_id = @org2 where org_id = @org1 and address_id = @org2address1;

-- Move contacts

update org_contact set org_id = @org2 where org_id = @org1 and contact_id = @org2contact1;

-- Check and remove tags

select orgtag_id, orgtag.a_time, orgtag.base_short from orgtag
  join org_orgtag using (orgtag_id)
  where org_id = @org1
  and (
    orgtag.base_short like "military-export-applicant-%" or
    orgtag.base_short like "security-and-policing-2016-%" or
    orgtag.base_short = "security-and-policing-2016"
  )
;

delete org_orgtag
 from orgtag
  join org_orgtag using (orgtag_id)
  where org_id = @org1
  and (
    orgtag.base_short like "military-export-applicant-%" or
    orgtag.base_short like "security-and-policing-2016-%" or
    orgtag.base_short = "security-and-policing-2016"
  )
;
  
    
-- time ./tools/insert_organisations.py ~/jobs/caat-directory/eco/source/company-country-rating-20??/company-country-rating-20??.json
-- 5m
--
-- time ./tools/insert_organisations.py ~/jobs/caat-directory/security-and-policing-2016/security-and-policing-2016.json
-- 15s
