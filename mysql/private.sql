-- Should be pending:

select count(*)
  from org as o1
  where
    o1.public = 0
    and (
    o1.end_date
    or
    not exists (
    select 1
      from orgtag
      join org_orgtag using (orgtag_id)
      where orgtag.name_short like "activity-exclusion|%"
        and org_orgtag.org_id = o1.org_id
    ))
  ;


select *
  from org
  where
    public = 0
    and (
    end_date
    or
    not exists (
    select 1
      from orgtag
      join org_orgtag using (orgtag_id)
      where orgtag.name_short like "activity-exclusion|%"
        and org_orgtag.org_id = org.org_id
    ))
    limit 30
  ;

update org
  set
    public = null
  where
    public = 0
    and (
    end_date
    or
    not exists (
    select 1
      from orgtag
      join org_orgtag using (orgtag_id)
      where orgtag.name_short like "activity-exclusion|%"
        and org_orgtag.org_id = org.org_id
    ))
  ;
