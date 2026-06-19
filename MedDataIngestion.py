import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import date, timedelta
import os
import base64
import pandas as pd
import io
from datetime import datetime
import subprocess
import shutil
import logging
from email.message import EmailMessage
import numpy as np

# Define the permissions your app needs
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# create log folder
today = str(date.today())
os.makedirs(os.path.join("logs", today), exist_ok=True)


logging.basicConfig(
    filename=os.path.join("logs", str(date.today()), "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")

def authenticate_gmail():
    """Handles OAuth 2.0 authentication and returns a service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    # Build the Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service

# Get the authenticated service
gmail_service = authenticate_gmail()
logging.info("Authentication successful. Service object created.")

def sendEmail(subject, message="", email="sueannetan@snoc.org.sg"):
    service = gmail_service

    newMessage = EmailMessage()
    newMessage.set_content(message)
    
    newMessage["To"] = email
    newMessage["From"] = "me"
    newMessage["Subject"] = subject

    # Encode message
    encoded_message = base64.urlsafe_b64encode(newMessage.as_bytes()).decode()

    create_message = {
        'raw': encoded_message
    }

    send_message = service.users().messages().send(
        userId="me",
        body=create_message
    ).execute()

    logging.info(f'Message Id: {send_message["id"]}')
    
def retrieveMedData(service, user_id='me', max_results=5):
    """Retrieve the injury surveillance from yesterday"""
    #dayBefore = date.today() - timedelta(days=2)
    try:
        # Call the Gmail API
        results = service.users().messages().list(
            userId=user_id, maxResults=max_results, labelIds=['INBOX'], q="from:sueannetan.ssi@gmail.com subject:[RTT-RTP ra16x2druw] Daily injury cases after:" +str(date.today())).execute()
        messages = results.get('messages', [])

        if not messages:
            return []

        full_messages = []
        for msg in messages:
            full_msg = service.users().messages().get(
                userId=user_id,
                id=msg['id']
            ).execute()
            full_messages.append(full_msg)

        # Sort by internalDate (descending = latest first)
        latest_message = sorted(
            full_messages,
            key=lambda x: int(x['internalDate']),
            reverse=True
        )[0]

        medDataFrames = []

        # Extract attachments from latest message
        for part in latest_message['payload'].get('parts', []):
            if part.get('filename'):  # has attachment
                attachment_id = part['body'].get('attachmentId')

                attachment = service.users().messages().attachments().get(
                    userId=user_id,
                    messageId=latest_message['id'],
                    id=attachment_id
                ).execute()

                fileData = base64.urlsafe_b64decode(attachment['data'])

                # Save locally (optional)
                os.makedirs("downloads", exist_ok=True)
                path = os.path.join("downloads", str(date.today())+ "_" +part['filename'])
                with open(path, 'wb') as f:
                    f.write(fileData)

                logging.info(f"Downloaded: {part['filename']}")

                try:
                    df = pd.read_excel(io.BytesIO(fileData))
                    medDataFrames.append(df)
                except Exception as error:
                    logging.exception(f'Error could not convert attachment to dataframe: {error}')
                    sendEmail(subject="RTT/RTP: Error could not convert attachment to dataframe")
                    return []

                # Stop after 2 attachments if desired
                if len(medDataFrames) == 2:
                    break

        return medDataFrames

    except Exception as error:
        logging.exception(f'An error occurred: {error}')
        return []

# Import mapping file
mappingDf = pd.read_excel(os.path.join("mapping", "mapping.xlsx"))

# Retrieve file from email and assign to dataframes
messages = retrieveMedData(gmail_service)

if not messages:

    logging.info("No email messages found")
    sendEmail(subject="Error: Last RTT/RTP received no messages")

else:
  
    if 'Sport' in messages[0].columns:
        mergedDF = pd.merge(messages[1], messages[0][["PCNO","Sport", "SP Code", "Service Provider"]], on=['PCNO','SP Code'], how="left")
    elif 'Sport' in messages[1].columns:
        mergedDF = pd.merge(messages[0], messages[1][["PCNO","Sport", "SP Code", "Service Provider"]], on=['PCNO','SP Code'], how="left")
    else:
        logging.error("Failed to merge both datasources.")

    mergedDF = mergedDF.replace(r'^\s*$', np.nan, regex=True)
    if not mergedDF.empty and not mergedDF.dropna(how="all").empty:
        finalDf = mergedDF[['Name', 'VisitDate', 'Sport', 'Event Played', 'Service Provider', 'Body Part Affected', 'Injury Diagnosis', 'Position Played', 'Hand/ Leg Dominance']]
        finalDf = finalDf.rename(columns={
                                'Event Played': 'New / Subsequent Injury',
                                'Service Provider': 'Attending Practitioner',
                                "Position Played": "Traffic Light Status",
                                "Hand/ Leg Dominance": "Comments",
                                "VisitDate": "Visit Date"
        })
        finalDf['First Name'] = finalDf['Name'].map(mappingDf.set_index('Name')['First Name'])
        finalDf['Last Name'] = finalDf['Name'].map(mappingDf.set_index('Name')['Last Name'])
        finalDf['Date'] = pd.to_datetime(date.today()).strftime("%d-%m-%Y")
        finalDf['Time'] = datetime.now().time()
        finalDf['Visit Date'] = pd.to_datetime(finalDf['Visit Date']).dt.strftime("%d-%m-%Y")

        #handle unmapped athletes
        unmappedAthletes = finalDf[finalDf['First Name'].isna()]
        logging.warning("Some athletes were unmapped: " +unmappedAthletes['Name'].to_string())
        sendEmail(subject="RTT/RTP: Some athletes were unmapped", message=unmappedAthletes.to_string())

        finalDf = finalDf.drop("Name", axis=1)
        finalDf = finalDf[["First Name", "Last Name", "Date", "Time", "Visit Date", "Sport", "New / Subsequent Injury", "Attending Practitioner", "Body Part Affected", "Injury Diagnosis",	"Traffic Light Status",	"Comments"]]

        #drop all unmapped athletes
        finalDf = finalDf.dropna(subset=['First Name'])

        #send out email notif to whoever is needed
        for index, row in finalDf.iterrows():
            msgString = (
                "Hi,\nThere has been an updated status for athlete "
                + row["First Name"] + " " + row["Last Name"] + " of " + row["Sport"]
                + ".\nNew / Subsequent Injury: " + row["New / Subsequent Injury"] + "\n"
                + "Traffic Light Status: " + row["Traffic Light Status"] + "\n"
                + "Injury Diagnosis: " + row["Injury Diagnosis"] + "\n"
                + "Body Part Affected: " + row["Body Part Affected"] + "\n"
                + "Comments: " + row["Comments"] + "\n"
                + "Recorded by " + row["Attending Practitioner"] + " on " + row["Visit Date"]
            )
            sendEmail(message=msgString, subject="RTT/RTP: Traffic light status changed for athlete")

        os.makedirs("templates", exist_ok=True)
        finalDf.to_csv(os.path.join("templates", "templates.csv"), index=False)

        result = subprocess.run("npx playwright test --headed --project=chromium --reporter=html --output=logs/"+str(today), shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            sendEmail(subject="RTT/RTP: Playwright automation passed")
        else:
            sendEmail(subject="RTT/RTP: Playwright automation failed")

        shutil.move("playwright-report", os.path.join("logs", today, "playwright-report"))
    else:
        logging.info("RTT/RTP: No cases today")
        sendEmail("RTT/RTP: No cases today")
        exit()