/* Defininig the sets */
set timeSteps;
set processes;
set markets;
set storageUnits;
set standardUtilities;
set utilities := standardUtilities union markets union storageUnits;
set units := utilities union processes;
set layers;
set layersOfUnit{u in units};
set mainLayerOfUnit{u in units};
set unitsOfLayer{l in layers} := setof{u in units : l in layersOfUnit[u]} u;
set marketLayers := setof{u in markets, l in layersOfUnit[u]} l;
set outputMarketLayers := setof{u in markets, l in layersOfUnit[u]} (u, l);

set chargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;
set dischargingUtilitiesOfStorageUnit{u in storageUnits} within utilities;

set nonmarketUtilities := utilities diff markets;
set nonstorageUtilities within utilities := utilities diff storageUnits;
# set nonstorageUnits := nonstorageUtilities union processes;
# set chargingUtilitiesOfUnit{su in storageUnits};
# set dischargingUtilitiesOfUnit{su in storageUnits};
# set chargingUtilities within utilities := setof{u in storageUnits, ch in chargingUtilitiesOfUnit[u]} ch;
# set dischargingUtilities within utilities := setof{u in storageUnits, dis in dischargingUtilitiesOfUnit[u]} dis;
# set powerLimitUnits within utilities := (nonstorageUtilities diff chargingUtilities) diff dischargingUtilities;

/* Defining the parameters */
param POWER_MAX{u in nonstorageUtilities, l in layersOfUnit[u]} default 0;
param POWER_MAX_REL{u in nonstorageUtilities, l in layersOfUnit[u], t in timeSteps} default 1;

/* Storage-related parameters */
param ENERGY_MAX{u in storageUnits} default 0;
param CRATE{u in storageUnits} default 1;
param ERATE{u in storageUnits} default 1;
param STORAGE_CYCLIC_ACTIVE default 1;

/* General parameters */
param POWER{p in processes, l in layersOfUnit[p], t in timeSteps};
param TIME_STEP_DURATION;
param OCCURRANCE;

/* Cost-related parameters */
param SPECIFIC_INVESTMENT_COST_ANNUALIZED{u in nonmarketUtilities} default 0;  # It is the annualized cost
param ENERGY_AVERAGE_PRICE{u in markets, l in layersOfUnit[u]} default 0;
param ENERGY_PRICE_VARIATION{u in markets, l in layersOfUnit[u], t in timeSteps} default 1;


/* Defining the variables */
var power{u in units, l in layersOfUnit[u], t in timeSteps};
var energyStorageLevel{u in storageUnits, l in layersOfUnit[u], t in timeSteps} >=0;
var energyStorageLevel0{u in storageUnits, l in layersOfUnit[u]} >=0;
var unitAnnualizedInvestmentCost{u in nonmarketUtilities} >= 0;
var layer_operating_cost{(u,l) in outputMarketLayers} ;
var ics{u in nonmarketUtilities, t in timeSteps} >= 0, <= 1;
var size{u in nonmarketUtilities} >= 0;

var CAPEX;
var OPEX;


minimize obj: CAPEX + OPEX;

s.t. calculate_capex: CAPEX = sum{u in nonmarketUtilities} unitAnnualizedInvestmentCost[u]; 

s.t. calculate_opex: OPEX = sum{(u,l) in outputMarketLayers} layer_operating_cost[u,l] ;

s.t. calculate_investment_cost{u in nonmarketUtilities}: unitAnnualizedInvestmentCost[u] = size[u] * SPECIFIC_INVESTMENT_COST_ANNUALIZED[u];

s.t. calculate_operating_cost{u in markets, l in layersOfUnit[u]}: layer_operating_cost[u,l] = sum{t in timeSteps} (power[u,l,t] * ENERGY_AVERAGE_PRICE[u,l] * ENERGY_PRICE_VARIATION[u,l,t]) * TIME_STEP_DURATION * OCCURRANCE;

s.t. layer_balance{l in layers, t in timeSteps}: sum{u in unitsOfLayer[l]} (power[u,l,t]) = 0;

s.t. component_load{u in standardUtilities, l in layersOfUnit[u], t in timeSteps}: power[u,l,t] = ics[u,t] * POWER_MAX[u,l] * POWER_MAX_REL[u,l,t]; 
s.t. sale_to_market_limits{u in markets, l in layersOfUnit[u], t in timeSteps: POWER_MAX[u,l] < 0}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] <= power[u,l,t] <= 0;
s.t. purchase_from_market_limits{u in markets, l in layersOfUnit[u], t in timeSteps: POWER_MAX[u,l] > 0}: POWER_MAX[u,l] * POWER_MAX_REL[u,l,t] >= power[u,l,t] >= 0;

s.t. componentSizing{u in standardUtilities, l in mainLayerOfUnit[u], t in timeSteps}: size[u] >= ics[u,t] * abs(POWER_MAX[u,l]); 

s.t. process_power{p in processes, l in layersOfUnit[p], t in timeSteps}: power[p,l,t] = POWER[p,l,t];

# Storage equations	
s.t. storage_balance{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: energyStorageLevel[u,l,t] = (if t == 1 
	then 
		energyStorageLevel0[u,l] - power[u,l,t]*TIME_STEP_DURATION 
	else 
		energyStorageLevel[u,l,t-1] - power[u,l,t]*TIME_STEP_DURATION 
	);

s.t. storage_cyclic_constraint{u in storageUnits, l in layersOfUnit[u]}: 
	energyStorageLevel0[u,l] = (if STORAGE_CYCLIC_ACTIVE = 1
	then
		energyStorageLevel[u,l,card(timeSteps)]
	else
		0
	);
s.t. storage_max_energy{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: 
	energyStorageLevel[u,l,t] <= size[u];
s.t. storage_max_energy2{u in storageUnits}: 
	size[u] <= ENERGY_MAX[u];
s.t. storage_max_ch_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: 
	power[u,l,t] >= -size[u] * CRATE[u];
s.t. storage_max_dis_power{u in storageUnits, l in layersOfUnit[u], t in timeSteps}: 
	power[u,l,t] <= size[u] * ERATE[u];
s.t. storage_ch_power_cost{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}: 
	power[ch,l,t] <= size[u] * CRATE[u];
s.t. storage_dis_power_cost{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}: 
	power[dis,l,t] >= -size[u] * ERATE[u];	
s.t. charging_power_only_positive{u in storageUnits, l in layersOfUnit[u], ch in chargingUtilitiesOfStorageUnit[u], t in timeSteps}: 
	power[ch,l,t] >= 0; 
s.t. discharging_power_only_negative{u in storageUnits, l in layersOfUnit[u], dis in dischargingUtilitiesOfStorageUnit[u], t in timeSteps}: 
	power[dis,l,t] <= 0; 