import pandas as pd
from pulp import *
import time
import re
import warnings
import os

warnings.filterwarnings('ignore')
#pd.set_option('display.max_columns', 500)


start_time = time.time()

def formula_generator(data, variable, row, opt_lineup):
    '''This function determines what gets optimized'''
    return data.loc[row, opt_lineup] * variable #(round(data.loc[row, 'Ceiling'], 3) + round(data.loc[row, 'Projection']) + round(data.loc[row, 'Floor'], 3)) / 3 * variable


def fanduel_maximizer(data, i, opt_lineup):
    prob = pulp.LpProblem('FanduelSelections', LpMaximize)
    #print(data.loc[0,'Projection'])
    decision_variables = []
    total_projections = ''
    salary_variables = []
    pg_variables = []
    sg_variables = []
    sf_variables = []
    pf_variables = []
    c_variables = []

    for row in range(len(data)):
        variable = str('x' + str(row))
        variable = pulp.LpVariable(str(variable), lowBound=0, upBound=1, cat='Integer')
        decision_variables.append(variable)
        #print(data.loc[row, 'Ceiling'])
        ### TODO Change this line below to change what gets optimized
        formula = formula_generator(data, variable, row, opt_lineup)
        total_projections += formula
        salary_variables.append(int(data.loc[row, 'Salaries']) * variable)
        if data.loc[row, 'Position'] == 'PG':
            pg_variables.append(variable)
            data.loc[row, 'Position #'] = 1
        elif data.loc[row, 'Position'] == 'SG':
            sg_variables.append(variable)
            data.loc[row, 'Position #'] = 2
        elif data.loc[row, 'Position'] == 'SF':
            sf_variables.append(variable)
            data.loc[row, 'Position #'] = 3
        elif data.loc[row, 'Position'] == 'PF':
            pf_variables.append(variable)
            data.loc[row, 'Position #'] = 4
        elif data.loc[row, 'Position'] == 'C':
            c_variables.append(variable)
            data.loc[row, 'Position #'] = 5
    #posit_map = {'PG':1,'SG':2,'SF':3,'PF':4,'C':5}
    #data['Position #'] = data['Position'].map(posit_map)


    #print(pg_variables)

    prob += total_projections
    prob += lpSum(decision_variables) == 9
    prob += lpSum(pg_variables) == 2
    prob += lpSum(sg_variables) == 2
    prob += lpSum(sf_variables) == 2
    prob += lpSum(pf_variables) == 2
    prob += lpSum(c_variables) == 1

    prob += lpSum(salary_variables) <= 60000


    #prob += lpSum()
    #print(prob)
    prob.writeLP('FanduelSelections.lp')

    optimization_result = prob.solve()

    assert optimization_result == pulp.LpStatusOptimal

    variable_name = []
    variable_value = []
    for v in prob.variables():
        variable_name.append(v.name)
        variable_value.append(v.varValue)

    df = pd.DataFrame({'variable' : variable_name, 'value': variable_value})
    for rownum, row in df.iterrows():
        value = re.findall(r'(\d+)', row['variable'])   # this removes the x from the variable name e.g. x10 -> 10
        df.loc[rownum, 'variable'] = int(value[0])

    df = df.sort_values(by='variable')

    for rownum, row in data.iterrows():
        for results_rownum, results_row in df.iterrows():
            if rownum == results_row['variable']:
                data.loc[rownum, 'Play?'] = results_row['value']
    selected_players = data[data['Play?'] == 1].sort_values(by='Position #')
    #selected_players = selected_players.loc[:, 'Player Name':'Projection']
     #selected_players = [i.replace(".","") for i in selected_players]

    print(selected_players)
    print('Total Salary: {}'.format(sum(selected_players['Salaries'])))
    print('Total Projection: {}'.format((sum(selected_players[opt_lineup]))))#+sum(selected_players['Projection'])+sum(selected_players['Floor'])) / 3))
    print('Actual Points: {}'.format(sum(selected_players['FD_PTS'])))
    end_time = time.time() - start_time
    print('Elapsed Time: {}'.format(round(end_time,3)) + ' seconds')

    return selected_players


if __name__ == "__main__":
    total_data = pd.read_csv('Combined_Roto_NBA_18-19.csv')

    start_date = '2018-10-16'
    end_date = '2019-04-10'
    date_range = pd.Series(pd.date_range(start_date, end_date)).astype(str).to_list()#.apply(lambda x: x.split('-')).to_list()  # Creates a list of datetime objects
    types_of_lineups = ['Projection', 'Floor']
    for date in date_range:
        #print(date+" Lineups")

        for type in types_of_lineups:
            print(date+" "+type+" Lineups")

            player_data = total_data[total_data['Date'] == date].reset_index(drop=True)
            #print(player_data)

            try:
                first_lineup = fanduel_maximizer(player_data, 1, type).reset_index(drop=True)
            except TypeError:
                continue
            data_path = os.path.join('Hist_Data',date,type)
            try:
                os.makedirs(data_path)
            except OSError:
                print ("Creation of the directory %s failed" % data_path)
            #else:
                #print ("Successfully created the directory %s " % path)
            first_lineup.to_csv(os.path.join(data_path, 'lineup1.csv'), index=False)
            for i in range(len(first_lineup)):
                print('Lineup {}'.format(i+2))
                updated_player_data = player_data[(player_data['Name'] != first_lineup.loc[i,'Name'])].reset_index(drop=True)
                players = fanduel_maximizer(updated_player_data, i+2, type)
                #print(players)
                #lineup = players['Name'].tolist()
                players.to_csv(os.path.join(data_path, 'lineup{}.csv'.format(i+2)), index=False)


            #print(first_lineup)
            #time.sleep(10)
