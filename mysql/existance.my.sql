-- Org Addresses that should be linked

select org_id, address_id, existence, a_time
  from (
    select org_id, address_id, existence, a_time
      from org_address_v as t1
      where not exists (
        select 1
          from org_address_v as t2
          where t1.org_id = t2.org_id
            and t1.address_id = t2.address_id
            and t2.a_time > t1.a_time
      )
  ) as q1
  where q1.existence = 1
    and not exists (
      select 1
        from org_address as t3
        where t3.org_id = q1.org_id
          and t3.address_id = q1.address_id
      )
  order by a_time desc;


-- Org Addresses that should not be linked

select org_id, address_id, existence, a_time
  from (
    select org_id, address_id, existence, a_time
      from org_address_v as t1
      where not exists (
        select 1
          from org_address_v as t2
          where t1.org_id = t2.org_id
            and t1.address_id = t2.address_id
            and t2.a_time > t1.a_time
      )
  ) as q1
  where q1.existence = 0
    and exists (
      select 1
        from org_address as t3
        where t3.org_id = q1.org_id
          and t3.address_id = q1.address_id
      )
  order by a_time desc;


-- Org Addresses that have no versions

-- ?
