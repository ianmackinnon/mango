#!/usr/bin/env python3

import re
import json
import urllib.request
import urllib.parse
import urllib.error
import httplib2


SESSION_COOKIE = "mango-session"


def get_session(http):
    http.follow_redirects = False
    (res, _body) = HTTP.request("http://localhost:8802/auth/login/local")
    session_ = res["set-cookie"]
    session_ = re.sub('^.*"(.*)".*$', "\\1", session_)
    return session_



def make_note(text, source):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/note",
        "POST",
        headers=headers,
        body=json.dumps({"text": text, "source": source}),
    )
    assert res.status == 200
    return json.loads(body)

def get_one_note(text, source):
    headers = {
        "Accept": "application/json",
        }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    uri = "http://localhost:8802/note?text=%s,source=%s" % (
        urllib.parse.quote_plus(text), urllib.parse.quote_plus(source))
    res, body = HTTP.request(
        uri,
        headers=headers,
    )
    assert res.status == 200, repr((res, body))
    try:
        obj_list = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    if not obj_list:
        return None
    if len(obj_list) == 1:
        return obj_list[0]
    raise Exception(repr(obj_list))

def get_or_make_note(text, source):
    return get_one_note(text, source) or make_note(text, source)

def update_note(note):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802%s" % note["url"],
        "PUT",
        headers=headers,
        body=json.dumps(note)
    )
    assert res.status == 200, repr((res, body))
    try:
        obj = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    return obj



def make_organisation(name):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/organisation",
        "POST",
        headers=headers,
        body=json.dumps({"name": name}),
    )
    assert res.status == 200
    return json.loads(body)

def get_organisation_by_id(id_):
    headers = {
        "Accept": "application/json",
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/organisation/%d" % id_,
        headers=headers,
    )
    assert res.status == 200, repr((res, body))
    try:
        obj = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    if not obj:
        return None
    return obj

def get_one_organisation(name):
    headers = {
        "Accept": "application/json",
        }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/organisation?name=%s" % urllib.parse.quote_plus(name),
        headers=headers,
    )
    assert res.status == 200, repr((res, body))
    try:
        obj_list = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    if not obj_list:
        return None
    if len(obj_list) == 1:
        return obj_list[0]
    raise Exception(repr(obj_list))

def get_or_make_organisation(name):
    return get_one_organisation(name) or make_organisation(name)

def update_organisation(organisation):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802%s" % organisation["url"],
        "PUT",
        headers=headers,
        body=json.dumps(organisation)
    )
    assert res.status == 200, repr((res, body))
    try:
        obj = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    return obj



def make_organisation_tag(name):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/organisation-tag",
        "POST",
        headers=headers,
        body=json.dumps({"name": name})
    )
    assert res.status == 200, repr((res, body))
    return json.loads(body)

def get_one_organisation_tag(name):
    headers = {
        "Accept": "application/json",
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802/organisation-tag?name=%s" % urllib.parse.quote_plus(
            name),
        headers=headers,
    )
    assert res.status == 200, repr((res, body))
    try:
        obj_list = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    if not obj_list:
        return None
    if len(obj_list) == 1:
        return obj_list[0]
    raise Exception(repr(obj_list))

def get_or_make_organisation_tag(name):
    return get_one_organisation_tag(name) or make_organisation_tag(name)

def update_organisation_tag(tag):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802%s" % tag["url"],
        "PUT",
        headers=headers,
        body=json.dumps(tag)
    )
    assert res.status == 200, repr((res, body))
    try:
        obj = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    return obj



def update_address(address):
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    res, body = HTTP.request(
        "http://localhost:8802%s" % address["url"],
        "PUT",
        headers=headers,
        body=json.dumps(address)
    )
    assert res.status == 200, repr((res, body))
    try:
        obj = json.loads(body)
    except ValueError as e:
        print(body)
        raise e
    return obj



def address_add_note(address, note):
    address["note_id"] = list(
        set(address["note_id"]) | set([note["id"]])
    )



def organisation_add_note(organisation, note):
    organisation["note_id"] = list(
        set(organisation["note_id"]) | set([note["id"]])
    )



def organisation_tag_add_note(tag, note):
    tag["note_id"] = list(
        set(tag["note_id"]) | set([note["id"]])
    )



def organisation_add_tag(organisation, tag):
    organisation["tag_id"] = list(
        set(organisation["tag_id"]) | set([tag["id"]])
    )



def organisation_add_address(organisation, postal, source):
    # Only if it doesn't already exist
    for address in organisation["address"]:
        if address["postal"] == postal:
            if address["lookup"] is not None:
                break
            if address["manual_longitude"] is not None:
                break
            if address["manual_latitude"] is not None:
                break
            return organisation
    headers = {
        'Content-type': 'application/json',
        "Accept": "application/json",
        "Cookie": "%s=%s" % (SESSION_COOKIE, SESSION),
    }
    HTTP.follow_redirects = True
    HTTP.follow_all_redirects = True
    data = json.dumps({"postal": postal, "source": source})
    print(data)
    res, body = HTTP.request(
        "http://localhost:8802%s/address" % organisation["url"],
        "POST",
        headers=headers,
        body=data,
    )
    assert res.status == 200, repr((res, body))
    return json.loads(body)



HTTP = httplib2.Http(cache=None)
SESSION = get_session(HTTP)
