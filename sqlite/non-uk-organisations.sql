-- Show non-UK addresses

select org.name, longitude, latitude from address join org_address using (address_id) join org using (org_id) where not
(
       -8 < longitude and longitude < 2 and
       49 < latitude and latitude < 59
);
