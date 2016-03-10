
## PROJECT

Vineeta Conference Central - App Engine - Project 4 - Full Stack Web Developer - Nanodegree - Udacity

---------------------------------


## PROJECT DESCRIPTION

This is  Conference Central application where each conference has name, description and date when the conference happens. User can create multiple sessions, with different speakers, maybe some of them happening in parallel! User can register to any conference depending on seats available. Also can create/view/delete sessions in a particular conference. User can also add the sessions in their wishlist. If there are multiple sessions of the same speaker then those featured speaker sessions can also be listed.

---------------------------------

## COPYRIGHT INFO

Author: Vineeta Gupta
Version: 1.0
Available At: GitHub
Copyright: March 2016 All rights reserved

---------------------------------
## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting
   your local server's address (by default [localhost:8080][5].)
1. Generate your client library(ies) with [the endpoints tool][6].
1. Deploy your application.


[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool

---------------------------------
##Design Explanation for Session & Speaker:

Sessions will be created under partucular conference thus reffering to conference as Parent.
Each Conference can have multiple sessions by different speakers.
Session Name is a mandatory field.
Speakers is a free text entry for now, also case sensitive for now.
As per design there can be only one speaker per session.
Speaker if not provided explicitely, it would be 'Vineeta' by default.
Duration is a integer number with no validations today.
type of Session if not provided explicitly, would be 'Webninar' by default. 
Date if not provided explicitly will put Conference start date by default.
starttime is integer to mark 24 hrs data but does not have any validation implemented for now.
