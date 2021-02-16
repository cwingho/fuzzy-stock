import requests
from alpha_vantage.techindicators import TechIndicators
import skfuzzy as fuzz
import skfuzzy.control as ctrl
import numpy as np
from datetime import date,timedelta
import sys

# defind data format, setting
symbol = sys.argv[1]
interval = 'daily'
datatype = 'json'
series_type = 'close'

# api key
# please fill in your alpha vantage api key
api_key = list(['xxxxxxxxxxxxxxxx','xxxxxxxxxxxxxxxx','xxxxxxxxxxxxxxxx','xxxxxxxxxxxxxxxx'])

# MACD
fast_period = 12
slow_period = 24
signal_period = 9

# RSI
rs = 14
overbought = 70
oversold = 30

# STOCH
k_period = 10
overbought = 80
oversold = 20

# OBV
# upward = buy
# downward = sell

def scaleRange(val, orig_min=-2, orig_max=2, min=0, max=1):
    '''
    Scale the value
    :param val: current value
    :param orig_min: the min. value
    :param orig_max: the max. value
    :param min: the min. target value
    :param max: the max. target value
    '''
    scale = (max - min) / (orig_max - orig_min)
    val = scale * (val - orig_min) + min
    return val


def recommend(simulation, symbol):
	'''
    make recommendation
    :param simulation: instance of fuzzy system
    :param symbol: code of the stock
    '''
	ti1 = TechIndicators(key=api_key[0], output_format='json')
	ti2 = TechIndicators(key=api_key[1], output_format='json')
	ti3 = TechIndicators(key=api_key[2], output_format='json')
	ti4 = TechIndicators(key=api_key[3], output_format='json')

	macd = ti1.get_macd(symbol,interval=interval,series_type=series_type,fastperiod=fast_period,slowperiod=slow_period,signalperiod=signal_period)
	rsi = ti2.get_rsi(symbol,interval=interval,series_type=series_type,time_period=rs)
	stoch = ti3.get_stoch(symbol,interval=interval,fastkperiod=k_period,slowkperiod=k_period,slowdperiod=k_period)
	obv = ti4.get_obv(symbol,interval=interval)

	last_day = (date.today()-timedelta(days=1)).strftime("%Y-%m-%d")

	# macd
	macd_range = list()
	for k,v in macd[0].items():
		macd_range.append(float(v['MACD_Hist']))
	macd_val = float(macd[0][last_day]['MACD_Hist'])

	# rsi
	rsi_val = rsi[0][last_day]['RSI']

	# stoch
	# stoch_val = stoch[0][last_day]['SlowK']
	stoch_val = stoch[0][last_day]['SlowD']
	
	# obv
	obv_vals = list()
	for k,v in obv[0].items():
		obv_vals.append(float(v['OBV']))
	obv_range = [y-x for x, y in zip(obv_vals, obv_vals[1:])]
	obv_val = obv_range[-1]

	# feed to the simulator
	simulation.input['macd'] = scaleRange(macd_val, orig_min=min(macd_range), orig_max=max(macd_range), min=0, max=1)
	simulation.input['rsi'] = float(rsi_val)
	simulation.input['stoch'] = float(stoch_val)
	simulation.input['obv'] = scaleRange(obv_val,orig_min=min(obv_range), orig_max=max(obv_range), min=0, max=1)

	try:
		simulation.compute()
		if simulation.output['action'] > 20:
			print('Recommended to buy {}'.format(symbol))
		elif simulation.output['action'] > 10:
			print('Recommended to hold {}'.format(symbol))
		else:
			print('Recommended to sell {}'.format(symbol))
	except:
		print('No enough information to make decision for {}'.format(symbol))

print('init fuzzy system...')

# membership function
bool_range = np.arange(0,1.1,0.1,dtype=np.float32)
hundred_range = np.arange(0,101,1,dtype=np.float32)
action_range = np.arange(0,31,dtype=np.float32)

macd = ctrl.Antecedent(bool_range, 'macd') 
rsi = ctrl.Antecedent(hundred_range, 'rsi')
stoch = ctrl.Antecedent(hundred_range, 'stoch')
obv = ctrl.Antecedent(bool_range, 'obv') 
action = ctrl.Consequent(action_range, 'action')

macd['L'] = fuzz.trimf(bool_range,[0,0,1])
macd['H'] = fuzz.trimf(bool_range,[0,1,1])

rsi['L'] = fuzz.trimf(hundred_range,[0,0,30])
rsi['M'] = fuzz.trimf(hundred_range,[30,50,70])
rsi['H'] = fuzz.trimf(hundred_range,[70,100,100])

stoch['L'] = fuzz.trimf(hundred_range,[0,0,20])
stoch['M'] = fuzz.trimf(hundred_range,[20,50,80])
stoch['H'] = fuzz.trimf(hundred_range,[80,100,100])

obv['L'] = fuzz.trimf(bool_range,[0,0,1])
obv['H'] = fuzz.trimf(bool_range,[0,1,1])

action['S'] = fuzz.trimf(action_range,[0,0,10])
action['H'] = fuzz.trimf(action_range,[10,15,20])
action['B'] = fuzz.trimf(action_range,[20,30,30])

# defuzzification method
action.defuzzify_method='centroid'

print('init rules...')

# rule
rule = list()
rule.append(
	ctrl.Rule(	antecedent=((macd['H']&rsi['L']&stoch['L']&obv['H'])|
							(macd['L']&rsi['H']&stoch['H']&obv['L'])|
							(macd['H']&rsi['M']&stoch['M']&obv['H'])|
							(rsi['L']&stoch['L']&obv['H'])),
				consequent=action['B'], label='rule B')
	)
rule.append(
	ctrl.Rule(	antecedent=((macd['L']&rsi['M']&stoch['H']&obv['L'])|
							(rsi['H']&stoch['H']&obv['L'])|
							(macd['L']&rsi['H']&stoch['H'])),
				consequent=action['S'], label='rule S')
	)
rule.append(
	ctrl.Rule(	antecedent=((macd['L']&rsi['M']&stoch['M'])|
							(macd['H']&rsi['M']&stoch['M']&obv['L'])),
				consequent=action['H'], label='rule H')
	)

# init 
system = ctrl.ControlSystem(rules=rule)
sim = ctrl.ControlSystemSimulation(system)
 
print('retrieve stock data...')

recommend(sim,symbol)







