import sys
import json
from dateutil import tz
from datetime import datetime, timedelta
import csv
import plotly
import plotly.graph_objects as go
import pandas as pd

from pyemvue.pyemvue import PyEmVue
from pyemvue.customer import Customer
from pyemvue.enums import Scale, Unit, TotalTimeFrame, TotalUnit
from pyemvue.device import VueDevice, VueDeviceChannel, VuewDeviceChannelUsage

vue = PyEmVue()

def main():
    errorMsg = 'Please pass a file containing the "email" and "password" as json.'
    if len(sys.argv) == 1:                      # Chequea si se pasó el archivo Json
        print(errorMsg)
        sys.exit(1)

    filepath = sys.argv[1]                      # Path del archivo Json

    data = {}
    email = None
    passw = None
    idToken = None
    accessToken = None
    refreshToken = None

    try:
        with open(filepath) as f:               # Abre el archivo Json
            data = json.load(f)
    except:
        print('Error opening file.', errorMsg)
        raise

    if ('email' not in data or 'password' not in data) and ('idToken' not in data or 'accessToken' not in data or 'refreshToken' not in data):
        print(errorMsg)
        sys.exit(1)
    canLogIn = False
    if 'email' in data:
        email = data['email']
        if 'password' in data:
            passw = data['password']
            canLogIn = True
    if 'idToken' in data and 'accessToken' in data and 'refreshToken' in data:
        idToken = data['idToken']
        accessToken = data['accessToken']
        refreshToken = data['refreshToken']
        canLogIn = True
    if not canLogIn:
        print('Not enough details to log in.', errorMsg)
        sys.exit(1)
    # LOGIN
    vue.login(email, passw, idToken, accessToken, refreshToken, token_storage_file=filepath)
    # CUSTOMER DATA
    customer = vue.get_customer_details()                   # Get customer details
    print("Customer ID: " + str(customer.customer_gid))
    print("Nombre: " + customer.first_name)
    print("Apellidos: " + customer.lastName)
    print("Email: " + customer.email)
    created_str = str(customer.created_at).replace("Z", "")                 # Remueve TIMEZONE de created_at
    created_at = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%f")     # Convierte created_str a datetime nuevamente
    created_at = created_at.replace(minute=0, second=0, microsecond=0)
    print(f"Creado: {created_at}")
    print()
    # DEVICES DETAILS
    devices = vue.get_devices()
    now = datetime.utcnow()
    start_date = created_at                     # Para asignar fecha directamente datetime(2020, 11, 1, 5, 0, 0)
    end_date = now                              # Get devices details
    for i, device in enumerate(devices):
        device = vue.populate_device_properties(device)
        device_name = "Dispositivo " + str(i) if device.device_name == None else device.device_name
        total_usage = vue.get_usage_over_time(devices[i].channels[0], start_date, end_date, scale=Scale.HOUR.value, unit=Unit.WATTS)
        # Crear Archivos CSV
        create_csv(device_name, total_usage, start_date)          
        create_plot(device_name, start_date, end_date)      # Crea Gráficos en html
        print("Dispositivo: " + device_name)                # Nombre del equipo
        print("GID: " + str(device.device_gid))             # GID del equipo
        print("Modelo: " + device.model)                    # Modelo del equipo
        print("Device ID: " + '-'.join(device.manufacturer_id.upper()[i:i+4] for i in range(0,16,4)))  # Serial del equipo
        print("Firmware: " + device.firmware)
        vue.populate_device_properties(device)                 # Firmware del equipo
        for chan in device.channels:
            print(f"Canales en uso: {chan.channel_num} Multiplicador: {chan.channel_multiplier}")
        print(round(vue.get_total_usage(devices[i].channels[0], TotalTimeFrame.MONTH.value) / 1000, 2), "kwh used month to date")
        print(round(vue.get_total_usage(devices[i].channels[0], TotalTimeFrame.ALL.value) / 1000, 2), "kwh used TOTAL")
        print()  

def create_csv(name, total, start_date):
    filename = name + ".csv"
    field_names = ["DateTime", "Value"]
    start_time = start_date + timedelta(hours=-4)
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for i, line in enumerate(total):
            date_and_time = start_time + timedelta(hours=+i)
            if line is None:
                kwh = 0.0   
            else: 
                kwh = round(float(line)/1000, 2)
            writer.writerow({"DateTime":date_and_time, "Value":kwh})
            # Procedimiento adicional para corregir hora (2020,11,1,1,0,0) REPETIDA
            if date_and_time == datetime(2020, 11, 1, 1, 0, 0):
                start_time = start_date + timedelta(hours=-5)

def create_plot(name, start, end):
    csv_file = name + ".csv"
    df = pd.read_csv(csv_file)
    data = [go.Scatter( 
        x = df['DateTime'], 
        y = df['Value'], 
        mode='lines+markers',
        fill='tozeroy', 
        line=dict(color='green', width=2),
        text=df['Value'],
        textposition="top right",
        marker=dict(color="rgba(48,217,189,1)")
        )
    ]
    layout = go.Layout(
        plot_bgcolor="lightgrey",
        title=f"Dispositivo: {name}  / entre el {start.date()} y el {end.date()}",
        showlegend=True,
        xaxis=dict(
            title='Tiempo',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        ),
        yaxis=dict(
            title='Consumo Kwh',
            titlefont=dict(
                family='Courier New, monospace',
                size=18,
                color='#7f7f7f'
            )
        )
    )
    fig = go.Figure(data, layout=layout)
    plotly.offline.plot(fig, filename = name + ".html")    

if __name__ == '__main__':
    main()