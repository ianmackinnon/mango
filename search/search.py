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
es_path = "http://localhost:9200/"
es_index = "mango"
es_doc_type = "org"

logging.getLogger('elasticsearch.trace').setLevel(logging.WARNING)



def get_search():
    es = pyelasticsearch.ElasticSearch(es_path)
    try:
        es.refresh()
    except pyelasticsearch.exceptions.ConnectionError:
        return
    return es



def count_org(search):
    results = search.count(None, index=es_index, doc_type=es_doc_type)
    return results["count"]



def verify_org(es, orm, Org, Orgalias):
    len_alias_orm = orm.query(Org).count()
    len_alias_es = count_org(es)
    return len_alias_orm == len_alias_es



def verify(es, orm, Org, Orgalias):
    try:
        if verify_org(es, orm, Org, Orgalias):
            return
    except pyelasticsearch.exceptions.ElasticHttpError:
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
    es.index(es_index, es_doc_type, org_doc(org, alias_list), id=org.org_id)



def index_orgalias(es, orgalias, orm, Orgalias):
    query = orm.query(Orgalias) \
        .filter(Orgalias.org_id == orgalias.org_id) \
        .filter(Orgalias.public == 1)
    alias_list = [orgalias.name for orgalias in query.all()]
    index_org(es, orgalias.org, alias_list=alias_list)



def delete_org(es, org):
    es.delete(es_index, es_doc_type, id=org.org_id)



def build_org(es, orm, Org, Orgalias):
    log.warning("Bulk adding org : start")

    def docs():
        for org in orm.query(Org):
            yield es.index_op(org_doc(org), id=org.org_id)

    for chunk in pyelasticsearch.bulk_chunks(
            docs(), docs_per_chunk=500, bytes_per_chunk=10000):
        es.bulk(chunk, doc_type=es_doc_type, index=es_index)

    log.warning("Bulk adding org : end")

    

def rebuild(es, orm, Org, Orgalias):
    settings_path = os.path.join(setting_path, u"mango.json")

    log.warning("Deleting ES index.")
    try:
        es.delete_index('mango')
    except:
        pass

    settings = json.load(open(settings_path))

    es.create_index(es_index, settings)

    build_org(es, orm, Org, Orgalias)

    

