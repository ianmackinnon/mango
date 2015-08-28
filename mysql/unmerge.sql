-- Examples:

select * from org_v where org_id = 6942;

-- note the deletion (merge) time

select org_id, orgtag_id from org_orgtag_v where org_id = 6942 and org_orgtag_v.a_time = 1400658709;


create temporary table `org_orgtag_temp` (
`org_id` int(11) NOT NULL,
`orgtag_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;


insert into org_orgtag_temp (org_id, orgtag_id) select org_id, orgtag_id from org_orgtag_v join orgtag using (orgtag_id) where org_id = 6942 and org_orgtag_v.a_time = 1400658709;

insert into org_orgtag (org_id, orgtag_id) select org_id, orgtag_id from org_orgtag_temp;

select org_id, orgtag_id, existence from org_orgtag_v where org_id = 6942 and org_orgtag_v.a_time = 1400658709;


-- Remove the copies from the merged-to org:

select org_id, orgtag_id, existence from org_orgtag_v where org_id = 2171 and org_orgtag_v.a_time = 1400658709;
select org_id, orgtag_id from org_orgtag where org_id = 2171 and org_orgtag.a_time = 1400658709;

delete from org_orgtag where org_id = 2171 and org_orgtag.a_time = 1400658709;

