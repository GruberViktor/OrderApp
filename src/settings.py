from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

with open("credentials.json", "r") as file:
    credentials = json.loads(file.read())

### Printing ###
printers = {
    "A4": "DCP-L3550CDW",
    "labels_groß": "BP730",
    "labels_klein": "QL-500"
}


### Emails ###
smtp_server = credentials["email"]["smtp_server"]
port = credentials["email"]["port"]
login_user = credentials["email"]["email-address"]
login_pwd = credentials["email"]["email-password"]


### languages to translate to
langs = {
    "bg": "Bulgarien",
    "hr": "Kroatien",
    "cs": "Tschechien",
    "da": "Dänemark",
    "et": "Estland",
    "fi": "Finnland",
    "fr": "Frankreich",
    "el": "Griechenland",
    "hu": "Ungarn",
    "is": "Island", 
    "it": "Italien",
    "lv": "Lettland",
    "lt": "Litauen",
    "nl": "Niederlande",
    "no": "Norwegen",
    "pl": "Polen",
    "pt": "Portugal",
    "ro": "Rumänien",
    "es": "Spanien",
    "sk": "Slovakei",
    "sl": "Slovenien",
    "sv": "Schweden",
    "en": "UK, Irland, Malta"
    }


def send_email(from_, to, subject, message):
    server = SMTP(smtp_server, port, "localhost")
    server.starttls()
    server.login(login_user, login_pwd)
    msg = MIMEMultipart()
    msg['From'] = from_
    msg['To'] = str(to)
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))
    server.send_message(msg)
    server.quit()
