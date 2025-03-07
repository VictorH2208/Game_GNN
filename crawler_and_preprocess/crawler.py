# standard library imports
import csv 
import datetime as dt
import json
import os
import statistics
import time
import urllib.error

# third-party imports
import numpy as np
import pandas as pd
import requests
import sys


# from tqdm.notebook import tqdm
tqdm = lambda x: x

# customisations - ensure tables show all columns
pd.options.display.max_columns = 100


def get_request(url, parameters=None):
    """Return json-formatted response of a get request using optional parameters.
    
    Parameters
    ----------
    url : string
    parameters : {'parameter': 'value'}
        parameters to pass as part of get request
    
    Returns
    -------
    json_data
        json-formatted response (dict-like)
    """
    try:
        response = requests.get(url=url, params=parameters)
    except SSLError as s:
        print('SSL Error:', s)
        
        for i in range(5, 0, -1):
            print('\rWaiting... ({})'.format(i), end='')
            time.sleep(1)
        print('\rRetrying.' + ' '*10)
        
        # recusively try again
        return get_request(url, parameters)
    
    if response:
        return response.json()
    else:
        # response is none usually means too many requests. Wait and try again 
        print('No response, waiting 10 seconds...')
        time.sleep(10)
        print('Retrying.')
        return get_request(url, parameters)

def get_app_data(start, stop, parser, pause):
    """Return list of app data generated from parser.
    
    parser : function to handle request
    """
    app_data = []
    
    # iterate through each row of app_list, confined by start and stop
    for index, row in app_list[start:stop].iterrows():
        print('Current index: {}'.format(index), end='\r')
        
        appid = row['appid']
        name = row['name']

        # retrive app data for a row, handled by supplied parser, and append to list
        data = parser(appid, name)
        app_data.append(data)

        time.sleep(pause) # prevent overloading api with requests
    
    return app_data


def process_batches(parser, app_list, download_path, data_filename, index_filename,
                    columns, begin=0, end=-1, batchsize=100, pause=1):
    """Process app data in batches, writing directly to file.
    
    parser : custom function to format request
    app_list : dataframe of appid and name
    download_path : path to store data
    data_filename : filename to save app data
    index_filename : filename to store highest index written
    columns : column names for file
    
    Keyword arguments:
    
    begin : starting index (get from index_filename, default 0)
    end : index to finish (defaults to end of app_list)
    batchsize : number of apps to write in each batch (default 100)
    pause : time to wait after each api request (defualt 1)
    
    returns: none
    """
    print('Starting at index {}:\n'.format(begin))
    
    # by default, process all apps in app_list
    if end == -1:
        end = len(app_list) + 1
    
    # generate array of batch begin and end points
    batches = np.arange(begin, end, batchsize)
    batches = np.append(batches, end)
    
    apps_written = 0
    batch_times = []
    data_list = []
    
    for i in tqdm(range(len(batches) - 1)):
        start_time = time.time()
        
        start = batches[i]
        stop = batches[i+1]
        
        app_data = get_app_data(start, stop, parser, pause)
                
        # writing app data to file
        # with open(rel_path, 'a', newline='', encoding='utf-8') as f:
        #     writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        for j in range(1,0,-1):
            print("\rAbout to write data, don't stop script! ({})".format(j), end='')
            time.sleep(0.5)
        
        # writer.writerows(app_data)
        data_list += app_data
        print('\rExported lines {}-{} to {}.'.format(start, stop-1, data_filename), end=' ')
            
        apps_written += len(app_data)
        
        # idx_path = os.path.join(download_path, index_filename)
        
        # writing last index to file
        # with open(idx_path, 'w') as f:
            # index = stop
            # print(index, file=f)
            
        # logging time taken
        end_time = time.time()
        time_taken = end_time - start_time
        
        batch_times.append(time_taken)
        mean_time = statistics.mean(batch_times)
        
        est_remaining = (len(batches) - i - 2) * mean_time
        
        remaining_td = dt.timedelta(seconds=round(est_remaining))
        time_td = dt.timedelta(seconds=round(time_taken))
        mean_td = dt.timedelta(seconds=round(mean_time))
        
        print('Batch {} time: {} (avg: {}, remaining: {})'.format(i, time_td, mean_td, remaining_td))
            
    print('\nProcessing batches complete. {} apps written'.format(apps_written))
    return data_list

def parse_steam_request(appid, name):
    """Unique parser to handle data from Steam Store API.
    
    Returns : json formatted data (dict-like)
    """
    url = "http://store.steampowered.com/api/appdetails/"
    parameters = {"appids": appid}
    
    json_data = get_request(url, parameters=parameters)
    json_app_data = json_data[str(appid)]
    
    if json_app_data['success']:
        data = json_app_data['data']
    else:
        data = {'name': name, 'steam_appid': appid}
        
    return data

if __name__ == '__main__':
    
    if len(sys.argv)==3:
        try:
            start_page, end_page = int(sys.argv[1]), int(sys.argv[2])
        except:
            print('please input integers!!!')
    else:
        print('please specify the pages: startpage and endpage')
        print('exampe: python crawler.py 10 20')


    download_path = '../data/download'
    steam_app_data = 'steam_app_data.csv'
    steam_index = 'steam_index.txt'

    steam_columns = [
        'type', 'name', 'steam_appid', 'required_age', 'is_free', 'controller_support',
        'dlc', 'detailed_description', 'about_the_game', 'short_description', 'fullgame',
        'supported_languages', 'header_image', 'website', 'pc_requirements', 'mac_requirements',
        'linux_requirements', 'legal_notice', 'drm_notice', 'ext_user_account_notice',
        'developers', 'publishers', 'demos', 'price_overview', 'packages', 'package_groups',
        'platforms', 'metacritic', 'reviews', 'categories', 'genres', 'screenshots',
        'movies', 'recommendations', 'achievements', 'release_date', 'support_info',
        'background', 'content_descriptors'
    ]

    all_page = []
    for page_num in tqdm(range(start_page, end_page+1)):
        url = "http://steamspy.com/api.php?request=all&page=" + str(page_num)
        parameters = {"request": "all"}

        # request 'all' from steam spy and parse into dataframe
        json_data = get_request(url, parameters=parameters)
        steam_spy_all = pd.DataFrame.from_dict(json_data, orient='index')

        # generate sorted app_list from steamspy data
        app_list = steam_spy_all[['appid', 'name']].sort_values('appid').reset_index(drop=True)



        # Set end and chunksize for demonstration - remove to run through entire app list
        data_list = process_batches(
            parser=parse_steam_request,
            app_list=app_list,
            download_path=download_path,
            data_filename=steam_app_data,
            index_filename=steam_index,
            columns=steam_columns,
            begin=0,
            end=-1,
            batchsize=30,
            pause = 1,
        )
        # print(data_list)
        all_page.append(data_list)
        all_data = data_list
        dict_list = {k: [all_data[i][k]  if k in all_data[i] else None for i in range(len(all_data))] for k in steam_columns}
        df = pd.DataFrame(dict_list)
        df.to_csv(f'{page_num}.csv', index=False)

    # all_data = []
    # for data_list in all_page:

        
    #     all_data = all_data+data_list
    
    # make all data into a dictionary
    # if a key doesn't present in a game, make the value of that game None
    # dict_list = {k: [all_data[i][k]  if k in all_data[i] else None for i in range(len(all_data))] for k in steam_columns}
    # df = pd.DataFrame(dict_list)
    # df.to_csv(f'{start_page}--{end_page}.csv', index=False)