# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 10:07:08 2019

@author: kr_fl
"""

import os
import numpy as np
import pandas as pd
import datetime
from sklearn.ensemble import RandomForestRegressor 
from sklearn.model_selection import train_test_split
from sklearn.externals import joblib

os.chdir('E:\MIT\Capstone')
os.getcwd()

exec(open('scripts/functions.py').read())
exec(open('scripts/setup_stats.py').read())

customer_clean = pd.read_csv("data/customer_clean.csv", index_col = 'Unnamed: 0')

date_columns = ['Container Unload From Vessel-Actual',
                'ATA', 'ATD', 'ETA', 'ETD', 'Latest Receipt Date',
                'Book Date', 'Expected Receipt Date', 'Actual Receipt Date']

for column in date_columns:
    print('start converting column', column, 'to datetime...')
    customer_clean[column] = pd.to_datetime(customer_clean[column],
                                            format = '%Y-%m-%d')
print('begin creating new columns...')

##########################################################################################
# get relevant variables

#stat = stat[stat['ETP'] > 0]
#stat = stat[(stat['y_book'] > 0) & (stat['y_book'] < 150)]

# get model departed
customer_clean = customer_clean[customer_clean['ATD'].isna() == False]
customer_clean['departure_day'] = customer_clean.apply(lambda x: x['ATD'].strftime('%A'), axis=1)
customer_clean['late_departure'] = np.where((customer_clean['ATD']-customer_clean['ETD']).dt.days > 0, 1, 0) # if vessel left after scheduled time
customer_clean['quarter'] = customer_clean['ETD'].dt.quarter

print('created departed columns...')
model_route = (customer_clean.merge(stat_pod, on=['Final Port Of Discharge', 'customer'])
                             .merge(stat_route_y, on=['Carrier', 'Original Port Of Loading', 'Final Port Of Discharge'])
                             .merge(stat_route, on=['Carrier', 'Original Port Of Loading', 'Final Port Of Discharge'])
                             .merge(stat_schedule,
                                    on=['Carrier', 'Original Port Of Loading',
                                        'Final Port Of Discharge', 'departure_day'],
                                    how = 'left')
                             .merge(stat_quarter, on=['quarter']))

model_route['schedule'] = np.where(model_route['schedule'].isna(),
                                   model_route['route_mean'],
                                   model_route['schedule'])
print('merged departed statistics...')
model_route = model_route[(model_route['y_depart'] > 0) & (model_route['y_depart'] < 40)]
model_route_ready = model_route[['quarter_z', 'pod_mean', 'pod_std', 'mean_all_departed',
                           'cap', 'late_departure', 'schedule', 'y_depart',
                           'Container Unload From Vessel-Actual']]
model_route_ready = model_route_ready.dropna()
print('model route ready!')

###############################################################################################
# get model received

customer_clean = customer_clean[customer_clean['ETD'].isna() == False]
customer_clean['departure_day'] = customer_clean.apply(lambda x: x['ETD'].strftime('%A'), axis=1)

customer_clean['quarter'] = customer_clean['ETD'].dt.quarter
customer_clean['Origin Service'] = np.where(customer_clean['Origin Service'] == 'CFS', 1, 0)
customer_clean['poo_late'] = (customer_clean['Expected Receipt Date']-customer_clean['Actual Receipt Date']).dt.days
customer_clean['poo_late'] = np.where(customer_clean['poo_late'] >= 0, 0, 1)
customer_clean['poo_latest'] = (customer_clean['Latest Receipt Date']-customer_clean['Actual Receipt Date']).dt.days
customer_clean['poo_latest'] = np.where(customer_clean['poo_latest'] >= 0, 0, 1)

print('created received columns...')
model_received = (customer_clean.merge(stat_pod, on=['Final Port Of Discharge', 'customer'])
                                .merge(stat_route, on=['Carrier', 'Original Port Of Loading', 'Final Port Of Discharge'])
                                .merge(stat_schedule,
                                       on=['Carrier', 'Original Port Of Loading',
                                           'Final Port Of Discharge', 'departure_day'],
                                       how = 'left')
                                .merge(stat_quarter, on=['quarter'])
                                .merge(stat_poo, on=['Original Port Of Loading', 'Shipper']))
model_received['schedule'] = np.where(model_received['schedule'].isna(),
                                      model_received['route_mean'],
                                      model_received['schedule'])
print('merged with statistics...')

features = ['pod_mean', 'pod_std', 'poo_mean', 'poo_std', 'poo_late', 'poo_latest',
            'quarter_z', 'schedule', 'cap', 'Origin Service', 'holiday', 'y_receive',
            'Container Unload From Vessel-Actual']

model_received = model_received[(model_received['y_depart'] > 0) & (model_received['y_depart'] < 40)]
model_received = model_received[(model_received['y_receive'] > 0) & (model_received['y_receive'] < 70)]
model_received = model_received[(model_received['y_book'] > 0) & (model_received['y_book'] < 100)]
model_received = model_received.dropna(subset = features)
model_received_ready = model_received[features]
#model_booked_ready = (model_booked_ready.join(pd.get_dummies(model_booked_ready['Carrier']))
#                                        .drop(['ZIMU','Carrier'], axis=1))
print('model received ready...')

###############################################################################################
# get variables booked

customer_clean['quarter'] = customer_clean['Expected Receipt Date'].dt.quarter
customer_clean['ETP'] = (customer_clean['Expected Receipt Date'] - customer_clean['Book Date']).dt.days   # expected time between booking and receival
customer_clean['Origin Service'] = np.where(customer_clean['Origin Service'] == 'CFS', 1, 0)
print('created booked columns...')

model_booked = (customer_clean.merge(stat_pod, on=['Final Port Of Discharge', 'customer'])
                              .merge(stat_route, on=['Carrier', 'Original Port Of Loading', 'Final Port Of Discharge'])
                              .merge(stat_quarter, on=['quarter'])
                              .merge(stat_poo, on=['Original Port Of Loading', 'Shipper']))

print('merged with statistics...')

features = ['quarter_z', 'pod_mean', 'pod_std', 'poo_mean', 'poo_std', 'route_mean',
            'Origin Service', 'holiday', 'y_book', 'ETP',
            'Container Unload From Vessel-Actual']

model_booked = model_booked[(model_booked['y_depart'] > 0) & (model_booked['y_depart'] < 40)]
model_booked = model_booked[(model_booked['y_book'] > 0) & (model_booked['y_book'] < 100)]
model_booked = model_booked.dropna(subset = features)
model_booked_ready = model_booked[features]
#model_booked_ready = (model_booked_ready.join(pd.get_dummies(model_booked_ready['Carrier']))
#                                        .drop(['ZIMU','Carrier'], axis=1))
print('model booked ready...')

##########################################################################################
##########################################################################################

#X_route = ['quarter_z', 'pod_mean', 'pod_std', 'mean_all_departed', 'cap', 'late_departure', 'schedule']
model = model_route_ready
model = model.rename(columns={'y_depart':'y', 'y_book':'y', 'y_receive':'y'})

date = max(model['Container Unload From Vessel-Actual']) - datetime.timedelta(days=365)
train = model[model['Container Unload From Vessel-Actual'] < date].drop('Container Unload From Vessel-Actual', axis=1)
test = model[model['Container Unload From Vessel-Actual'] >= date].drop('Container Unload From Vessel-Actual', axis=1)

# random forest
metrics_total_test = pd.DataFrame({'trees': [],
                            'depth': [],
                            'MAPE': [],
                            'MAE': []})
metrics_total_train = pd.DataFrame({'trees': [],
                            'depth': [],
                            'MAPE': [],
                            'MAE': []})

X_train = train.drop('y', axis=1)
y_train = train['y']
X_test = test.drop('y', axis=1)
y_test = test['y']

for depth in [10]: 
    for tree in [500]:
        rf = randomforest(max_depth = depth, trees = tree, features = 'sqrt')
        rf.fit(X_train, y_train)

        y_hat = rf.predict(X_test)
        m = print_metrics(y_hat, y_test)
        metrics_test = pd.DataFrame({'trees': [tree],
                                     'depth': [depth],
                                     'MAPE': [m['MAPE'][0]],
                                     'MAE': [m['MAE'][0]]})
        metrics_total_test = metrics_total_test.append(metrics_test)
        
        y_hat_train = rf.predict(X_train)
        m = print_metrics(y_hat_train, y_train)
        metrics_train = pd.DataFrame({'trees': [tree],
                                      'depth': [depth],
                                      'MAPE': [m['MAPE'][0]],
                                      'MAE': [m['MAE'][0]]})
        metrics_total_train = metrics_total_train.append(metrics_train)
        print('\n', metrics_test)
        print('\n', 'finished tree: ', tree, '\n', 'depth: ', depth)

metrics_total_train
metrics_total_test.sort_values(['MAPE', 'MAE']).head(5)

metrics_total_test.to_csv('data/results/randomforest_test_route_2.csv')
metrics_total_train.to_csv('data/results/randomforest_train_route_2.csv')

feature_importance = (pd.DataFrame(test.drop('y',axis=1).columns,
                                   rf.feature_importances_)
                        .reset_index()
                        .sort_values('index', ascending=0))
feature_importance

# save output

output = model_route.ix[list(test.index.values)]
output['y_hat'] = y_hat
output.to_csv('data/results/route_test_new.csv')
filename = 'data/models/randomforest_route_1_3.joblib'
joblib.dump(rf, filename) 

# linear regression
from sklearn import linear_model
regr = linear_model.LinearRegression()
regr.fit(X_train, y_train)
print('fitted linear model...')

coef = pd.DataFrame({'names': X_train.columns, 'coeficients': regr.coef_})
y_hat = regr.predict(X_test)

print(print_metrics(y_hat, y_test))
print(coef)

###############################################################################
# base case
model = customer_clean[(customer_clean['y_book'] > 0) & (customer_clean['y_book'] < 100)]
model = model.rename(columns={'y_receive':'y'})

date = max(model['Container Unload From Vessel-Actual']) - datetime.timedelta(days=365)
train = model[model['Container Unload From Vessel-Actual'] < date].drop('Container Unload From Vessel-Actual', axis=1)
test = model[model['Container Unload From Vessel-Actual'] >= date].drop('Container Unload From Vessel-Actual', axis=1)

test_base = (model.groupby(['Carrier','Original Port Of Loading',
                            'Final Port Of Discharge'])['y']
                  .mean().reset_index().rename(columns={'y':'mean'})
                  .merge(model,
                         on=['Carrier','Original Port Of Loading', 'Final Port Of Discharge'],
                         how='right'))
    
test_base['mean'] = round(test_base['mean'], 2)

test_base = test_base[np.isnan(test_base['y_depart']) == False]
test_base = test_base[np.isnan(test_base['mean']) == False]

print_metrics(test_base['mean'], test_base['y_depart'])
test_base.columns


