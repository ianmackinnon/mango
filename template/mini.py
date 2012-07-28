# -*- coding: utf-8 -*-

visibility_bar = u"""\
<% if (obj.hasOwnProperty("public")) { %>\
<div class="visibility
<%= {true:"public", false:"private", null:"pending"}[obj.public] %>
  ">\
<%= {true:"Public", false:"Private", null:"Pending"}[obj.public] %>\
</div>\
<% } %>\
"""

org_box = u"""
<div class="org-box">
  
  <%=tmpl("visibility_bar", {obj: org})%>
  
  <div class="org_name">
    <a
       href="<%= m.url_rewrite(org["url"], parameters) %>"
       ><%=m.filter.h(org["name"])%></a>
  </div>
  
  <% if (tag && org.tag_list) { %>
  <ul class="tag_list">
    <% for (t in org["tag_list"]) { %>
    <% var tag = org["tag_list"][t]; %>
    <li class="orgtag">
      <a
         href="<%= m.url_rewrite(tag["url"], parameters) %>"
         ><%=m.filter.h(tag["name"])%></a>
    </li>
    <% } %>
  </ul>
  <% } %>

  <% if (org.address_list) { %>
  <div class="org_address_list">
    <% for (a in org["address_list"]) { %>
    <% var address = org["address_list"][a]; %>
    <% if (!m.geo.in(address["latitude"], address["longitude"], geobox)) continue; %>
    <div class="address-row">
      <div class="pin"
	   <%
	      var short_names = new Array();
	      for (t in org["tag"]) {
	      short_names.push(org["tag"][t]["short"]);
	      }
              if ($.inArray("arms-trade", short_names) >= 0) {%>
	color="red"
	<% } else if ($.inArray("peace-group", short_names) >= 0) { %>
	color="green"
	<% } else { %>
	color="<%=short_names%>"
	<% } %>
	all="<%=short_names%>"
	source="mini.py"
        <%if (address["latitude"]) { %>
        latitude="<%=m.filter.h(address["latitude"])%>"
        longitude="<%=m.filter.h(address["longitude"])%>"
        <% } %>
        >
        &nbsp;
      </div>
      <div class="address">
        <%=tmpl("visibility_bar", {obj: address})%>
        <a
           href="<%= m.url_rewrite(address["url"], parameters) %>"
           ><%=m.filter.newline_comma(m.filter.h(address["postal"]))%></a>
      </div>
    </div>
    <% } %>
  </div>
  <% } %>

  <% if (note && org.note_list) { %>
  <div class="note_len">
    <%=org["note_list"].length%>
  </div>
  <% } %>

</div>
"""

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
