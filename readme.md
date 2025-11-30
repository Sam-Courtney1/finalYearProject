Project overview:

The code in this project runs 2 different sites.

App.py starts a flask application which runs the client site which is were users can fill out questionnaires and view / delete there data

while client.py starts the client site where clients can create and edit questionnaires.

Both can be started by typing python followed by the file name.

It is important to note that the .env file with all of the required variables has not been provided or pushed to git.
This means that if you try to run the file and login or register you will be met with errors as you are not connected to the database.
It is also important to understand that the database held inside RDS must be in an RUNNING state or the database will not connect.


The main features of both sites are as follows

User site (app.py):

Authentication
    Register and log in as a user.
Questionnaire selection and submission
    Choose an organisation and complete its questionnaire.
    Consent checkbox required on each submission.
Right to Access
    View a Core Information table (name, address, age) stored at registration.
    View Per company Data grouped by organisation showing what each client stores.
Right to be Forgotten   
    From the homepage a user can also delete their account and all there data

The client site (client.py):

Client authentication
    Register / log in as a client (organisation).
Questionnaire builder
    Add and remove questionnaire fields with type and category (PII / Medical / Demographic etc.).


There is also a requirnments.txt file for installing all require requirnments to run this application. 