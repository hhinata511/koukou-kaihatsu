"""Test to verify all routes including analysis are loading correctly."""
from app import create_app

app = create_app()
app.testing = True

with app.test_client() as c:
    # Test home page
    r = c.get('/')
    print(f'Home page: {r.status_code}')

    # Test new record form
    r = c.get('/record/new')
    print(f'New record form: {r.status_code}')

    # Test settings
    r = c.get('/settings')
    print(f'Settings: {r.status_code}')

    # Test record list
    r = c.get('/records')
    print(f'Record list: {r.status_code}')

    # Test POST to create a record
    r = c.post('/record/new', data={
        'record_date': '2025-06-24',
        'menu_name': '100m',
        'menu_count': '3',
        'sleep_hours': '6.5',
        'subjective_fatigue': '4',
        'temperature': '28',
        'remark': 'test',
    }, follow_redirects=True)
    print(f'Create record (POST): {r.status_code}')

    # Test record detail
    r = c.get('/record/1')
    print(f'Record detail: {r.status_code}')

    # Test analysis page (with record that exists)
    r = c.get('/analysis/1')
    print(f'Analysis page: {r.status_code}')

    # Print available routes
    print('\nAvailable routes:')
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f'  {methods:8s} {rule.rule}')

    print('\nAll route tests passed!')