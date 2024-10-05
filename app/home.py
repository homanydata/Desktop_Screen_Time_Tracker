from flask import Blueprint, render_template, make_response, session, url_for, redirect
from utils.summarizer import get_denormalized_records


home = Blueprint('home', __name__)

# Route for the index page
@home.route('/', methods=['GET'])
def index():
    # Render the index page with the empty graph initially
    return render_template('index.html')

@home.route('/export-data', methods=['GET'])
def export_data():
    df = get_denormalized_records()
    df = df.rename(columns={'duration': 'duration (in seconds)', 'datetime': 'datetime (every hour)'})
    # Create a CSV file from the data
    csv_data = df.to_csv(index=False)

    # Create a response with the CSV file
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = 'attachment; filename="screentime_data.csv"'
    response.headers['Content-Type'] = 'text/csv'

    return response

@home.route('/change-theme')
def change_theme():
    if 'theme' not in session or session['theme'] == 'light':
        session['theme'] = 'dark'
    else:
        session['theme'] = 'light'
    return redirect(url_for('home.index'))