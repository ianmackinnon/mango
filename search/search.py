#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import inspect
import logging
from optparse import OptionParser

import pyelasticsearch



log = logging.getLogger('search')
setting_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
elasticsearch_path = "http://localhost:9200/"



def get_search():
    es = pyelasticsearch.ElasticSearch(elasticsearch_path)
    try:
        es.refresh()
    except pyelasticsearch.requests.exceptions.ConnectionError:
        return
    return es



def count_org(search):
    results = search.count(None, index="mango", doc_type="org")
    return results["count"]



def verify_org(es, orm, Org, Orgalias):
    len_alias_orm = orm.query(Org).count()
    len_alias_es = count_org(es)
    return len_alias_orm == len_alias_es



def verify(es, orm, Org, Orgalias):
    try:
        if verify_org(es, orm, Org, Orgalias):
            return
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        pass

    rebuild(es, orm, Org, Orgalias)



def org_doc(org, alias_list=None):
    if alias_list is None:
        alias_list = [orgalias.name for orgalias in org.orgalias_list_public]
    return {
        "org_id": org.org_id,
        "name": org.name,
        "public": org.public,
        "alias": [org.name] + alias_list,
        }
    


def index_org(es, org, alias_list=None):
    es.index("mango", "org", org_doc(org, alias_list), id=org.org_id,)



def index_orgalias(es, orgalias, orm, Orgalias):
    query = orm.query(Orgalias) \
        .filter(Orgalias.org_id == orgalias.org_id) \
        .filter(Orgalias.public == 1)
    alias_list = [orgalias.name for orgalias in query.all()]
    index_org(es, orgalias.org, alias_list=alias_list)



def delete_org(es, org):
    es.delete("mango", "org", id=org.org_id,)



def build_org(es, orm, Org, Orgalias):
    log.warning("Bulk adding org : start")
    es.bulk_index("mango", "org",
                  [org_doc(org) for org in orm.query(Org)[:10000]],
                  id_field="org_id",
                  )
    log.warning("Bulk adding org : end")





    

def rebuild(es, orm, Org, Orgalias):
    settings_path = os.path.join(setting_path, u"mango.json")

    log.warning("Deleting ES index.")
    try:
        es.delete_index('mango')
    except:
        pass

    settings = json.load(open(settings_path))

    es.create_index("mango", settings)

    build_org(es, orm, Org, Orgalias)

    




def main(orm):
    for hit in es.search("name.name_fuzzy:aerro", index="mango")["hits"]["hits"]:
        print "%0.3f  %6s  %s" % (hit["_score"], hit["_source"]["public"], hit["_source"]["name"])

    d = {
        "query": {
            "filtered": {
                "query": {
                    "query_string": {
                        "fields": ["alias_name.name_fuzzy"],
                        "query": "sys"
                        }
                    },
                "filter": {
                    "term": {
                        "org_public": 1
                        }
                    }
                }
            }
        }

    print
    print "d"
    for hit in es.search(d, index="mango")["hits"]["hits"]:
        print "%0.3f  %6s  %s  %s" % (hit["_score"], hit["_source"]["org_public"], hit["_source"]["org_name"], hit["_source"]["alias_name"])





u"""

curl http://localhost:9200/mango/org/_search?pretty=true -d '{
  "query": {
    "query_string": {
      "fields": ["name"],
      "query": "aero"
    }
  }
}'

curl http://localhost:9200/mango/org/_search?pretty=true -d '{
  "query": {
    "query_string": {
      "fields": ["name.name_fuzzy"],
      "query": "aerro"
    }
  }
}'

curl http://localhost:9200/mango/org/_search?pretty=true -d '{
  "query": {
    "filtered": {
      "query": {
        "query_string": {
          "fields": ["name"],
          "query": "aero"
        }
      },
      "filter": {
        "term": {
          "public": 1
        }
      }
    }
  }
}'

curl http://localhost:9200/mango/org/_search?pretty=true -d '{
  "query": {
    "filtered": {
      "query": {
        "query_string": {
          "fields": ["name.name_fuzzy"],
          "query": "aerro"
        }
      },
      "filter": {
        "term": {
          "public": 1
        }
      }
    }
  }
}'



"""
