import gtpyhop
import os
import dotenv

dotenv.load_dotenv()

user_token = os.getenv('JWTEndUserAttributes')

domain = gtpyhop.Domain('cambio medico')

from methods.methods import *
from actions.actions import *

gtpyhop.current_domain = domain

# from helper_functions.rigid import rigid
from helper_functions.state import state_0

state_0.display('This is initial state')

state1 = state_0.copy()

gtpyhop.verbose = 3

gtpyhop.print_domain()

result = gtpyhop.find_plan(state1, [('endpoint', user_token)])

print(result)


# IDEAS

# 1. if user wants doctor with surname_x in zone_y and search doesn't find anything, 
# do search only with surname_x and print in which zone this doctor works

# 2. use API https://srvcarto2svil.regione.liguria.it/geoservices/REST/geocoder/proxy/pelias_geocode/v1/search/?text=via%20borgo%20incrociati%207
# or google maps api to order list of doctors by distance to home/work

# 3. add filter by gender

# 4. during the choice of doctor from list show number of pages and at the last page don't let person go further