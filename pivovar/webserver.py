from flask import Flask, render_template, send_from_directory


app = Flask(__name__)


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/')
def wash():
    return render_template(
        'wash.html',
        real_temps_url='http://localhost:5001/real_temps',
        wash_machine_phases_url='http://localhost:5001/phases',
        wash_machine_current_phase_url='http://localhost:5001/current_phase',
    )


def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()
