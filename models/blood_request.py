"""
HEMONEXAS Blood Request Model
Manages blood requests, requirements, and statuses.
"""
from database.db import query_db, execute_db

class BloodRequestModel:
    @staticmethod
    def get_by_id(request_id, db=None):
        return query_db(
            """SELECT br.*, u.full_name AS patient_name, u.email AS patient_email
               FROM blood_requests br
               JOIN users u ON br.patient_id = u.id
               WHERE br.id = ?""",
            (request_id,),
            one=True,
            db=db
        )

    @staticmethod
    def list_by_patient(patient_id, db=None):
        return query_db(
            """SELECT br.*, 
                      COUNT(r.id) AS total_sent,
                      SUM(CASE WHEN r.status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count,
                      SUM(CASE WHEN r.status = 'PENDING' THEN 1 ELSE 0 END) AS pending_count
               FROM blood_requests br
               LEFT JOIN donor_request_responses r ON br.id = r.blood_request_id
               WHERE br.patient_id = ?
               GROUP BY br.id
               ORDER BY br.created_at DESC""",
            (patient_id,),
            db=db
        )
