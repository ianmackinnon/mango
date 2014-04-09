create view org_include as
select *
  from org
  where (
    exists (
      select 1
      from org_orgtag
      join orgtag using (orgtag_id)
      where (
        path_short = 'activity'
        or name_short like 'ranking|sipri-top-100-%'
        )
      and org_orgtag.org_id = org.org_id
      )
    or (
      exists (
        select 1
        from org_orgtag
        join orgtag using (orgtag_id)
        where name_short like 'exhibitor|dsei-%'
        and org_orgtag.org_id = org.org_id
        )
      and exists (
        select 1
        from org_orgtag
        join orgtag using (orgtag_id)
        where name_short like 'market|military-export-applicant-%'
        and org_orgtag.org_id = org.org_id
        )
      )
    )
  and not exists (
    select 1
    from org_orgtag
    join orgtag using (orgtag_id)
    where path_short = 'activity'
    and base_short in ('armed-forces', 'bespoke-firearms', 'exhibitions', 'government', 'medical', 'media')
    and org_orgtag.org_id = org.org_id
    );
