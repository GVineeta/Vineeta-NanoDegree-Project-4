# main.py -- Udacity conference server-side Python App Engine API; Handles TAsks & MemCaches
# Udacity - NanoDegree FullStack Web Developer - Project 4
# Created by: Vineeta Gupta
# Date: 3 March 2016

import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi

class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()


class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )

class IdentifyFeatureSpeakerHandler(webapp2.RequestHandler):
    def post(self):
        """Identify the speaker & put in memcache."""
        ConferenceApi._identifyFeatureSpeaker(self.request.get('speaker'),self.request.get('confId'))
        
app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/identify_featured_speaker', IdentifyFeatureSpeakerHandler),
], debug=True)
