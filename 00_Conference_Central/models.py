#!/usr/bin/env python
# models.py -- Udacity conference server-side Python App Engine API; Handles TAsks & MemCaches
# Udacity - NanoDegree FullStack Web Developer - Project 4
#Template by: 'wesc+api@google.com (Wesley Chun)'
# Created by: Vineeta Gupta
# Date: 3 March 2016


import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class Profile(ndb.Model):
    """Profile -- User profile object"""
    userId = ndb.StringProperty()
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)

class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    userId = messages.StringField(1)
    displayName = messages.StringField(2)
    mainEmail = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15

class Conference(ndb.Model):
    """Conference -- Conference object"""
    name            = ndb.StringProperty(required=True)
    description     = ndb.StringProperty()
    organizerUserId = ndb.StringProperty()
    topics          = ndb.StringProperty(repeated=True)
    city            = ndb.StringProperty()
    startDate       = ndb.DateProperty()
    month           = ndb.IntegerProperty()
    endDate         = ndb.DateProperty()
    maxAttendees    = ndb.IntegerProperty()
    seatsAvailable  = ndb.IntegerProperty()

class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name            = messages.StringField(1)
    description     = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics          = messages.StringField(4, repeated=True)
    city            = messages.StringField(5)
    startDate       = messages.StringField(6)
    month           = messages.IntegerField(7, variant=messages.Variant.INT32)
    maxAttendees    = messages.IntegerField(8, variant=messages.Variant.INT32)
    seatsAvailable  = messages.IntegerField(9, variant=messages.Variant.INT32)
    endDate         = messages.StringField(10)
    websafeKey      = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)

class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)

class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)

class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)

    # needed for conference & WishList registration
class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)

class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT

"""
Design Explanation:

Sessions will be created under partucular conference thus reffering to conference as Parent.
Each Conference can have multiple sessions by different speakers.
Session Name is a mandatory field.
Speakers is a free text entry for now, that too case sensitive for now.
As per design there can be only one speaker per session.
Speaker if not provided explicitely, it would be 'Vineeta' by default.
Duration is a integer number with no validations today.
type of Session if not provided explicitly, would be 'Webninar' by default. 
Date if not provided explicitly will put Conference start date by default.
starttime is integer to mark 24 hrs data but does not have any validation implemented for now.
"""
class Session(ndb.Model):
    """Session -- Session object"""
    name            = ndb.StringProperty(required=True)
    webSafeConferenceKey    = ndb.StringProperty()
    highlights      = ndb.StringProperty()
    speaker         = ndb.StringProperty()
    duration        = ndb.IntegerProperty()
    typeOfSession   = ndb.StringProperty()
    date            = ndb.DateProperty()
    startTime       = ndb.IntegerProperty()
    
class SessionForm(messages.Message):
    """SessionForm -- Session outbound form message"""
    name            = messages.StringField(1)
    webSafeConferenceKey    = messages.StringField(2)
    highlights      = messages.StringField(3)
    speaker         = messages.StringField(4)
    duration        = messages.IntegerField(5, variant=messages.Variant.INT32)
    typeOfSession   = messages.StringField(6)
    date            = messages.StringField(7)    
    startTime       = messages.IntegerField(8, variant=messages.Variant.INT32)
    sessionKey      = messages.StringField(9)

class SessionForms(messages.Message):
    """SessionForms -- multiple Sessions outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)

class SessionQueryForm(messages.Message):
    """SessionQueryForm -- Session query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)

class SessionQueryForms(messages.Message):
    """SessionQueryForms -- multiple SessionQueryForm inbound form message"""
    filters = messages.MessageField(SessionQueryForm, 1, repeated=True)

"""
Design Explanation:

Wishlist is an independent Kind to maintain user & sessions relations
It could have been designed to add with Profiles, but Profiles already have ConferenceToAttend relation.
Thus to keep it simple, created another kind. This way all the operations would be fast.

"""
class WishList(ndb.Model):
    """WishList -- WishList object"""
    userId = ndb.StringProperty(required=True)
    sessionKey = ndb.StringProperty(required=True)

class WishListForm(messages.Message):
    """WishListForm -- Wishlist query outbound form message"""
    userId = messages.StringField(1)
    sessionKey    = messages.StringField(2)

class WishListForms(messages.Message):
    """WishListForms -- multiple WishListForm outbound form message"""    
    items = messages.MessageField(WishListForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)