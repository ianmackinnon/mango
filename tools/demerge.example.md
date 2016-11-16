# De-merging companies.

Example: ITT and Exelis

select * from org_event where org_id in (1227, 4950);
update org_event set org_id = 1227 where org_id = 4950;

select * from orgevent where org_id in (1227, 4950);
update orgalias set org_id = 1227 where name like "EDO%";

select * from contact join org_contact using (contact_id) join org using (org_id) where org_id in (1227, 4950);

select * from note join org_note using (note_id) join org using (org_id) where org_id in (1227, 4950);
--(all sipri, bdec, ads)

select org.org_id, orgtag.orgtag_id, org.name, orgtag.name_short from orgtag join org_orgtag using (orgtag_id) join org using (org_id)  where org_id in (1227, 4950) order by orgtag.name_short limit 60 offset 0;
+--------+-----------+--------+------------------------------------------------------------+
| org_id | orgtag_id | name   | name_short                                                 |
+--------+-----------+--------+------------------------------------------------------------+
|   4950 |       281 | ITT    | data-source|corpwatch|arms-dealing                         |
|   4950 |      1972 | ITT    | exhibitor|dsei                                             |
|   4950 |       262 | ITT    | exhibitor|dsei-2011                                        |
|   4950 |       286 | ITT    | exhibitor|dsei-2013                                        |
|   1227 |      1987 | Exelis | exhibitor|farnborough                                      |
|   4950 |      1987 | ITT    | exhibitor|farnborough                                      |
|   4950 |       264 | ITT    | exhibitor|farnborough-2012                                 |
|   1227 |       471 | Exelis | exhibitor|farnborough-2014                                 |
|   4950 |       471 | ITT    | exhibitor|farnborough-2014                                 |
|   4950 |       285 | ITT    | exhibitor|security-and-policing-2012                       |
|   1227 |       472 | Exelis | exhibitor|security-and-policing-2014                       |
|   1227 |      1981 | Exelis | exhibitor|sofex-2014                                       |
|   4950 |      1968 | ITT    | market|military-export-applicant                           |
|   4950 |      1988 | ITT    | market|military-export-applicant-in-2010                   |
|   4950 |      2160 | ITT    | market|military-export-applicant-in-2011                   |
|   1227 |      2195 | Exelis | market|military-export-applicant-in-2012                   |
|   4950 |      2195 | ITT    | market|military-export-applicant-in-2012                   |
|   4950 |      2025 | ITT    | market|military-export-applicant-to-brazil                 |
|   4950 |       307 | ITT    | market|military-export-applicant-to-brazil-in-2010         |
|   4950 |       727 | ITT    | market|military-export-applicant-to-brazil-in-2011         |
|   4950 |       550 | ITT    | market|military-export-applicant-to-brazil-in-2012         |
|   4950 |      2030 | ITT    | market|military-export-applicant-to-bulgaria               |
|   4950 |       358 | ITT    | market|military-export-applicant-to-bulgaria-in-2010       |
|   4950 |      2008 | ITT    | market|military-export-applicant-to-canada                 |
|   4950 |       319 | ITT    | market|military-export-applicant-to-canada-in-2010         |
|   4950 |      2053 | ITT    | market|military-export-applicant-to-china                  |
|   4950 |       310 | ITT    | market|military-export-applicant-to-china-in-2010          |
|   1227 |      2066 | Exelis | market|military-export-applicant-to-croatia                |
|   1227 |       562 | Exelis | market|military-export-applicant-to-croatia-in-2012        |
|   4950 |      2032 | ITT    | market|military-export-applicant-to-czech-republic         |
|   4950 |       331 | ITT    | market|military-export-applicant-to-czech-republic-in-2010 |
|   4950 |       677 | ITT    | market|military-export-applicant-to-czech-republic-in-2011 |
|   4950 |      1990 | ITT    | market|military-export-applicant-to-denmark                |
|   4950 |       299 | ITT    | market|military-export-applicant-to-denmark-in-2010        |
|   4950 |       486 | ITT    | market|military-export-applicant-to-denmark-in-2012        |
|   4950 |      1997 | ITT    | market|military-export-applicant-to-france                 |
|   4950 |       304 | ITT    | market|military-export-applicant-to-france-in-2010         |
|   4950 |       654 | ITT    | market|military-export-applicant-to-france-in-2011         |
|   4950 |       488 | ITT    | market|military-export-applicant-to-france-in-2012         |
|   4950 |      1998 | ITT    | market|military-export-applicant-to-germany                |
|   4950 |       308 | ITT    | market|military-export-applicant-to-germany-in-2010        |
|   4950 |       653 | ITT    | market|military-export-applicant-to-germany-in-2011        |
|   4950 |       485 | ITT    | market|military-export-applicant-to-germany-in-2012        |
|   4950 |      1999 | ITT    | market|military-export-applicant-to-india                  |
|   4950 |       318 | ITT    | market|military-export-applicant-to-india-in-2010          |
|   4950 |       665 | ITT    | market|military-export-applicant-to-india-in-2011          |
|   4950 |      2000 | ITT    | market|military-export-applicant-to-italy                  |
|   4950 |       317 | ITT    | market|military-export-applicant-to-italy-in-2010          |
|   4950 |       666 | ITT    | market|military-export-applicant-to-italy-in-2011          |
|   1227 |      2012 | Exelis | market|military-export-applicant-to-kuwait                 |
|   1227 |       492 | Exelis | market|military-export-applicant-to-kuwait-in-2012         |
|   4950 |      2043 | ITT    | market|military-export-applicant-to-mexico                 |
|   4950 |       387 | ITT    | market|military-export-applicant-to-mexico-in-2010         |
|   4950 |       807 | ITT    | market|military-export-applicant-to-mexico-in-2011         |
|   4950 |      2013 | ITT    | market|military-export-applicant-to-morocco                |
|   4950 |       668 | ITT    | market|military-export-applicant-to-morocco-in-2011        |
|   4950 |      2044 | ITT    | market|military-export-applicant-to-netherlands            |
|   4950 |       324 | ITT    | market|military-export-applicant-to-netherlands-in-2010    |
|   4950 |       680 | ITT    | market|military-export-applicant-to-netherlands-in-2011    |
|   4950 |      2016 | ITT    | market|military-export-applicant-to-pakistan               |
+--------+-----------+--------+------------------------------------------------------------+
60 rows in set (0.01 sec)

select org.org_id, orgtag.orgtag_id, org.name, orgtag.name_short from orgtag join org_orgtag using (orgtag_id) join org using (org_id)  where org_id in (1227, 4950) order by orgtag.name_short limit 60 offset 60;
+--------+-----------+--------+----------------------------------------------------------------------------------------------------------+
| org_id | orgtag_id | name   | name_short                                                                                               |
+--------+-----------+--------+----------------------------------------------------------------------------------------------------------+
|   4950 |       716 | ITT    | market|military-export-applicant-to-pakistan-in-2011                                                     |
|   4950 |      2019 | ITT    | market|military-export-applicant-to-saudi-arabia                                                         |
|   4950 |       538 | ITT    | market|military-export-applicant-to-saudi-arabia-in-2012                                                 |
|   4950 |      2049 | ITT    | market|military-export-applicant-to-south-korea                                                          |
|   4950 |       328 | ITT    | market|military-export-applicant-to-south-korea-in-2010                                                  |
|   4950 |       500 | ITT    | market|military-export-applicant-to-south-korea-in-2012                                                  |
|   4950 |      1991 | ITT    | market|military-export-applicant-to-switzerland                                                          |
|   4950 |       352 | ITT    | market|military-export-applicant-to-switzerland-in-2010                                                  |
|   4950 |       676 | ITT    | market|military-export-applicant-to-switzerland-in-2011                                                  |
|   4950 |       527 | ITT    | market|military-export-applicant-to-switzerland-in-2012                                                  |
|   4950 |      2094 | ITT    | market|military-export-applicant-to-turkey                                                               |
|   4950 |       685 | ITT    | market|military-export-applicant-to-turkey-in-2011                                                       |
|   4950 |       526 | ITT    | market|military-export-applicant-to-turkey-in-2012                                                       |
|   4950 |      1996 | ITT    | market|military-export-applicant-to-united-arab-emirates                                                 |
|   4950 |       303 | ITT    | market|military-export-applicant-to-united-arab-emirates-in-2010                                         |
|   4950 |       481 | ITT    | market|military-export-applicant-to-united-arab-emirates-in-2012                                         |
|   4950 |      1989 | ITT    | market|military-export-applicant-to-united-states                                                        |
|   4950 |       298 | ITT    | market|military-export-applicant-to-united-states-in-2010                                                |
|   4950 |       649 | ITT    | market|military-export-applicant-to-united-states-in-2011                                                |
|   4950 |       473 | ITT    | market|military-export-applicant-to-united-states-in-2012                                                |
|   4950 |       295 | ITT    | market|military-export-licence-applicant-2011                                                            |
|   4950 |      1006 | ITT    | products-and-services|dsei-2011|dsei-2011-actuators                                                      |
|   4950 |       887 | ITT    | products-and-services|dsei-2011|dsei-2011-aerospace                                                      |
|   4950 |       863 | ITT    | products-and-services|dsei-2011|dsei-2011-audio-communication-systems                                    |
|   4950 |       966 | ITT    | products-and-services|dsei-2011|dsei-2011-battlefield-digitisation                                       |
|   4950 |       859 | ITT    | products-and-services|dsei-2011|dsei-2011-communications                                                 |
|   4950 |       953 | ITT    | products-and-services|dsei-2011|dsei-2011-electro-optics                                                 |
|   4950 |      1040 | ITT    | products-and-services|dsei-2011|dsei-2011-imaging-graphics-gis-mapping-displays                          |
|   4950 |       928 | ITT    | products-and-services|dsei-2011|dsei-2011-instruments-instrumentation-systems                            |
|   4950 |       994 | ITT    | products-and-services|dsei-2011|dsei-2011-mobile-communications                                          |
|   4950 |       996 | ITT    | products-and-services|dsei-2011|dsei-2011-network-enabled-capability                                     |
|   4950 |       954 | ITT    | products-and-services|dsei-2011|dsei-2011-night-vision                                                   |
|   4950 |       929 | ITT    | products-and-services|dsei-2011|dsei-2011-power-systems                                                  |
|   4950 |       999 | ITT    | products-and-services|dsei-2011|dsei-2011-radar                                                          |
|   4950 |      1000 | ITT    | products-and-services|dsei-2011|dsei-2011-radio-equipment                                                |
|   4950 |       857 | ITT    | products-and-services|dsei-2011|dsei-2011-surveillance-systems-equipment                                 |
|   4950 |       909 | ITT    | products-and-services|dsei-2011|dsei-2011-systems-integration                                            |
|   4950 |       867 | ITT    | products-and-services|dsei-2011|dsei-2011-telecommunications                                             |
|   4950 |       959 | ITT    | products-and-services|dsei-2011|dsei-2011-thermal-imaging                                                |
|   1227 |      1796 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-c-ied                        |
|   1227 |      1769 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-command-control              |
|   1227 |      1737 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-communications-equipment     |
|   1227 |      1753 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-national-security-resilience |
|   1227 |      1760 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-night-vision                 |
|   1227 |      1740 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-radio-communications         |
|   1227 |      1866 | Exelis | products-and-services|security-and-policing-2014|security-and-policing-2014-satellite-communications     |
|   4950 |      1930 | ITT    | products-and-services|sipri-2011|sipri-2011-electronics                                                  |
|   4950 |      1910 | ITT    | ranking|sipri-top-100-2008                                                                               |
|   4950 |      1911 | ITT    | ranking|sipri-top-100-2009                                                                               |
|   4950 |      1912 | ITT    | ranking|sipri-top-100-2010                                                                               |
|   4950 |      1917 | ITT    | ranking|sipri-top-100-2011                                                                               |
|   4950 |      1940 | ITT    | ranking|sipri-top-100-2012                                                                               |
|   4950 |         2 | ITT    | registrant|ads-aerospace                                                                                 |
|   1227 |         3 | Exelis | registrant|ads-defence                                                                                   |
|   4950 |         3 | ITT    | registrant|ads-defence                                                                                   |
|   1227 |         4 | Exelis | registrant|ads-security                                                                                  |
|   1227 |         1 | Exelis | registrant|bdec                                                                                          |
|   4950 |         1 | ITT    | registrant|bdec                                                                                          |
+--------+-----------+--------+----------------------------------------------------------------------------------------------------------+
58 rows in set (0.00 sec)

delete from org_orgtag where org_id in (1227, 4950);

## To update


data-source|corpwatch|arms-dealing                         |
exhibitor|dsei-2011                                        |
exhibitor|dsei-2013                                        |
exhibitor|farnborough-2012                                 |
exhibitor|farnborough-2014                                 |
exhibitor|security-and-policing-2012                       |
exhibitor|security-and-policing-2014                       |
exhibitor|sofex-2014                                       |
market|military-export-applicant-to-brazil-in-2010         |
market|military-export-applicant-to-brazil-in-2011         |
market|military-export-applicant-to-brazil-in-2012         |
products-and-services|dsei-2011|dsei-2011-actuators                                                      |
products-and-services|security-and-policing-2014|security-and-policing-2014-c-ied                        |
products-and-services|sipri-2011|sipri-2011-electronics                                                  |
ranking|sipri-top-100-2008                                                                               |
ranking|sipri-top-100-2009                                                                               |
ranking|sipri-top-100-2010                                                                               |
ranking|sipri-top-100-2011                                                                               |
ranking|sipri-top-100-2012                                                                               |
registrant|ads-aerospace                                                                                 |
registrant|ads-defence                                                                                   |
registrant|ads-security                                                                                  |
registrant|bdec                                                                                          |


/opt/python3-webapps/bin/python tools/insert_organisations.py -Av -L 1227,4950 \
  /tmp/corpwatch.2012-09-07.13-30.json \
  /tmp/dsei-2011.json \
  /tmp/dsei-2013.json \
  /tmp/farnborough-2012.json \
  /tmp/farnborough-2014.json \
  /tmp/security-and-policing-2012.json \
  /tmp/security-and-policing-2014.json \
  /tmp/sofex-2014.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2010.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2011.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2012.json \
  /tmp/sipri-top-100-2008.json \
  /tmp/sipri-top-100-2009.json \
  /tmp/sipri-top-100-2010.json \
  /tmp/sipri-top-100-2011.json \
  /tmp/sipri-top-100-2012.json \
  /tmp/ads-aerospace.20120627.1621.json \
  /tmp/ads-defence.20120627.1624.json \
  /tmp/ads-security.20120627.1634.json \
  ;


/opt/python3-webapps/bin/python tools/insert_organisations.py -A \
  /tmp/corpwatch.2012-09-07.13-30.json \
  /tmp/dsei-2011.json \
  /tmp/dsei-2013.json \
  /tmp/farnborough-2012.json \
  /tmp/farnborough-2014.json \
  /tmp/security-and-policing-2012.json \
  /tmp/security-and-policing-2014.json \
  /tmp/sofex-2014.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2010.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2011.json \
  /tmp/companies-that-applied-for-ml-licences-by-country-2012.json \
  /tmp/sipri-top-100-2008.json \
  /tmp/sipri-top-100-2009.json \
  /tmp/sipri-top-100-2010.json \
  /tmp/sipri-top-100-2011.json \
  /tmp/sipri-top-100-2012.json \
  /tmp/ads-aerospace.20120627.1621.json \
  /tmp/ads-defence.20120627.1624.json \
  /tmp/ads-security.20120627.1634.json \
  ;


### Then

update orgalias set org_id = 1227 where orgalias.name = "ITT Exelis";
delete from org_orgtag where org_id in (1227, 4950);
