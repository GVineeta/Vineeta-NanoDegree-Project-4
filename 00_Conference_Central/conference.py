#!/usr/bin/env python
# conference.py -- Udacity conference server-side Python App Engine API; uses Google Cloud Endpoints
# Udacity - NanoDegree FullStack Web Developer - Project 4
#Template by: wesc on 2014 apr 21
# Created by: Vineeta Gupta
# Date: 3 March 2016

#import all the required modules

from datetime import datetime
import json
import os
import time

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize

from utils import getUserId
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms

from models import Session
from models import SessionForm
from models import SessionForms
from models import SessionQueryForm
from models import SessionQueryForms

from models import WishList
from models import WishListForm
from models import WishListForms

from models import BooleanMessage
from models import ConflictException

from settings import WEB_CLIENT_ID

from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import StringMessage
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "ANNOUNCEMENT_NEW"
MEMCACHE_FEATURED_SPEAKER_KEY = "FEATURED_SPEAKER"
DEFAULTS = {
        "city": "Default City",
        "maxAttendees": 0,
        "seatsAvailable": 0,
        "topics": [ "Default", "Topic" ],
    }
SESSION_DEFAULTS = {
        "highlights": "Web Architecture",
        "speaker": "Vineeta",
        "duration": 1,
        "typeOfSession": "Webninar",
        "startTime":1,
    }
OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }
FIELDS =    {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#Requets
CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)
SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1),
)
CONF_SESSION_TYPE_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    typeOfSession=messages.StringField(1),
    websafeConferenceKey=messages.StringField(2),
)
WISHLIST_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sessionKey=messages.StringField(1),
)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@endpoints.api( name='conference',
                version='v1',
                allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
                scopes=[EMAIL_SCOPE])

class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        profile = None
        userID = getUserId(user)
        userID_key = ndb.Key(Profile, userID)
        profile = userID_key.get()
        # If Profile not in datastore already, create new
        if not profile:
            profile = Profile(
                userId = userID,
                key = userID_key,
                displayName = user.nickname(), 
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
        profile.put()
        return profile

    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()
        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
            prof.put()
        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
            path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
            path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)
        # Check if Conferenece name provided
        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        # both for data model & outbound Message
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
            setattr(request, "seatsAvailable", data["maxAttendees"])

        # make Profile Key from user ID
        p_key = ndb.Key(Profile, user_id)
        # allocate new Conference ID with Profile key as parent
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        # make Conference key from ID
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference & return (modified) ConferenceForm
        Conference(**data).put()
        # Add a task to send a mail to owner when ever new conference is added
        taskqueue.add(params={'email': user.email(),
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )

        return request

    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
            http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # return ConfrenceForms
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") \
            for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
        path='getConferencesCreated',
        http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # make profile key
        p_key = ndb.Key(Profile, getUserId(user))
        # create ancestor query for this user
        conferences = Conference.query(ancestor=p_key)
        # get the user profile and display name
        prof = p_key.get()
        displayName = getattr(prof, 'displayName')
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, displayName) for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
        path='filterPlayground',
        http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Return Medical Innovations Conferences happening in Londan"""
        
        q = Conference.query()
        
        # Filter Conferences on City = London
        field = "city"
        operator = "="
        value = "London"
        f = ndb.query.FilterNode(field, operator, value)
        q = q.filter(f)

        # Filter Conferences on topics = Medical Innovations
        field = "topics"
        operator = "="
        value = "Medical Innovations"
        f = ndb.query.FilterNode(field, operator, value)
        q = q.filter(f)
        
        # Filter Conferences where maxAttendes is greater then 10
        q = q.filter(Conference.maxAttendees > 10)

        # Order Conferences on name
        q = q.order(Conference.name)

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser() # get user Profile

        # check if conf exists given websafeConfKey
        
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        # check if conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)
        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)

# - - - Query Conferences - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
            path='conference/detail/{websafeConferenceKey}',
            http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""

        prof = self._getProfileFromUser() # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck) for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf, "")\
         for conf in conferences]
        )

# - - - Session Objects - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(SessionForm, SessionForm, path='sesion',
                http_method='POST', name='createSession')
    def createSession(self, request):
        """Create new Session for a particular Conference."""
        
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # Check if the conference exists
        wsck = request.webSafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # Check if the Session name provided
        if not request.name:
            raise endpoints.BadRequestException("Session 'name' field required")

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        # Delete the sesison Key property coming from SessionForm
        del data['sessionKey']
        # add default values for those missing (both data model & outbound Message)
        for df in SESSION_DEFAULTS:
            if data[df] in (None, []):
                data[df] = SESSION_DEFAULTS[df]
                setattr(request, df, SESSION_DEFAULTS[df])

        # convert dates from strings to Date objects; If date is already not there then set the conference start date
        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10], "%Y-%m-%d").date()
        else:
            data['date'] = conf.startDate

        # allocate new Session ID with Conference key as parent
        c_id = conf.key.id()
        c_key = ndb.Key(Conference, c_id)
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        # make session key from ID
        s_key = ndb.Key(Session, s_id, parent=c_key)
        data['key'] = s_key
        data['webSafeConferenceKey'] = request.webSafeConferenceKey
        Session(**data).put()
        # Add a task which will identify featured speaker & add it to memcache 
        # if this speaker has many sessions in this conference
        taskqueue.add(params={'speaker': data['speaker'],
            'confId': request.webSafeConferenceKey},
            url='/tasks/identify_featured_speaker'
        )
        
        return request

    @endpoints.method(CONF_GET_REQUEST, SessionForms, path='allSesions/{websafeConferenceKey}',
                    http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Return sessions under this conf key."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        s = Session.query()
        # get the sessions of this conference
        field = "webSafeConferenceKey"
        operator = "="
        value = request.websafeConferenceKey
        f = ndb.query.FilterNode(field, operator, value)
        s = s.filter(f)
        # return set of SessionForm objects per Session
        return SessionForms(
            items=[self._copySessionToForm(ses) for ses in s]
            
        )

    def _copySessionToForm(self, ses):
        """Copy relevant fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(ses, field.name):
            # convert Date to date string; just copy others
                if field.name.endswith('date'):
                    setattr(sf, field.name, str(getattr(ses, field.name)))
                else:
                    setattr(sf, field.name, getattr(ses, field.name))
            elif field.name == "sessionKey":
                setattr(sf, field.name, ses.key.urlsafe())
        sf.check_initialized()
        return sf   
    
    @endpoints.method(SPEAKER_GET_REQUEST, SessionForms, path='speakerSesions/{speaker}',
                    http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Return sessions by this speaker."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        s = Session.query()
        # Look for the sessions by this speaker
        field = "speaker"
        operator = "="
        value = request.speaker
        f = ndb.query.FilterNode(field, operator, value)
        s = s.filter(f)
        # return set of SessionForm objects per Session
        return SessionForms(
            items=[self._copySessionToForm(ses) for ses in s]
            
        )

    @endpoints.method(CONF_SESSION_TYPE_GET_REQUEST, SessionForms, path='getConferenceSessionsByType/{typeOfSession}/{websafeConferenceKey}',
                        http_method='GET', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Return sessions by its type."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        s = Session.query()
        # Look for sessions under this particular conference
        field = "webSafeConferenceKey"
        operator = "="
        value = request.websafeConferenceKey
        f = ndb.query.FilterNode(field, operator, value)
        s = s.filter(f)
        # Look for sessions under this type
        field = "typeOfSession"
        operator = "="
        value = request.typeOfSession
        f = ndb.query.FilterNode(field, operator, value)
        s = s.filter(f)
        # return set of SessionForm objects per Session
        return SessionForms(
            items=[self._copySessionToForm(ses) for ses in s]
            
        )

# - - - WishList Objects - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(WISHLIST_GET_REQUEST, WishListForm, path='addSessionToWishlist/{sessionKey}',
                        http_method='GET', name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Add particular Session to users wishlist"""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
               
        # make sure session Key is provided
        if not request.sessionKey:
            raise endpoints.BadRequestException("Session 'key' field required")

        # make sure the session Key provided is already there in datastore
        skey = request.sessionKey
        sess = ndb.Key(urlsafe=skey).get()
        if not sess:
            raise endpoints.NotFoundException(
                'No Session found with key: %s' % sess)

        # Check if the user has already added this session in wishlist earlier
        userID = getUserId(user)
        w = WishList.query(ndb.AND(
            WishList.userId == userID,
            WishList.sessionKey == request.sessionKey)
        ).fetch()
        if w:
            raise ConflictException("You have already added this session to wishlist")

        # copy WishListForm/ProtoRPC Message into dict
        data= {}
       
        data['userId'] = userID
        data['sessionKey'] = request.sessionKey
        
        #  Store the data in data store
        WishList(**data).put()

        # return WishListForm
        wlf = WishListForm()
        wlf.userId = userID
        wlf.sessionKey = request.sessionKey
        wlf.check_initialized()

        return wlf  

    @endpoints.method(message_types.VoidMessage, WishListForms, path='getSessionsInWishlist',
                        http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Return sessions under this users wishlist."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get users wishlist
        userID = getUserId(user)
        wishLists = WishList.query(WishList.userId == userID).fetch()
        
        # Return wishlistforms
        return WishListForms(
            items=[self._copyWishListToForm(w) for w in wishLists]
            
        )

    def _copyWishListToForm(self, w):
        """Copy relevant fields from WishList to WishListForm."""
        wf = WishListForm()
        for field in wf.all_fields():
            setattr(wf, field.name, getattr(w, field.name))

        wf.check_initialized()
        return wf   


    @endpoints.method(WISHLIST_GET_REQUEST, BooleanMessage, path='deleteSessionInWishlist/{sessionKey}',
                    http_method='GET', name='deleteSessionInWishlist')
    def deleteSessionInWishlist(self, request):
        """Delete a particular Session from Wishlist."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # Get the session of this user from wishlist
        userID = getUserId(user)
        w = WishList.query(ndb.AND(
            WishList.userId == userID,
            WishList.sessionKey == request.sessionKey)
        ).fetch()        
        retval = True
        # Check if the session which is asked to delate exists or not
        if not w:
            raise ConflictException("You dont have this session in the wishlist")
            retval=False
        else:
            # if session exists then delete from wishlist
            for tmp in w:
                tmp.key.delete()
            retval=True

        return BooleanMessage(data=retval)

# - - - Memcache Additions - - - - - - - - - - - - - - - - - - - -


    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement of conferences whose seats left are less then 5 & assign to memcache"""
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @staticmethod
    def _identifyFeatureSpeaker(speaker,confId):
        """identify featured speaker of a particular conference & assign to memcache"""
        sessions = Session.query(ndb.AND(
            Session.webSafeConferenceKey == confId,
            Session.speaker == speaker)
        ).fetch(projection=[Session.name])

        if sessions:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            featuredSpeaker = '%s %s %s' % (
                speaker,'has the following sessions --------',','.join(session.name for session in sessions))
            memcache.set(MEMCACHE_FEATURED_SPEAKER_KEY, featuredSpeaker)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            featuredSpeaker = ""
            memcache.delete(MEMCACHE_FEATURED_SPEAKER_KEY)
        
        return featuredSpeaker

    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        # return an existing announcement from Memcache or an empty string.
        announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        if not announcement:
            announcement = ""
        return StringMessage(data=announcement)


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/getFeaturedSpeaker',
            http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Return featured speaker from memcache."""
        # return a featured speaker from Memcache or an empty string.
        featuredSpeaker = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        if not featuredSpeaker:
            featuredSpeaker = "" 
        return StringMessage(data=featuredSpeaker)

# - - - Endpoints for Indexes Queries - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(CONF_GET_REQUEST, StringMessage, path='getConferenceSpeakers/{websafeConferenceKey}',
                        http_method='GET', name='getConferenceSpeakers')
    def getConferenceSpeakers(self, request):
        """Return all the Speakers under this Conference."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get sessions of this conference
        sessions = Session.query(Session.webSafeConferenceKey == request.websafeConferenceKey).fetch()
        speakers = ' %s %s' % (
                'The speakers of the selected conference are --------',','.join(session.speaker for session in sessions))
        
        # Return Speaker List
        return StringMessage(data=speakers)

    @endpoints.method(CONF_GET_REQUEST, StringMessage, path='getConferenceRegisterdUsers/{websafeConferenceKey}',
                        http_method='GET', name='getConferenceRegisterdUsers')
    def getConferenceRegisterdUsers(self, request):
        """Return all the registered users of this Conference."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get users who has this conference in their attend list OR in other words have registered to
        profiles = Profile.query(Profile.conferenceKeysToAttend == request.websafeConferenceKey).fetch()
        users = ' %s %s' % (
                'The Users registered for the selected conference are --------',','.join(user.displayName for user in profiles))
        
        # Return users List
        return StringMessage(data=users)

    @endpoints.method(message_types.VoidMessage, StringMessage, path='getFilteredSessions',
                        http_method='GET', name='getFilteredSessions')
    def getFilteredSessions(self, request):
        """Return all the sessions of this Conference where typeOfSession!='Workshop' AND starttime <= (18-duration)."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        
        # get sessions != Workshop
        sessions = Session.query(ndb.OR(
            Session.typeOfSession > 'Workshop',
            Session.typeOfSession < 'Workshop'
            )).fetch()
        
        fSessions=[]

        # check for sessions not starting at 7
        for session in sessions:            
            if session.startTime < 19: # 19 is 7 pm
                fSessions.append(session)


        filteredSessions = ' %s %s' % (
                'The filtered sessions are --------',','.join(session.name for session in fSessions))
        
        # Return filteredSessions List
        return StringMessage(data=filteredSessions)

        
# registers API
api = endpoints.api_server([ConferenceApi]) 
