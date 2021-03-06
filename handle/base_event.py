
import datetime

from collections import OrderedDict

from sqlalchemy import and_, exists
from sqlalchemy.sql import func
from tornado.web import HTTPError

from model import User, Event, Address, Eventtag, detach, event_eventtag

from model_v import Event_v, \
    accept_event_address_v

from handle.base import BaseHandler, MangoBaseEntityHandlerMixin



MAX_EVENT_PER_PAGE = 20
MAX_ADDRESS_PER_PAGE = 26
MAX_ADDRESS_PAGES = 3



class BaseEventHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_event(self, event_id, required=True):
        return self._get_entity(
            Event,
            "event_id",
            "event",
            event_id,
            required,
        )

    def _get_event_v(self, event_v_id):
        return self._get_entity_v(
            Event,
            "event_id",
            Event_v,
            "event_v_id",
            "event",
            event_v_id,
        )

    def _touch_event(self, event_id):
        return self._touch_entity(
            Event,
            "event_id",
            "event",
            self._decline_event_v,
            event_id,
        )

    def _create_event(self, id_=None, version=False):
        # pylint: disable=redefined-variable-type
        # Entity may be a previous version ("_v")

        is_json = self.content_type("application/json")

        name = self.get_argument("name", is_json=is_json)
        start_date = self.get_argument_date("start_date", is_json=is_json)
        end_date = self.get_argument_date("end_date", None, is_json=is_json)
        description = self.get_argument("description", None, is_json=is_json)
        start_time = self.get_argument_time("start_time", None, is_json=is_json)
        end_time = self.get_argument_time("end_time", None, is_json=is_json)

        if end_date is None:
            end_date = start_date

        if end_time and not start_time:
            raise HTTPError(
                400, "End time only allowed if start time is also supplied.")

        if end_date < start_date:
            raise HTTPError(
                400, "End date is earlier than start date.")
        if (
                end_date == start_date and
                start_time and
                end_time and
                end_time < start_time
        ):
            raise HTTPError(
                400, "End time is earlier than start time on the same date.")

        public, moderation_user = self._create_revision()

        if version:
            event = Event_v(
                id_,
                name, start_date, end_date,
                description, start_time, end_time,
                moderation_user=moderation_user, public=public)
        else:
            event = Event(
                name, start_date, end_date,
                description, start_time, end_time,
                moderation_user=moderation_user, public=public)

            if id_:
                event.event_id = id_

        detach(event)

        return event

    def _create_event_v(self, event_id):
        return self._create_event(event_id, version=True)

    @staticmethod
    def _decline_event_v(event_id, moderation_user):
        date = datetime.datetime.utcnow().date()

        event = Event_v(
            event_id,
            "DECLINED", date, date,
            moderation_user=moderation_user, public=None)
        event.existence = False

        detach(event)

        return event

    def _event_history_query(self, event_id):
        return self._history_query(
            Event, "event_id",
            Event_v,
            event_id)

    def _get_event_history(self, event_id):
        (event_v_query, event) = self._event_history_query(event_id)

        event_v_query = event_v_query \
            .order_by(Event_v.event_v_id.desc())

        return event_v_query.all(), event

    def _count_event_history(self, event_id):
        (event_v_query, _event) = self._event_history_query(event_id)

        return event_v_query.count()

    def _get_event_latest_a_time(self, event_id):
        # pylint: disable=singleton-comparison
        # Cannot use `is` in SQLAlchemy filters

        event_v = self.orm.query(Event_v.a_time) \
            .join((User, Event_v.moderation_user)) \
            .filter(Event_v.event_id == event_id) \
            .filter(User.moderator == True) \
            .order_by(Event_v.event_v_id.desc()) \
            .first()

        return event_v and event_v.a_time or None

    def _after_event_accept_new(self, event):
        accept_event_address_v(self.orm, event.event_id)

    def _get_event_search_query(
            self, name=None, name_search=None,
            tag_name_list=None,
            tag_all=False,
            visibility=None):

        event_query = self.orm.query(Event)
        event_query = self.filter_visibility(event_query, Event, visibility)

        if name:
            event_query = event_query.filter_by(name=name)
        elif name_search:
            name_column = func.lower(Event.name)
            name_value = name_search.lower()
            event_query = event_query\
                .filter(name_column.contains(name_value))

        if tag_name_list:
            if tag_all:
                for tag_name in tag_name_list:
                    e1 = self.orm.query(event_eventtag) \
                        .filter(event_eventtag.c.event_id == Event.event_id) \
                        .join(Eventtag) \
                        .filter(Eventtag.base_short == tag_name)
                    e1 = self.filter_visibility(
                        e1, Eventtag, visibility, secondary=True)
                    event_query = event_query \
                        .filter(exists(e1.statement))
            else:
                event_query = event_query \
                    .join((Eventtag, Event.eventtag_list)) \
                    .filter(Eventtag.base_short.in_(tag_name_list))
                event_query = self.filter_visibility(
                    event_query, Eventtag, visibility, secondary=True)

            # order by?

        return event_query



    def _get_event_packet_search(self, name=None, name_search=None,
                                 past=False,
                                 tag_name_list=None,
                                 tag_all=False,
                                 location=None,
                                 visibility=None,
                                 offset=None,
                                 page_view="entity"):

        event_query = self._get_event_search_query(
            name=name, name_search=name_search,
            tag_name_list=tag_name_list,
            tag_all=tag_all,
            visibility=visibility)

        date_start = None
        date_end = None
        today = datetime.datetime.today().date()
        if past:
            date_end = today
        else:
            date_start = today

        if date_start:
            event_query = event_query.filter(Event.end_date >= date_start)
        if date_end:
            event_query = event_query.filter(Event.start_date <= date_end)

        if location:
            event_address_query = event_query \
                .join(Event.address_list)
        else:
            event_address_query = event_query \
                .outerjoin(Event.address_list)

        event_address_query = event_address_query \
            .add_entity(Address)
        event_address_query = self.filter_visibility(
            event_address_query, Address, visibility,
            secondary=True, null_column=Address.address_id)

        if location:
            event_address_query = event_address_query \
                .filter(and_(
                    Address.latitude != None,
                    Address.latitude >= location.south,
                    Address.latitude <= location.north,
                    Address.longitude != None,
                    Address.longitude >= location.west,
                    Address.longitude <= location.east,
                    ))

        if past:
            event_address_query = event_address_query \
                .order_by(Event.end_date.desc())
        else:
            event_address_query = event_address_query \
                .order_by(Event.start_date.asc())

        event_packet = {
            "location": location and location.to_obj(),
            }

        if page_view == "marker":
            # Just want markers for all matches.
            event_packet["markerList"] = []
            for event, address in event_address_query:
                event_packet["markerList"].append({
                    "name": event.name,
                    "url": event.url,
                    "latitude": address and address.latitude,
                    "longitude": address and address.longitude,
                })
        elif page_view == "map":
            if (
                    event_address_query.count() >
                    MAX_ADDRESS_PER_PAGE * MAX_ADDRESS_PAGES
            ):
                # More than 3 pages of addresses. Want markers for all matches,
                # and names of the first 10 matching companies (with offset).
                events = OrderedDict()
                event_packet["markerList"] = []
                for event, address in event_address_query:
                    event_packet["markerList"].append({
                        "name": event.name,
                        "url": event.url,
                        "latitude": address and address.latitude,
                        "longitude": address and address.longitude,
                    })
                    if event.event_id not in events:
                        events[event.event_id] = {
                            "event": event,
                            }
                event_packet["eventLength"] = len(events)
                event_packet["eventList"] = []
                for data in list(events.values())[
                        (offset or 0):(offset or 0) + MAX_EVENT_PER_PAGE]:
                    event = data["event"]
                    event_packet["eventList"].append(event.obj(
                        public=self.moderator,
                        description=False,
                    ))

            else:
                # Get all addresses, don't send markers.
                events = OrderedDict()
                for event, address in event_address_query:
                    if event.event_id not in events:
                        events[event.event_id] = {
                            "event": event,
                            "addressList": [],
                            }
                    if address:
                        events[event.event_id]["addressList"].append(
                            address.obj(
                                public=self.moderator,
                                general=address.general(address.postal),
                            )
                        )

                event_packet["eventLength"] = len(events)
                event_packet["eventList"] = []
                for data in list(events.values()):
                    event = data["event"]
                    address_list = data["addressList"]
                    address_list.sort(
                        key=lambda address_obj: address_obj.get(
                            "latitude", None) or 0,
                        reverse=True
                        )
                    event_packet["eventList"].append(event.obj(
                        public=self.moderator,
                        description=False,
                        address_list=address_list,
                    ))
        else:
            # Get all events, no addresses
            events = OrderedDict()
            for event, address in event_address_query:
                if event.event_id not in events:
                    events[event.event_id] = {
                        "event": event,
                        "addressList": [],
                        }
            event_packet["eventList"] = []
            for data in list(events.values()):
                event = data["event"]
                event_packet["eventList"].append(event.obj(
                    public=self.moderator,
                    description=False,
                ))

        return event_packet
