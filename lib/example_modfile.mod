###snapshot-version: 0.1.6
###model-start
set timeSteps;
set processes;
set markets;
set storageUnits;
set standardUtilities;
set utilities = standardUtilities union markets union storageUnits;
set units = utilities union processes;
set layers;
set layersOfUnit{u in units};
set mainLayerOfUnit{u in units};
set unitsOfLayer{l in layers}  =  setof {u in units: l in  layersOfUnit[u]} u;
set outputMarketLayers =  setof {u in markets, l in  layersOfUnit[u]} (u,l);
set nonmarketUtilities = utilities diff markets;
set unitsWithMinimumSizeIfInstalled within nonmarketUtilities;
set chargingUtilitiesOfStorageUnit{u in storageUnits}  within utilities;
set dischargingUtilitiesOfStorageUnit{u in storageUnits}  within utilities;
set nonStorageUtilities within utilities = utilities diff storageUnits;
param POWER_MAX{u in nonStorageUtilities, l in  layersOfUnit[u]}  default 0;
param SIZE_MIN_IF_INSTALLED{u in unitsWithMinimumSizeIfInstalled} default 0;
param POWER{p in processes, l in  layersOfUnit[p], t in timeSteps};
param TIME_STEP_DURATION;
param OCCURRANCE;
param SPECIFIC_INVESTMENT_COST_ANNUALIZED{u in utilities}  default 0;
param ENERGY_AVERAGE_PRICE{m in markets, l in  layersOfUnit[m]}  default 0;
param POWER_MAX_REL{u in nonStorageUtilities, l in  layersOfUnit[u], t in
  timeSteps}  default 1;
param ENERGY_PRICE_VARIATION{m in markets, l in  layersOfUnit[m], t in
  timeSteps}  default 1;
param ENERGY_MAX{u in storageUnits}  default 0;
param CRATE{u in storageUnits}  default 1;
param ERATE{u in storageUnits}  default 1;
param STORAGE_CYCLIC_ACTIVE default 1;
var power{u in units, l in  layersOfUnit[u], t in timeSteps};
var layer_operating_cost{(u,l) in outputMarketLayers};
var ics{u in nonmarketUtilities, t in timeSteps}  >= 0
     <= 1;
var ips{u in unitsWithMinimumPowerIfInstalled} binary;
var OPEX;
var energyStorageLevel{u in storageUnits, l in  layersOfUnit[u], t in
  timeSteps}  >= 0;
var energyStorageLevel0{u in storageUnits, l in  layersOfUnit[u]}  >= 0;
var unitAnnualizedInvestmentCost{u in nonmarketUtilities}  >= 0;
var size{u in nonmarketUtilities}  >= 0;
var CAPEX;
var TOTEX;
minimize obj: TOTEX;
subject to calculate_opex: OPEX == sum{(u,l) in outputMarketLayers}
  layer_operating_cost[u,l];
subject to layer_balance{l in layers, t in timeSteps} : sum{u in
   unitsOfLayer[l]} power[u,l,t] == 0;
subject to process_power{p in processes, l in  layersOfUnit[p], t in
  timeSteps} : power[p,l,t] == -POWER[p,l,t];
subject to component_sizing{u in standardUtilities, l in  mainLayerOfUnit[u],
  t in timeSteps} : size[u] >= ics[u,t]*abs(POWER_MAX[u,l]);
subject to component_sizing_with_minimum_power_if_installed{u in unitsWithMinimumPowerIfInstalled, l in  mainLayerOfUnit[u], t in timeSteps} : 
	size[u] >= ics[u,t]*abs(POWER_MAX[u,l]); 
subject to calculate_capex: CAPEX == sum{u in nonmarketUtilities}
  unitAnnualizedInvestmentCost[u];
subject to calculate_investment_cost{u in nonmarketUtilities} :
  unitAnnualizedInvestmentCost[u] == size[u]*
  SPECIFIC_INVESTMENT_COST_ANNUALIZED[u];
subject to calculate_totex: TOTEX == CAPEX + OPEX;
subject to calculate_operating_cost_time_dependent{u in markets, l in
   layersOfUnit[u]} : layer_operating_cost[u,l] == sum{t in timeSteps}
  power[u,l,t]*ENERGY_AVERAGE_PRICE[u,l]*ENERGY_PRICE_VARIATION[u,l,t]*
  TIME_STEP_DURATION*OCCURRANCE;
subject to component_load{u in standardUtilities, l in  layersOfUnit[u],
  t in timeSteps} : power[u,l,t] == ics[u,t]*POWER_MAX[u,l]*POWER_MAX_REL[u,l,
  t];
subject to purchase_market_limits{u in markets, l in  layersOfUnit[u],
  t in timeSteps: POWER_MAX[u,l] >= 0} : 0 <= power[u,l,t] <= POWER_MAX[u,l]*
  POWER_MAX_REL[u,l,t];
subject to selling_market_limits{u in markets, l in  layersOfUnit[u], t in
  timeSteps: POWER_MAX[u,l] <= 0} : POWER_MAX[u,l]*POWER_MAX_REL[u,l,t] <=
  power[u,l,t] <= 0;
subject to storage_balance{u in storageUnits, l in  layersOfUnit[u], t in
  timeSteps} : energyStorageLevel[u,l,t] ==  if t == 0 then
  energyStorageLevel0[u,l] - power[u,l,t]*TIME_STEP_DURATION else
  energyStorageLevel[u,l,t - 1] - power[u,l,t]*TIME_STEP_DURATION;
subject to storage_cyclic_constraint{u in storageUnits, l in  layersOfUnit[u]
  } : energyStorageLevel[u,l,1] <= STORAGE_CYCLIC_ACTIVE*
  energyStorageLevel[u,l,card(timeSteps) - 1];
subject to storage_max_energy{u in storageUnits, l in  layersOfUnit[u],
  t in timeSteps} : energyStorageLevel[u,l,t] <= size[u];
subject to storage_max_energy2{u in storageUnits} : size[u] <= ENERGY_MAX[u];
subject to storage_max_ch_power{u in storageUnits, l in  layersOfUnit[u],
  t in timeSteps} : power[u,l,t] >= -(size[u]*CRATE[u]);
subject to storage_max_dis_power{u in storageUnits, l in  layersOfUnit[u],
  t in timeSteps} : power[u,l,t] <= size[u]*ERATE[u];
subject to storage_ch_power_cost{u in storageUnits, l in  layersOfUnit[u],
  ch in  chargingUtilitiesOfStorageUnit[u], t in timeSteps} : power[ch,l,t]
   <= size[u]*CRATE[u];
subject to storage_dis_power_cost{u in storageUnits, l in  layersOfUnit[u],
  dis in  dischargingUtilitiesOfStorageUnit[u], t in timeSteps} : power[dis,l,
  t] >= -(size[u]*ERATE[u]);
subject to charging_power_only_positive{u in storageUnits, l in
   layersOfUnit[u], ch in  chargingUtilitiesOfStorageUnit[u], t in
  timeSteps} : power[ch,l,t] >= 0;
subject to discharging_power_only_negative{u in storageUnits, l in
   layersOfUnit[u], dis in  dischargingUtilitiesOfStorageUnit[u], t in
  timeSteps} : power[dis,l,t] <= 0;
###model-end

###current-problem/environment-start
problem Initial;
environ Initial;
###current-problem/environment-end

###objectives-start
objective obj;
###objectives-end

###fixes-start
###fixes-end

###drop-restore-start
###drop-restore-end

