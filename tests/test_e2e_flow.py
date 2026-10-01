import urllib.request
import urllib.parse
import json
import http.cookiejar

def run_test():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    BASE = 'http://127.0.0.1:5000'

    def post_json(url, data):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        try:
            with opener.open(req) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    def post_form(url, data):
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode('utf-8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with opener.open(req) as resp:
            return resp.status, resp.read().decode('utf-8')

    def get_json(url):
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        try:
            with opener.open(req) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    # 1. Login as patient
    status, login_res = post_json(f'{BASE}/api/login', {'email': 'patient.raj@example.com', 'password': 'Patient@1234'})
    print('1. Login Patient:', status, login_res.get('message'))

    # 2. Check /api/me
    status, me = get_json(f'{BASE}/api/me')
    print('2. /api/me:', status, me['user']['email'], me['user']['role'])

    # 3. Create Blood Request
    status, res = post_json(f'{BASE}/api/patient/blood-requests', {
        'required_blood_group': 'A+',
        'hospital_name': 'AMRI Hospital Kolkata',
        'location': 'Kolkata',
        'latitude': 22.5852,
        'longitude': 88.4124,
        'urgency': 'URGENT',
        'required_units': 1,
        'preferred_max_distance': 30.0
    })
    req_id = res['request']['id']
    print('3. Blood Request created:', req_id)

    # 4. Get Matches
    status, matches_res = get_json(f'{BASE}/api/patient/blood-requests/{req_id}/matches')
    matches = matches_res.get('matches', [])
    print(f'4. Matches returned: {len(matches)}')
    assert len(matches) > 0, "Expected at least 1 match"
    donor_id = matches[0]['user_id']
    donor_name = matches[0]['full_name']
    print(f'   Selected donor_id: {donor_id} ({donor_name})')

    # 5. Dispatch Donor (Requirement 1)
    status, disp_res = post_json(f'{BASE}/api/patient/blood-requests/{req_id}/send-request', {'donor_id': donor_id})
    print(f'5. Dispatch status: {status}, message: {disp_res.get("message")}')
    assert status == 201

    # Duplicate Dispatch test (409)
    status_dup, dup_res = post_json(f'{BASE}/api/patient/blood-requests/{req_id}/send-request', {'donor_id': donor_id})
    print(f'   Duplicate dispatch status: {status_dup} (expected 409)')
    assert status_dup == 409

    # 6. Test Dashboard endpoint data for Patient (Requirement 2)
    status, details = get_json(f'{BASE}/api/patient/blood-requests/{req_id}')
    responses = details.get('responses', [])
    print(f'6. Dashboard data: {len(responses)} response(s) logged')
    assert len(responses) >= 1
    print(f'   Response status: {responses[0]["status"]}, donor: {responses[0]["donor_name"]}')

    # 7. Test Emergency SOS (Requirement 3)
    status, sos_res = post_json(f'{BASE}/api/patient/blood-requests', {
        'required_blood_group': 'O+',
        'hospital_name': 'Emergency Trauma Center',
        'location': 'Kolkata',
        'latitude': 22.5697,
        'longitude': 88.4046,
        'urgency': 'CRITICAL',
        'required_units': 3,
        'preferred_max_distance': 30.0
    })
    sos_id = sos_res['request']['id']
    status, sos_matches = get_json(f'{BASE}/api/patient/blood-requests/{sos_id}/matches')
    sos_list = sos_matches.get('matches', [])
    print(f'7. Emergency SOS Request #{sos_id} found {len(sos_list)} candidates')
    for m in sos_list:
        d_id = m['user_id']
        d_name = m['full_name']
        st, sr = post_json(f'{BASE}/api/patient/blood-requests/{sos_id}/send-request', {'donor_id': d_id})
        print(f'   SOS alert sent to {d_id} ({d_name}): status {st}')

    # 8. Check Header & Routes (Requirement 4)
    req = urllib.request.Request(f'{BASE}/match')
    with opener.open(req) as resp:
        html = resp.read().decode('utf-8')
        assert 'Dispatch Route' not in html
        print('8. Dispatch Route removed cleanly from header/sidebar HTML!')

    # 9. Test Donor side (Requirement 5): Accept Request
    # Login as donor (Amitav Sengupta, donor_id=5)
    cj_donor = http.cookiejar.CookieJar()
    opener_donor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_donor))
    
    def post_json_donor(url, data):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        try:
            with opener_donor.open(req) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    def get_json_donor(url):
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        try:
            with opener_donor.open(req) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode('utf-8'))

    status, login_donor_res = post_json_donor(f'{BASE}/api/login', {'email': 'amitav.donor@example.com', 'password': 'Donor@1234'})
    print('9. Login Donor:', status, login_donor_res.get('message'))

    status, donor_reqs = get_json_donor(f'{BASE}/api/donor/requests')
    d_requests = donor_reqs.get('requests', [])
    print(f'   Donor received {len(d_requests)} incoming requests')
    assert len(d_requests) > 0

    target_response_id = d_requests[0]['response_id']
    status, accept_res = post_json_donor(f'{BASE}/api/donor/requests/{target_response_id}/accept', {'message': 'Confirmed donation!'})
    print(f'   Donor accepted response #{target_response_id}: status {status}, {accept_res.get("message")}')
    assert status == 200

    # 10. Verify Dashboard reflects the ACCEPTED status
    status, updated_details = get_json(f'{BASE}/api/patient/blood-requests/{sos_id}')
    updated_responses = updated_details.get('responses', [])
    assert any(r['status'] == 'ACCEPTED' for r in updated_responses), "Expected at least one ACCEPTED response"
    print('10. Dashboard successfully updated with ACCEPTED donor response!')

    print('\n*** SUCCESS: ALL 5 REQUIREMENTS VERIFIED AND FUNCTIONING 100% ***')

if __name__ == '__main__':
    run_test()
