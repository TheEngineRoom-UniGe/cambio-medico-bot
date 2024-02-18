import gtpyhop
import asyncio
from helper_functions.nlp import get_name_surname
from helper_functions.apis import get_date_of_birth, determine_type_of_doctor, preliminary_checks, get_doctors_list, print_doctors_offices, change_doctor

def do_preliminary_checks(state, user_token):
    if state.can_change_doctor == None:
        response = preliminary_checks(user_token)

        state.can_change_doctor = response['sceltaMedicoPossibile']
        if state.can_change_doctor == 'SI':
            state.available_comunas = [comuna['nomeComune'] for comuna in response['comuni']]
            state.comune = response['comuni'][0]['nomeComune'] if len(response['comuni']) == 1 else None
            state.available_zones = [zona['descrizioneCircoscrizione'] for zona in response['circoscrizioni']]
            state.zona = '' if state.available_zones == [] else None
        elif state.can_change_doctor == 'NO':
            state.message = response['messaggio']
        else:
            print('ERROR')
        return state

def retrieve_doctor_type(state, user_token):
    if state.doctor_type == None:
        date = get_date_of_birth(user_token)
        state.doctor_type = determine_type_of_doctor(date)
        return state

def ask_doctor_type(state, user_token):
    if state.doctor_type == None:
        doctor_type = input('What type of doctor are you looking for?\n1. Generico\n2. Pediatra\n')
        try:
            doctor_type = int(doctor_type)
        except Exception:
            print('You need to type "1" or "2".')
            state = ask_doctor_type(state, user_token)
        else:
            if doctor_type == 1:
                state.doctor_type = 'Generico'
            elif doctor_type == 2:
                state.doctor_type = 'Pediatra'
            else:
                print('You need to type "1" or "2".')
                state = ask_doctor_type(state, user_token)
        return state

def ask_doctor_gender(state, user_token):
    if state.doctor_gender == None:
        doctor_gender = input('Do you have preferences in doctor gender?\n1. I want a female\n2. I want a male\n3. I do not have preferences\n')
        try:
            doctor_gender = int(doctor_gender)
        except Exception:
            print('You need to type "1", "2" or "3".')
            state = ask_doctor_gender(state, user_token)
        else:
            if doctor_gender == 1:
                state.doctor_gender = 'f'
            elif doctor_gender == 2:
                state.doctor_gender = 'm'
            elif doctor_gender == 3:
                pass
            else:
                print('You need to type "1", "2" or "3".')
                state = ask_doctor_gender(state, user_token)
        return state

def ask_comuna(state, user_token):
    if state.comune == None:
        if len(state.available_comunas) == 1:
            state.comune = state.available_comunas[0]
        else:
            comunes_dict = dict(zip(range(1, len(state.available_comunas)+1), state.available_comunas))
            comunes_list = "\n".join([f'{key}. {comunes_dict[key]}' for key in comunes_dict])
            chosen_comuna = input(f'What comuna do you choose?\n{comunes_list}\n')
            try:
                chosen_comuna = int(chosen_comuna)
            except Exception:
                print('You need to type the number related to the zone of your choice.')
                state = ask_comuna(state, user_token)
            else:
                if chosen_comuna in range(1, len(state.available_comunas)+1):
                    state.comune = comunes_dict[chosen_comuna]
                else:
                    print('You need to type the number related to the zone of your choice.')
                    state = ask_comuna(state, user_token)
        return state

def ask_doctor_name(state, user_token):
    if state.doctor_surname == None:
        knows_name = input('Do you know the name of the doctor you want to take?\n1. yes\n2. no\n')
        try:
            knows_name = int(knows_name)
        except Exception:
            print('You need to type "1" or "2".')
            state = ask_doctor_name(state, user_token)
        else:
            if knows_name == 1:
                sentence = input('Ok, what is the name?\n')
                doctor_name = get_name_surname(sentence.title())
                # here I choose the first name, but I better choose all the names
                state.doctor_name = doctor_name[0]['nome']
                state.doctor_surname = doctor_name[0]['cognome']
            elif knows_name == 2:
                state.doctor_name = ''
                state.doctor_surname = ''
                print('Cool, any doctor then.\n')
            else:
                print('You need to type "1" or "2".')
                state = ask_doctor_name(state, user_token)
        return state

def ask_zona(state, user_token):
    if state.zona == None:
        if len(state.available_zones) == 1:
            state.zona = state.available_zones[0]
        elif len(state.available_zones) == 0:
            state.zona = ''
        else:
            zones_dict = dict(zip(range(1, len(state.available_zones)+1), state.available_zones))
            zones_list = "\n".join([f'{key}. {zones_dict[key]}' for key in zones_dict])
            chosen_zone = input(f'What zone do you choose?\n{zones_list}\n')
            try:
                chosen_zone = int(chosen_zone)
            except Exception:
                print('You need to type the number related to the zone of your choice.')
                state = ask_zona(state, user_token)
            else:
                if chosen_zone in range(1, len(state.available_zones)+1):
                    state.zona = zones_dict[chosen_zone]
                else:
                    print('You need to type the number related to the zone of your choice.')
                    state = ask_zona(state, user_token)
        return state


def get_doctor_list(state, user_token):
    if state.chosen_doctor == None and ((state.doctor_type != '' and state.doctor_surname != '') or (state.comune != '' and state.doctor_type != '')):
        doctor_list = get_doctors_list(user_token, state.comune, state.doctor_type, state.zona, state.doctor_name, state.doctor_surname, state.doctor_gender)
        state.search_result = doctor_list
        return state

def clear_search(state, user_token):
    if state.search_result != None:
        state.search_result = None
        state.zona = None
        state.comune = None
        state.doctor_gender = None
        state.doctor_name = None
        state.doctor_surname = None
        state.need_clear_search = False
        return state

def ask_choose_doctor(state, user_token, start, end):
    if state.search_result:
        print('Here are some of the doctors meeting your requirements:\n')
        res = asyncio.run(print_doctors_offices(state.search_result, start, end))
        print(res)
        chosen_doctor = input("\nChoose one of them or press -1 to kill the search or press 0 to see next doctors.\n")
        try:
            chosen_doctor = int(chosen_doctor)
        except Exception:
            print('You need to type the number related to the doctor of your choice OR -1 if you want to kill the search OR 0 if you want to see other doctors.')
            state = ask_choose_doctor(state, user_token, start, end)
        else:
            if chosen_doctor in range(1, len(state.search_result)+1):
                state.chosen_doctor = state.search_result[chosen_doctor-1]['codice']
                state.doctor_name = state.search_result[chosen_doctor-1]['nome']
                state.doctor_surname = state.search_result[chosen_doctor-1]['cognome']
            elif chosen_doctor == -1:
                state.need_clear_search = True
                # state = clear_search(state, user_token)
                # print('You cleared the search.')
            elif chosen_doctor == 0:
                start += end
                end += end
                state = ask_choose_doctor(state, user_token, start, end)
            else:
                print('You need to type the number related to the doctor of your choice.')
                state = ask_choose_doctor(state, user_token, start, end)
        return state

def confirm_choice(state, user_token):
    if not state.confirmation and state.chosen_doctor and state.doctor_name != '' and state.doctor_surname != '' and state.doctor_type:
        confirmation = input(f'Do you confirm that you want to change your doctor to {state.doctor_name} {state.doctor_surname} {state.chosen_doctor}?\n1. yes\n2. no\n')
        try:
            confirmation = int(confirmation)
        except Exception:
            print('You need to type "1" or "2".')
            state = confirm_choice(state, user_token)
        else:
            if confirmation == 1:
                state.confirmation = True
            elif confirmation == 2:
                state.confirmation = False
            else:
                print('You need to type "1" or "2".')
                state = confirm_choice(state, user_token)
        return state


def a_change_doctor(state, user_token):
    if state.confirmation and state.chosen_doctor and state.doctor_name != '' and state.doctor_surname != '' and state.doctor_type:
        result = change_doctor(user_token, state.doctor_name, state.doctor_surname, state.doctor_type, state.chosen_doctor)
        state.change_result = result
        state.display()
        return state

def do_nothing(state, user_token):
    if state.can_change_doctor == 'NO':
        print('Sorry, you cannot change your doctor now:', state.message)
        return state

gtpyhop.declare_actions(do_nothing, do_preliminary_checks, retrieve_doctor_type, ask_doctor_type, ask_doctor_gender, ask_doctor_name, ask_comuna, ask_zona, get_doctor_list, ask_choose_doctor, confirm_choice, a_change_doctor, clear_search)
