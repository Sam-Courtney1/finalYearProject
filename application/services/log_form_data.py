from data.questionnaire import insert_questionnaire

"""
This function handles data being sent to it from the questionnaire
it assigns the data to variables which are stored and in another
function called insert questionnaire, these valuesare insterted
into the database
"""
def handle_questionnaire_submission(user_id, form_data):
    insert_questionnaire(
        user_id = user_id, 
        first_name = form_data['first_name'],
        age = form_data['age'],
        address= form_data['address'],
        blood_type = form_data['blood_type'],
        organ = form_data['organ'],
        consent = 'consent' in form_data
    )
