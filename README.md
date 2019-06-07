## Follow-Up

A flask server, which serves an endpoint to send an email (with custom body and attached image) to all guests who attended the most recent meeting ((scheduled on Google Calendar).

### How it works

* Once the request is sent to the API, it checks the logged-in user's calendar to find his most recent meeting.
* From this meeting event, it extracts the email ids (if visible) of all the attendees
* An email is then created (body of the email, and an image attachment can be sent as part of the request)
* This email is then sent to each of the attendees

### How to use

* Clone this repository
* Create a project on [Google Cloud Engine](https://console.cloud.google.com/)
* Give this project access to Gmail API and Google Calendar API
* Create a credential (of type OAuth client ID). Set up the OAuth Consent screen. In the "Scopes for Google APIs" section, add these additional scopes:
    * ../auth/calendar.readonly
    * ../auth/gmail.compose
* Once the credential has been created, download it, and save it into the `config` folder of the cloned project as `credentials.json`
* Create a virtual environment if needed.
* Install the requirements. `pip install -r requirements.txt`
* Run the server: `python app.py`
    * If this is the first time running, it will open a browser, asking the user to login into Google. Once this is successful, a `token.pickle` file will be created in the `config` folder. This will save the session, and there will be no need to login again.
* The server should be running now. The endpoint to be used is `/sendnotes`, and the data should be sent as POST.
* Sample Requests:
    * `curl -X POST http://localhost:5000/sendnotes`
    * `curl -X POST http://localhost:5000/sendnotes -F "body=Minutes of the Meeting"`
    * `curl -X POST http://localhost:5000/sendnotes -F "body=Minutes of the Meeting" -F "image=@/some/path/to/image.jpg"`