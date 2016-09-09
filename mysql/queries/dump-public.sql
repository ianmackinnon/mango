-- Run as MySQL root user


select
    org_id,
    org.name
  from org
  where org.public = 1
  order by org_id
  into outfile '/tmp/mango-public-org.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;


select
    org_id,
    org.name,
    orgalias.name
  from org
    join orgalias using (org_id)
  where org.public = 1
    and orgalias.public = 1
  order by org_id, orgalias.name
  into outfile '/tmp/mango-public-org-alias.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;


select
    org_id,
    org.name,
    address.postal,
    coalesce(manual_longitude, longitude) as longitude,
    coalesce(manual_latitude, latitude) as latitude,
    source
  from org
    join org_address using (org_id)
    join address using (address_id)
  where org.public = 1
    and address.public = 1
  order by org_id, address_id
  into outfile '/tmp/mango-public-org-address.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;


select
    org_id,
    org.name,
    orgtag.base
  from org
    join org_orgtag using (org_id)
    join orgtag using (orgtag_id)
  where org.public = 1
    and orgtag.public = 1
    and orgtag.is_virtual is null
    and orgtag.path_short = "exhibitor"
  order by orgtag.name, org_id
  into outfile '/tmp/mango-public-org-exhibitor.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;


select
    org_id,
    org.name,
    orgtag.base
  from org
    join org_orgtag using (org_id)
    join orgtag using (orgtag_id)
  where org.public = 1
    and orgtag.public = 1
    and orgtag.is_virtual is null
    and orgtag.path_short = "market"
  order by orgtag.name, org_id
  into outfile '/tmp/mango-public-org-market.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;


select
    org_id,
    org.name,
    orgtag.base
  from org
    join org_orgtag using (org_id)
    join orgtag using (orgtag_id)
  where org.public = 1
    and orgtag.public = 1
    and orgtag.is_virtual is null
    and orgtag.path_short = "activity"
  order by orgtag.name, org_id
  into outfile '/tmp/mango-public-org-activity.csv'
    fields terminated by ','
    enclosed by '"'
    lines terminated by '\n'
;
