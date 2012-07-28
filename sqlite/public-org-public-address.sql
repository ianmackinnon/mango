-- Set addresses to public if their organisations are public too.

update address set public = 1 where exists (
select distinct address_id from address as a2 join org_address using (address_id) join org using (org_id)
       where a2.address_id = address.address_id and org.public is 1 and a2.public is not 1
);

-- check

select distinct address_id from address as a2 join org_address using (address_id) join org using (org_id)
       where org.public is 1 and a2.public is not 1
