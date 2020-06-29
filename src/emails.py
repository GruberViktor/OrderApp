from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from settings import credentials

def send_tracking_email(order, tracking_code):
    e = credentials["email"]
    server = SMTP(e["server"], e["port"], "localhost")
    server.starttls()
    server.login(e["email-address"], e["email-password"])
    
    msg = MIMEMultipart()
    

    if order["website"] == "https://www.fermentationculture.eu":
        msg['From'] = "fermentationculture.eu <office@fermentationculture.eu>"
        msg['To'] = str(order["billing"]["email"])
        msg['Subject'] = "[fermentationculture.eu] Your tracking link"

        if order["billing"]["first_name"] is not "":
            greeting = "Hi " + order["billing"]["first_name"].capitalize() + ","
        else:
            greeting = "Good day,"

        text = """{greeting}<br>

            <p>you can track your order from fermentationculture.eu at this link: <a href="https://www.post.at/track/{tracking_code}">https://www.post.at/track/{tracking_code}</a></p>

            <p>Please be aware that it might take a few hours for the tracking information to be up to date.</p>

            <p>Thanks for your order!</p>

            <p>Kind regards,<br>
            Viktor and Christine</p>
            """.format(
                greeting = greeting,
                tracking_code = tracking_code
                )

        msg.attach(MIMEText(text, 'html'))

    elif order["website"] == "https://www.luvifermente.eu":
        msg['From'] = "LUVI Fermente <office@luvifermente.eu>"
        msg['To'] = str(order["billing"]["email"])
        msg['Subject'] = "[luvifermente.eu] Dein Tracking Link"

        if order["billing"]["first_name"] is not "":
            greeting = "Hallo " + order["billing"]["first_name"].capitalize() + ","
        else:
            greeting = "Schönen guten Tag,"

        text = """{greeting}<br>

            <p>du kannst den Versand deiner Bestellung bei diesem Link verfolgen: <a href="https://www.post.at/track/{tracking_code}">https://www.post.at/track/{tracking_code}</a></p>

            <p>Es kann ein paar Stunden dauern bis das Tracking funktioniert.</p>

            <p>Wir sagen danke für die Bestellung, und wünschen viel Freude :)</p>

            <p>Liebe Grüße,<br>
            Viktor, Christine und Lukas</p>
            """.format(
                greeting = greeting,
                tracking_code = tracking_code
                )

        msg.attach(MIMEText(text, 'html'))
    

    server.send_message(msg)
    server.quit()