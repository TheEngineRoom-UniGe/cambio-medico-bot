import gtpyhop

def do_preliminary_checks(state, user_token):
    if state.can_change_doctor == None:
        return [('do_preliminary_checks', user_token)]

def m_retrieve_doctor_type(state, user_token):
    if state.doctor_type == None:
        return [('retrieve_doctor_type', user_token)]
    
def m_ask_doctor_type(state, user_token):
    if state.doctor_type == None:
        return [('ask_doctor_type', user_token)]

gtpyhop.declare_task_methods('m_doctor_type', m_retrieve_doctor_type, m_ask_doctor_type)

def collect_requirements(state, user_token):
    if state.can_change_doctor == 'SI':
        plan = []
        if state.doctor_type == None:
            plan.append(('m_doctor_type', user_token))
        if state.doctor_gender == None:
            plan.append(('ask_doctor_gender', user_token))
        if state.doctor_surname == None:
            plan.append(('ask_doctor_name', user_token))
        if state.comune == None:
            plan.append(('ask_comuna', user_token))
        if state.zona == None:
            plan.append(('ask_zona', user_token))
        return plan
    
gtpyhop.declare_task_methods('collect_requirements', collect_requirements)

def kill_search(state, user_token):
    if state.need_clear_search == True:
        return [('clear_search', user_token), ('preliminary_checks_result', user_token)]

def proceed(state, user_token):
    if state.need_clear_search == False:
        return []

def successful_search(state, user_token):
    if state.chosen_doctor == None and state.search_result != []:
        return [('ask_choose_doctor', user_token, 0, 3), ('clear_search_processing', user_token)]
    
def unsuccessful_search(state, user_token):
    if state.chosen_doctor == None and state.search_result == []:
        print('Sorry, your search was unsuccessful. I will start a new search.')
        return [('clear_search', user_token), ('preliminary_checks_result', user_token)]

def choose_doctor(state, user_token):
    if state.chosen_doctor == None and ((state.doctor_type != '' and state.doctor_surname != '') or (state.comune != '' and state.doctor_type != '')):
        return [('get_doctor_list', user_token), ('process_search_results', user_token)]        
    
gtpyhop.declare_task_methods('process_search_results', successful_search, unsuccessful_search)
gtpyhop.declare_task_methods('clear_search_processing', kill_search, proceed)
gtpyhop.declare_task_methods('choose_doctor', choose_doctor)


def m_change_doctor(state, user_token):
    if state.chosen_doctor and state.doctor_name != '' and state.doctor_surname != '' and state.doctor_type:
        return [('confirm_choice', user_token), ('process_confirmed_choice', user_token)]

def change_to_chosen_doctor(state, user_token):
    if state.confirmation:
        return [('a_change_doctor', user_token)]

def cancel_search_results(state, user_token):
    if not state.confirmation:
        print(f'You refused to change your doctor to {state.doctor_name} {state.doctor_surname} {state.chosen_doctor}.')
        return [('clear_search', user_token)]

gtpyhop.declare_task_methods('process_confirmed_choice', change_to_chosen_doctor, cancel_search_results)
gtpyhop.declare_task_methods('m_change_doctor', m_change_doctor)


def preliminary_checks_success(state, user_token):
    if state.can_change_doctor == 'SI':
        return [('collect_requirements', user_token), ('choose_doctor', user_token), ('m_change_doctor', user_token)]

def preliminary_checks_no_success(state, user_token):
    if state.can_change_doctor == 'NO':
        return [('do_nothing', user_token)]


gtpyhop.declare_task_methods('preliminary_checks_result', preliminary_checks_success, preliminary_checks_no_success)

def endpoint(state, user_token):
    return [('do_preliminary_checks', user_token), ('preliminary_checks_result', user_token)]

gtpyhop.declare_task_methods('endpoint', endpoint)
