import smtplib  #sending mail
from email.message import EmailMessage   #mail formatting
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)    
    server.login('moinuddinchistyshaik@gmail.com','kqqf bpyq cmxe nnjk')
    msg=EmailMessage()
    msg['FROM']='moinuddinchistyshaik@gmail.com'
    msg['SUBJECT']=subject
    msg['TO']=to
    msg.set_content(body)
    server.send_message(msg)
    server.close()