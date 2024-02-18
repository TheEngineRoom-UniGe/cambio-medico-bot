import requests
import base64
import json
from json.decoder import JSONDecodeError
from dateutil import relativedelta
from datetime import datetime
from typing import Literal
import asyncio, aiohttp

day_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato']
weekdays = {num: day for num, day in zip(range(1, len(day_names)+1), day_names)}

appointment = {1: 'libero', 2: 'per appuntamento', 3: 'misto', 4: 'per patologia', 5: '1 e 3 del mese', 6: '2 e 4 del mese'}

doc_type = {'Generico': 1, 'Pediatra': 2}

def preliminary_checks(user_token):
    
    url = "http://ies-test.liguriadigitale.it:8280/appSalute/ASR/private/controllo"
    response = requests.request("GET", url, headers={'JWTEndUserAttributes': user_token}, data={})
    try:
        response = response.json()
    except Exception:
        print('exception')
        response = {}
    return response

def get_date_of_birth(user_token):

    data = base64.b64decode(user_token.split('.')[1])
    data = json.loads(data)
    date_of_birth = data['http://wso2.org/claims/datanascita']
    return date_of_birth

def determine_type_of_doctor(date_of_birth: str):
    """ex. date_of_birth = '2020-07-30'"""

    date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d')
    delta = relativedelta.relativedelta(datetime.now(), date_of_birth)

    if delta.years > 13:
        doctor_type = 'Generico'
    else:
        doctor_type = 'Pediatra'
    return doctor_type

def get_doctor_gender(asl_num, distretto, doctor_type, nome='', cognome='', doc_id=None):

    url = f"http://ies-test.liguriadigitale.it:8280/appSalute/ASR/public/medico?ASL={asl_num}&distretto={distretto}&cognome={cognome}&nome={nome}&tipo={doctor_type}"
    response = requests.request("GET", url, headers={}, data={})
    try:
        response = response.json()
    except JSONDecodeError:
        response = []
    except Exception:
        print('exception', response.text)
        response = []
    else:
        if doc_id:
            for doctor in response:
                if doctor['codice'] == doc_id:
                   chosen_doctor = doctor
        else:
            chosen_doctor = response[0]
        gender = 'f' if int(chosen_doctor['codFiscale'][9:11]) > 40 else 'm'
    return gender

def get_doctor_list_public(asl_num, distretto, doctor_type, nome='', cognome=''):

    url = f"http://ies-test.liguriadigitale.it:8280/appSalute/ASR/public/medico?ASL={asl_num}&distretto={distretto}&cognome={cognome}&nome={nome}&tipo={doctor_type}"
    response = requests.request("GET", url, headers={}, data={})
    try:
        response = response.json()
    except JSONDecodeError:
        response = []
    except Exception:
        print('exception', response.text)
        response = []
    return response

def get_doctors_list(user_token, comune, doctor_type, zona='', nome='', cognome='', gender: Literal['f', 'm'] = '', only_available=True):

    url = f"http://ies-test.liguriadigitale.it:8280/appSalute/ASR/private/medico?cognomeMedico={cognome}&nomeMedico={nome}&comuneMedico={comune}&circoscrizioneMedico={zona}&tipoMedico={doctor_type}"
    response = requests.request("GET", url, headers={'JWTEndUserAttributes': user_token}, data={})
    try:
        response = response.json()
    except JSONDecodeError:
        response = []
    except Exception:
        print('exception', response.text)
        response = []
    else:
        if only_available:
            response = [doctor for doctor in response if doctor['sceglibile'] == 'SI']
        if gender:
            asl = response[0]['asl']
            ambito = response[0]['ambito']
            doctype = 1 if doctor_type == 'Generico' else 2
            public_list = get_doctor_list_public(asl, ambito, doctype, nome, cognome)
            for doctor in response:
                for doctor_pub in public_list:
                    if doctor['codice'] == doctor_pub['codice']:
                        doctor['gender'] = 'f' if int(doctor_pub['codFiscale'][9:11]) > 40 else 'm'
            response = [doctor for doctor in response if doctor['gender'] == gender]
    return response

async def find_doctor_offices(session, doctor_id):
    url = f'http://ies-test.liguriadigitale.it:8280/appSalute/ASR/public/studio?codicemedico={doctor_id}'
    async with session.get(url, headers={}, data={}) as response:
        try:
            response = await response.json()
        except Exception:
            response = {}
    return response
    # response = requests.request("GET", url, headers={}, data={})
    # try:
    #     response = response.json()
    # except Exception:
    #     print('exception')
    #     response = {}
    # return response

async def process_doctor_offices(offices):

    data = []

    for office in offices['studi']: # parse all offices
        data.append({key: office[key] if key in office else []
                    for key in ['codCap', 'idStudio', 'numTelefStudio', 'indStudioVia', 
                                'indStudioCivico', 'indStudioInterno', 'orari', 'giorni']})
    
    for orario in offices['orari']: # parse all timetables
        for office in data:
            if office['idStudio'] == orario['idStudioOrari']:
                day = weekdays[orario['giornoSettimana']]
                info = [{'apertura': orario[f'apertura{x}'], 
                        'chiusura': orario[f'chiusura{x}'],
                        'codOrarioRicev': orario[f'codOrarioRicev{x}']} for x in range(3) if orario[f'apertura{x}'] != None]
                if day in office['giorni']:
                    for x in office['orari']:
                        if x['giornoSettimana'] == day:
                            x['orario'] += info
                else:
                    office['orari'].append({'giornoSettimana': day, 'orario': info})
                    office['giorni'].append(day)

    for office in data:
        for orario in office['orari']:
            orario['text'] = f"\t{orario['giornoSettimana']}: " + ", ".join([f"{timeslot['apertura']} - {timeslot['chiusura']} ({appointment[timeslot['codOrarioRicev']]})" for timeslot in orario['orario']])

        office['address'] = f"{office['indStudioVia']}, {office['indStudioCivico']} - {office['codCap']} {office['indStudioInterno']}"

        office['timetable'] = "\n".join([orario['text'] for orario in office['orari']])

    return data

async def doctor_office_info(doctor_id):

    async with aiohttp.ClientSession() as session:
        offices_raw = await find_doctor_offices(session, doctor_id)
    
        offices = await process_doctor_offices(offices_raw)

    info_string = '\n\n'.join([f'{offices[o_id]["address"]}\n{offices[o_id]["timetable"]}' for o_id in range(len(offices))])
    return  info_string

async def print_doctors_offices(doctor_list, start=0, end=3):

    data = []
    offices = await asyncio.gather(*[doctor_office_info(doctor['codice']) for doctor in doctor_list[start:end]])
    for doctor, idx in zip(doctor_list[start:end], range(start, end)):
        data.append(f"{idx+1}. {doctor['nome']} {doctor['cognome']} {doctor['codice']}\n{doctor['motivo'] if doctor['motivo'] else ''}")

    data_1 = list(zip(data, offices))
    data = [item for sublist in data_1 for item in sublist]
    return "\n\n".join(data)

def change_doctor(user_token, doctor_name, doctor_surname, doctor_type, doctor_id):
    url = f"http://ies-test.liguriadigitale.it:8280/appSalute/ASR/private/scelta?codiceMedico={doctor_id}&nomeMedico={doctor_name}&tipoMedico={doctor_type}&cognomeMedico={doctor_surname}"
    response = requests.request("PUT", url, headers={'JWTEndUserAttributes': user_token}, data={})
    try:
        response = response.json()
    except Exception:
        print('exception')
        response = {}
    return response

if __name__ == '__main__':
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0=.ewogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL3JvbGUiOiAiSW50ZXJuYWxcL2V2ZXJ5b25lIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9hcHBsaWNhdGlvbnRpZXIiOiAiVW5saW1pdGVkIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9kb21pY2lsaW9maXNpY28iOiAiVmlhIExpc3R6IDIxIDAwMTQ0IFJvbWEiLAogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL2VtYWlsIjogInNwaWQudGVjaEBhZ2lkLmdvdi5pdCIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvY29nbm9tZSI6ICJBZ0lEIiwKICAgICJpc3MiOiAid3NvMi5vcmdcL3Byb2R1Y3RzXC9hbSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvcGFydGl0YWl2YSI6ICJWQVRJVC05NzczNTAyMDU4NCIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvZGF0YW5hc2NpdGEiOiAiMjAwMC0wMS0wMSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvZW5kdXNlclRlbmFudElkIjogIi0xMjM0IiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9kYXRhc2NhZGlkZW50IjogIjIwMjgtMDEtMDEiLAogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL2NvZGljZWZpc2NhbGUiOiAiVElOSVQtR0NDTVJBNjJNMDlJNDgwVSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvY29kaWNlc3BpZCI6ICJBR0lELTAwMSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvc3Vic2NyaWJlciI6ICJhZG1pbiIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvc2VkZWxlZ2FsZSI6ICJWaWEgTGlzdHogMjEgMDAxNDQgUm9tYSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvcHJvdmluY2lhbmFzY2l0YSI6ICJSTSIsCiAgICAiZXhwIjogMTY0ODYzOTgxNiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9hcHBsaWNhdGlvbmlkIjogIjgyIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC91c2VydHlwZSI6ICJBUFBMSUNBVElPTl9VU0VSIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9hcGljb250ZXh0IjogIlwvZnVuemlvbmFtZW50b2FtXC8xLjAuMCIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvc2Vzc28iOiAiTSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvcmFnaW9uZXNvY2lhbGUiOiAiQWdlbnppYSBwZXIgbCdJdGFsaWEgRGlnaXRhbGUiLAogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL2RvbWljaWxpb2RpZ2l0YWxlIjogInBlY0BwZWNhZ2lkLmdvdi5pdCIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wva2V5dHlwZSI6ICJQUk9EVUNUSU9OIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC92ZXJzaW9uIjogIjEuMC4wIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9hcHBsaWNhdGlvbm5hbWUiOiAiQ1BJX1ZpcnR1YWxpIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9lbmR1c2VyIjogIkpJVFBST1ZJU0lPTklOR1wvVElOSVQtR0RBU0RWMDBBMDFINTAxSkBjYXJib24uc3VwZXIiLAogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL25vbWUiOiAiU3BpZFZhbGlkYXRvciIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvZG9jdW1lbnRvaWRlbnRpdGEiOiAiQ2FydGFJZGVudGl0w6AgQUEwMDAwMDAwMCBDb211bmVSb21hIDIwMTgtMDEtMDEgMjAyOC0wMS0wMSIsCiAgICAiaHR0cDpcL1wvd3NvMi5vcmdcL2NsYWltc1wvbnVtZXJvY2VsbHVsYXJlIjogIiszOTMzMzEyMzQ1NjciLAogICAgImh0dHA6XC9cL3dzbzIub3JnXC9jbGFpbXNcL3RpZXIiOiAiVW5saW1pdGVkIiwKICAgICJodHRwOlwvXC93c28yLm9yZ1wvY2xhaW1zXC9sdW9nb25hc2NpdGEiOiAiUm9tYSIKfQ==.'
    doctor_list = get_doctors_list(token, 'SAVONA', 'Generico')
    res = asyncio.run(print_doctors_offices(doctor_list, start=0, end=3))
    print(res)