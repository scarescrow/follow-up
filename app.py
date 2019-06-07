from __future__ import print_function
import datetime
import pytz
import pickle
import os
import base64
import mimetypes
import json
from flask import Flask, request
from flask_cors import CORS
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

app = Flask(__name__)
CORS(app)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/gmail.compose']
MINIMUM_HOURS_LOOKUP = 2
SELF_EMAIL_ID = "qwe@asd.co"
IMAGE_SAVE_FOLDER = "workspace"
TIMEZONE = None

calendar_service = None
mail_service = None

def get_session():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('config/token.pickle'):
        with open('config/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'config/credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def create_message_with_attachment(sender, to, subject, message_text, file=None):
  """Create a message for an email.

  Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.
    file: The path to the file to be attached.

  Returns:
    An object containing a base64url encoded email object.
  """
  message = MIMEMultipart()
  message['to'] = ",".join(to)
  message['from'] = sender
  message['subject'] = subject

  msg = MIMEText(message_text)
  message.attach(msg)

  if file:
      content_type, encoding = mimetypes.guess_type(file)
      main_type, sub_type = content_type.split('/', 1)
      fp = open(file, 'rb')
      msg = MIMEImage(fp.read(), _subtype=sub_type)
      fp.close()

      filename = os.path.basename(file)
      msg.add_header('Content-Disposition', 'attachment', filename=filename)
      message.attach(msg)

  return {'raw': base64.urlsafe_b64encode(message.as_string().encode('utf8')).decode('utf8')}

def send_message(service, message, user_id="me"):
  """Send an email message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.

  Returns:
    Sent Message.
  """
  try:
    message = (service.users().messages().send(userId=user_id, body=message)
               .execute())
    print('Message Id: %s' % message['id'])
    return message
  except errors.HttpError as error:
    print('An error occurred: %s' % error)

def get_attendees(service):
    global TIMEZONE

    attendees = []

    # Set the timezon to be the same as the User's calendar
    if not TIMEZONE:
      TIMEZONE = service.settings().get(setting="timezone").execute()["value"]
      
    tz = pytz.timezone(TIMEZONE)
    
    # Call the Calendar API
    now = datetime.datetime.now(tz)
    end = now.isoformat()
    start = (now + datetime.timedelta(hours= -1 * MINIMUM_HOURS_LOOKUP)).isoformat()

    # Look for 10 events in this window
    print('Getting the 10 events in this {} hour window'.format(MINIMUM_HOURS_LOOKUP))
    events_result = service.events().list(calendarId='primary', timeMax=end,
                                        timeMin=start, maxResults=10, singleEvents=True, 
                                        orderBy="startTime").execute()
    events = events_result.get('items', [])

    if not events:
        print('No recent events found.')
        summary = ""
        start = ""
        attendees = []

    else:
        # Pick the last event from response
        # (which is the most recent event)
        current_event = events[-1]
        start = current_event['start'].get('dateTime', current_event['start'].get('date'))
        summary = current_event["summary"]
        attendees = [i["email"] for i in current_event.get("attendees", []) if "email" in i]
        
    return summary, start, attendees

@app.route("/sendnotes", methods=["POST"])
def sendnotes():
    # First, get list of meeting attendees
    summary, start_time, attendees = get_attendees(calendar_service)

    if len(attendees) == 0:
      return json.dumps({"message": "No recent events found"})

    # Start creating email body
    message_subject = "Meeting Notes"
    message_body = request.values.get("body")
    if not message_body:
        message_body = "Here are the meeting notes for the meeting {} on {}".format(summary, start_time)

    image = request.files.get("image")
    save_file_path = None

    if image:
        extension = image.filename.rsplit('.', 1)[1].lower()
        save_file_path = os.path.join(IMAGE_SAVE_FOLDER, "notes.{}".format(extension))
        image.save(save_file_path)

    message_content = create_message_with_attachment(SELF_EMAIL_ID, attendees, 
      message_subject, message_body, save_file_path)

    # Now, send email
    response = send_message(mail_service, message_content)
    return json.dumps(response)

if __name__ == '__main__':
    # Log in and get credentials
    creds = get_session()

    # Build the API services
    calendar_service = build('calendar', 'v3', credentials=creds)
    mail_service = build('gmail', 'v1', credentials=creds)

    # message_content = create_message_with_attachment(SELF_EMAIL_ID, ["sagnik.sinharoy@gmail.com", "thescarecrow14@gmail.com"], "Testing code", "Hello there!")
    # message = send_message(mail_service, message_content)
    # print(message)

    app.run()

    