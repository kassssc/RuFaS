################################################################################
'''
RUFAS: Ruminant Farm Systems Model
File name: ration.py
Description:
Author(s): Kass Chupongstimun, kass_c@hotmail.com
'''
################################################################################

from numpy import exp
from RUFAS import util

#-------------------------------------------------------------------------------
# Function: optimize
#-------------------------------------------------------------------------------
def optimize(constraints, rqmts, objective, limits, nutrients_list, feed_types):
	'''
	TODO: Add DocString
	'''

	# LP_RHS [type_nutrient]
	RHS = [ rqmts[nutrient]['val'] for nutrient in nutrients_list ]

	# LHS [type_nutrient][type_feed]
	LHS = [ constraints[nutrient] for nutrient in nutrients_list ]

	# operators [type_nutrient]
	operators = [ rqmts[nutrient]['op'] for nutrient in nutrients_list ]

	# Objective [type_feed]
	objective = [ objective[feed_type] for feed_type in feed_types ]

	# Variables
	variables = list(feed_types)

	# min/max variable values [type_feed]
	min_v = [0]*len(feed_types)
	max_v = [ limits[feed_type] for feed_type in feed_types ]

	#util.LP_print(LHS, RHS, objective, variables, operators,
	#			  "minimize", "RATION", min_v, max_v)

	return util.LP_solve(LHS, RHS, objective, variables, operators,
						 "minimize", "RATION", min_v, max_v)

#-------------------------------------------------------------------------------
# Function: calculate_rqmts
#-------------------------------------------------------------------------------
def calculate_rqmts(parity, WIM, AMF, BWR, base_NED, housing,
					nutrients_list, milk_production_multiplier):
	'''
	TODO: Add DocString
	'''

	#
	# FIC: Fiber intake capacity
	#
	if parity > 1:
		FIC = ( 0.564 * (WIM + 0.857)**0.360 *
				exp(-0.0186 * (WIM + 0.857)) )
	else:
		FIC = ( 0.388 * (WIM + 3)**0.588 *
				exp(-0.0277 * (WIM + 3)) )

	#
	# Estimate Base milk production (base milk yield)
	# BaseMY is the milk base milk yield estimated from breed specific lactation curve
	#
	if parity > 1:
		base_MY = ( 33.95 * WIM**0.2208 *
					exp(-0.03395 * WIM) )
	else:
		base_MY = ( 24.12 * WIM**0.1782 *
			 		exp(-0.02095 * WIM) )

	base_MY *= milk_production_multiplier

	#
	# Estimate Base milk fat
	# BaseMF is the base milk fat estimated from breed specific
	# average milk fat and compoMEInt lactation curve
	#
	base_MF = ( 1.4286 * AMF * WIM**-0.24 *
				exp(0.016 * WIM) )

	#
	# Estimate Body Weight
	# The body weight is estimated as a function of DIM and
	# the ratio of the calving weight of the breed to that of holsteins
	#
	if parity > 1:
		BW = ( BWR * 690 * ((WIM + 1.57) ** -0.0803) *
			   exp(0.00720 * (WIM + 1.57)))
	else:
  		BW = ( BWR * 567 * ((WIM + 1.71)** -0.0730) *
  			   exp(0.00869 * (WIM + 1.71)))


  	#
	# Estimate Change in Body weight
	#
	if WIM < 56:
		if parity > 1:
			DBW = ( BWR * 690 * ((WIM + 0.57)**(-0.0803)) *
					exp(0.00720 * (WIM + 0.57)))
		else:
			DBW = ( BWR * 567 * ((WIM + 0.71)**(-0.730)) *
					exp(0.00869 * (WIM + 0.71)))

		# change in body weight (kg/d)
		CBW = (BW - DBW) / 7

	#
	# Estimate eMEIrgy equivalent of Change in Bodyweight
	#
	if WIM < 11:
		CS = 3.4
	else:
		CS = 5 # change eMEIrgy value depending on stage in lactation
	MEIKG = 0.5381 * CS + 3.2855 # MEIt eMEIrgy in deposited or mobilized body (Mcal/kg bw) tissue

	if CBW < 0:
		MECBW = MEIKG * CBW/0.785/100
	else:
		MECBW = MEIKG * CBW/0.75/100

	#
	# Estimate Maintenance EMEIrgy Req
	# MEIeds: BW
	#
	SBW = 0.96 * BW
	MEIM = 0.073 * (SBW ** 0.75)

	#
	# Estimate Activity EMEIrgy Rew
	# set number of hours, position changes and distances traveled
	# if housed in a barn, drylot or grazing
	#
	if housing == "barn":
		hours = 12
		posHG = 9
		flat_dist = 0.5
		slope_dist = 0.001
	elif housing == "drylot":
		hours = 15
		posHG = 9
		flat_dist = 1.5
		slope_dist = 0.001
	else:
		hours = 16
		posHG = 6
		flat_dist = 1.0
		slope_dist = 0.0

	stand  = 0.1 * hours * SBW/0.96
	chang  = 0.062 * posHG * SBW/0.96
	dist_F  = 0.621 * flat_dist * SBW/0.96
	dist_S  = 6.69 * slope_dist * SBW/0.96
	MEIACT = (stand + chang + dist_F + dist_S)/1000

	#
	# Estimate Maintenance Protein Req
	#
	MPM = 3.8 * SBW ** 0.75  # g metabolizable protein for maintenance

	#
	# Estimate lacatation eMEIrgy and protein Req
	# MEIeds: base_MY, base_MF
	#
	ME_mlk = base_MY * (0.3523 + 0.0962 * base_MF)/0.644  #Mcal ME required for milk
	PROT_mlk = 1.9 + 0.4 * base_MF  # milk protein %
	MP_mlk = 10 * PROT_mlk*base_MY/0.65  # g metabolizable protein for milk

	#
	# Sum total requisrements
	# MEIeds: MEIM, MEIACT, ME_mlk, MECBW, MPM
	#
	ME_req = MEIM/0.667 + MEIACT/0.667 + ME_mlk + MECBW # total ME req (Mcal)
	MP_req = MPM + MP_mlk # total MP rew (g)

	#
	# Estimate Rumen degradable and undegradable protein
	# MEIeds: base_NED, ME_req
	#
	base_MED = 1.095 * base_NED + 0.751 # BaseMED is the baseliMEI Metabolizable eMEIrgy of the diet
	DMI_est = ME_req / base_MED
	TDN = 0.31 * base_NED + 0.2 # Total digestible Nutrients (TDN) is a measure of diet quality/content used the the NRC
	MCP = 0.13 * TDN * DMI_est # MCP is microbial crude protein



	# Set Constraints limits based on requirements and intake capacity
	# (RHS of constraints matrix)
	# MEIeds: BW, FIC, base_NED, DMI_est, MP_req, MCP

	FI_max = 0.01025 * BW * FIC
	RV_min = 0
	NE_min = base_NED * DMI_est * (1 - 0.0206) - 0.7 * MP_req / 1000
	RPD_min = MCP / 0.9
	RUP_min = MP_req /1000 - 0.8 * 0.8 * MCP

	nutrient_rqmts = [
						{'op': '<=', 'val': FI_max},
						{'op': '>=', 'val': RV_min},
						{'op': '>=', 'val': NE_min},
						{'op': '>=', 'val': RPD_min},
						{'op': '>=', 'val': RUP_min}
					 ]

	return dict(zip(nutrients_list, nutrient_rqmts))

#-------------------------------------------------------------------------------
# Function: calculate_constraints
#-------------------------------------------------------------------------------
"""
def calculate_constraints(feed, nutrients_list):
	'''
	TODO: Add DocString
	'''

	# LHS
	FI = {}
	RV = {}
	NE = {}
	RDP = {}
	RUP = {}

	# Intermediates
	NH3 = {}
	unavail_prot = {}

	# Loop over types of feed
	for feed_type in feed.keys():
		#set FI, rumen volume, and MEIt eMEIrgy
		FI[feed_type] = feed[feed_type]['nutrition']['FI']
		RV[feed_type] = feed[feed_type]['nutrition']['RV']
		NE[feed_type] = feed[feed_type]['nutrition']['NE']

		# Use rumen degradable, total, and indigestible CP to estimate degradable and undegradable CP
		NH3[feed_type] = feed[feed_type]['nutrition']['CP'] * feed[feed_type]['nutrition']['RDP']

		if feed[feed_type]['nutrition']['conc'] == "conc":
			unavail_prot[feed_type] = 0.4 * feed[feed_type]['nutrition']['ICP']
		else: # feed[feed_type]['conc'] == "rough"
			unavail_prot[feed_type] = 0.7 * feed[feed_type]['nutrition']['ICP']

		RDP[feed_type] = NH3[feed_type] + 0.15 * feed[feed_type]['nutrition']['CP']
		RUP[feed_type] = 0.87 * (feed[feed_type]['nutrition']['CP'] - NH3[feed_type] -
								 (unavail_prot[feed_type] * feed[feed_type]['nutrition']['CP']))


	constraint = [
					[ FI[feed_type] for feed_type in feed.keys() ],
					[ RV[feed_type] for feed_type in feed.keys() ],
					[ NE[feed_type] for feed_type in feed.keys() ],
					[ RDP[feed_type] for feed_type in feed.keys() ],
					[ RUP[feed_type] for feed_type in feed.keys() ]
				 ]

	return dict(zip(nutrients_list, constraint))
"""