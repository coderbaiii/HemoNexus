"""
HEMONEXAS Patient Model
Manages patient/requester profiles.
"""
from database.db import query_db, execute_db

class PatientModel:
    @staticmethod
    def get_by_user_id(user_id, db=None):
        return query_db(
            """SELECT p.*, u.full_name, u.email 
               FROM patient_profiles p
               JOIN users u ON p.user_id = u.id
               WHERE p.user_id = ?""",
            (user_id,),
            one=True,
            db=db
        )
