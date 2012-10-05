# -*- coding: utf-8 -*-

org_li = u"""
  <li class="tag">
    <span class="org_name">
      <a
         href="<%= m.url_rewrite(org["url"], parameters) %>"
         ><%=m.filter.h(org["name"])%></a>
    </span>
  </li>
"""

tag_li = u"""
<li class="tag">\
<span class="tag_name">\
<a
   href="<%= m.url_rewrite(tag["url"], parameters) %>"
   ><%=m.filter.nbsp(m.filter.h(tag["name"]))%></a>\
</span>\
\
<% if (org) { %>\
&nbsp;\
(\
<span class="org_len">\
<% if (tag["org_len"]) { %>\
<a
   href="<%= m.url_rewrite(tag["org_list_url"], parameters) %>"
   >\
<% } %>\
<%=tag["org_len"]%>\
<% if (tag["org_len"]) { %>\
</a>\
<% } %>\
</span>\
)\
<% } %>\
\
<% if (note && tag["note_len"]) { %>\
<span class="has-notes">…</span>\
<% } %>\
\
<% if (visibility && "public" in tag) { %>\
&nbsp;\
<%=tmpl("visibility_bar", {obj: tag})%>\
<% } %>\
</li>\
"""


u"""

"""
