#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 10 16:15:06 2023

@author: alvar
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import date
import os
from datetime import datetime
from scipy import stats

def get_percentile_selected_period(df, date_column = 'year', value_column = 'gwchange', prct_column = 'pctl_gwchange', baseline_start_year = 1991, baseline_end_year = 2020):
    """Calculates the percentiles based on a fixed baseline period.
    
    Parameters
    ----------
    df : dataframe
        The input dataframe that has a datetime and a value column to obtain
        the percentiles
    date_column : str
        The column label of the datetime column
    value_column : str
        The column label of the columns with the values
    station_id_column : str
        The column label of the id of the stations or wells
    baseline_start_year: int
        The start year for obtaining percentiles with a fixed baseline
    baseline_end_year: int
        The end year for obtaining percentiles with a fixed baseline
        
    Returns
    -------
    series
        A series with percentiles calculated over the baseline period for the selected value column.
    """
    df_for_arr = df.loc[(df[date_column]>(baseline_start_year-1)) & (df[date_column]<(baseline_end_year+1))]
    arr = df_for_arr[value_column]
    arr = arr.dropna()
    # df[prct_column] = 0.01*stats.percentileofscore(arr, df[value_column])            
    return  0.01*stats.percentileofscore(arr, df[value_column])

#Data from: https://data.cnra.ca.gov/dataset/periodic-groundwater-level-measurements
gwdata = pd.read_csv('../../Data/Downloaded/groundwater/periodic_gwl_bulkdatadownload/measurements.csv')
stations = pd.read_csv('../../Data/Downloaded/groundwater/periodic_gwl_bulkdatadownload/stations.csv')


#Adding hydrologic region to gwdata
hr = gpd.read_file('../../Data/Input_Data/HRs/i03_Hydrologic_Regions.shp')
hr = hr.to_crs('epsg:4326')
stations_gdf = gpd.GeoDataFrame(stations, geometry=gpd.points_from_xy(stations.longitude, stations.latitude))
stations_gdf = stations_gdf.set_crs('epsg:4326')
stations_gdf = gpd.sjoin(stations_gdf, hr)

end_date = datetime.now().strftime('%Y-%m-%d') #today's date

#Merging data with stations
gwdata = gwdata.merge(stations_gdf, on='site_code')

def well_percentile(df, date_column = 'msmt_date', value_column = 'gse_gwe',
                    station_id_column = 'stn_id', initial_date = '1990-01-01',
                    end_date = end_date, subset = ['HR_NAME', ['Sacramento River']], 
                    maxgwchange = 30, pctg_data_valid=0):
    """Calculates the percentiles for groundwater annual and seasonal elevation changes, as well as the cumulative changes for each well.
    
    Parameters
    ----------
    df : dataframe
        The input dataframe that has a datetime and a value column to obtain
        the percentiles
    date_column : str
        The column label of the datetime column
    value_column : str
        The column label of the columns with the values
    station_id_column : str
        The column label of the id of the stations or wells
    initial_date: str
        The initial data to be included in the calculations. String in
        datetime format
    end_date: str
        The end data to be included in the calculations. String in
        datetime format
    subset: list
        A list that includes in the first place the column label to subset the
        data, and in second place the field values used for the subset. For
        instance, if we include ['HR_NAME', ['Sacramento River', 'South Coast']],
        the dataframe should include a column called HR_NAME, and it will be
        filtered only with the fields included in the second list (in this case
        'Sacramento River' and 'South Coast'). It could also be by basin, and
        select specific basins.
    maxgwchange: int
        The maximum allowable change in groundwater levels; values exceeding this threshold will be considered outliers.
    pctg_data_valid: int
        The threshold percentage for valid data; station data with validity exceeding this percentage will be filtered out.
        
    Returns
    -------
    dataframe
        The original dateframe adding the percentiles for the temporal period
    """
    
    #First we filter the data with the initial subset and date
    df[date_column] = pd.to_datetime(df[date_column], format='mixed')
    if subset is not None:
        df = df.loc[df[subset[0]].isin(subset[1])]
    df = df.loc[df[date_column]>=initial_date]
    df = df.loc[df[date_column]<=end_date]
    #Filter out all the readings above 300 ft (potentially confined aquifers)
    df = df.loc[df[value_column]<=300]
    df[value_column] = -df[value_column]
    
    #We filter by semester
    df['year']=df[date_column].dt.year
    df['semester']=1
    df.loc[df[date_column].dt.month>6,'semester']=2
    
    #Obtain median groundwater elevation by semester
    dfsem = df.groupby([subset[0], station_id_column, 'year', 'semester']).median(numeric_only=True).reset_index()
    dfsem['month']=3
    dfsem.loc[dfsem.semester>1, 'month']=9
    dfsem['day']=30
    dfsem.loc[dfsem.semester==1,"day"]=31
    dfsem['date'] = pd.to_datetime(dfsem[['year','month', 'day']])
    
    dfallst = pd.DataFrame()
    for station in np.unique(dfsem[station_id_column]):
        dfst = dfsem.loc[dfsem[station_id_column]==station].reset_index(drop=True)
        #Filter stations with less than
        if dfst[value_column].count()>(pctg_data_valid*2*(date.today().year - int(initial_date[0:4]) + 1)): #We want max of 20% of empty
            dfst['gwchange'] = dfst[value_column].diff(periods=2)
            dfst.loc[(dfst.gwchange>maxgwchange) | (dfst.gwchange<-maxgwchange),
                     'gwchange']=np.nan
            dfst.loc[(dfst.gwchange>maxgwchange) | (dfst.gwchange<-maxgwchange),
                     value_column]=np.nan
            
            #Percentile of gw elev annual change
            dfst = dfst.reset_index(drop=True)
            dfst['pctl_gwchange'] = get_percentile_selected_period(df=dfst, prct_column = 'pctl_gwchange')
            dfst['half_gwchange']=dfst.gwchange*0.5
            dfst['cumgwchange'] = dfst.half_gwchange.cumsum()
            dfst.loc[dfst['gwchange'].isna(),'cumgwchange']=np.nan
            dfst['pctl_cumgwchange'] = get_percentile_selected_period(df=dfst, value_column='cumgwchange')
                        
            
            #Perentile of seasonal gw elevation
            dfstsem1 = dfst.loc[dfst.semester==1]
            dfstsem1['pctl_gwelev'] = get_percentile_selected_period(df = dfstsem1, value_column = value_column)
            dfstsem1['pctl_cumgwchange'] = get_percentile_selected_period(df = dfstsem1, value_column = 'cumgwchange')
            dfstsem2 = dfst.loc[dfst.semester==2]
            dfstsem2['pctl_gwelev'] = get_percentile_selected_period(df = dfstsem2, value_column = value_column)
            dfstsem2['pctl_cumgwchange'] = get_percentile_selected_period(df = dfstsem2, value_column = 'cumgwchange')
            dfst = pd.concat([dfstsem1, dfstsem2]).sort_values(by='date')
            
            dfallst = pd.concat([dfallst,dfst])
    
    dfallst = dfallst.reset_index(drop=True)
    return dfallst

def regional_pctl_analysis(df, grouping_column='HR_NAME', stat = 'all'):
    """Calculates the percentiles for groundwater annual and seasonal elevation changes, as well as the cumulative changes for each hydrologic region.
        Applies a correction to the groundwater percentile values by calculating percentiles.
        (This correction is applied because median values tend to cluster around the middle of the range, resulting in fewer 
         extreme values (near 0 or 1) - By recalculating percentiles of these median values, we distribute the median values
         more evenly between 0 and 1)
    
    Parameters
    ----------
    df : dataframe
        The input dataframe comes from the output of the well_percentile function
    grouping_column : str
        The column label of the datetime column that is used to obtain the
        statistics (it could be the hydrologic region or the basin)
    stat : str
        It can be the median (median), the 25th percentile (perc25) or the 75th
        percentile (perc75), or all (obtaining the three of them)
        
    Returns
    -------
    dataframe
        The dateframe of percentiles and corrected percentiles for each hydrologic region
    """
    df['reporting']=1
    if (stat == 'median') or (stat == 'all'):
        median = df.groupby(['date',grouping_column]).median()
        median['stat']='median'
        median['pctl_gwchange_corr'] = median['pctl_gwchange'].rank(pct=True)
        median['pctl_cumgwchange_corr'] = median['pctl_cumgwchange'].rank(pct=True)       
        median['reporting2']=df.groupby(['date',grouping_column])['reporting'].sum()
    if (stat == 'perc25') or (stat == 'all'):
        perc25 = df.groupby(['date',grouping_column]).quantile(0.25)
        perc25['stat']='perc25'
        perc25['pctl_gwchange_corr'] = perc25['pctl_gwchange'].rank(pct=True)
        perc25['pctl_cumgwchange_corr'] = perc25['pctl_cumgwchange'].rank(pct=True)
        perc25['reporting2']=df.groupby(['date',grouping_column])['reporting'].sum()
    if (stat == 'perc75') or (stat == 'all'):
        perc75 = df.groupby(['date',grouping_column]).quantile(0.75)
        perc75['stat']='perc75'
        perc75['pctl_gwchange_corr'] = perc75['pctl_gwchange'].rank(pct=True)
        perc75['pctl_cumgwchange_corr'] = perc75['pctl_cumgwchange'].rank(pct=True)
        perc75['reporting2']=df.groupby(['date',grouping_column])['reporting'].sum()
    result = pd.DataFrame()
    if stat == 'median':
        result = pd.concat([median]).reset_index().sort_values(['stat', grouping_column, 'date'])
    if stat == 'perc25':
        result = pd.concat([perc25]).reset_index().sort_values(['stat', grouping_column, 'date'])
    if stat == 'perc75':
        result = pd.concat([perc75]).reset_index().sort_values(['stat', grouping_column, 'date'])
    elif stat == 'all':        
        result = pd.concat([median, perc25, perc75]).reset_index().sort_values(['stat', grouping_column, 'date'])
    return result
    

hrs = list(gwdata['HR_NAME'].unique())
#Analysis all wells
all_wells_individual_analysis = well_percentile(gwdata, subset = ['HR_NAME', hrs])
all_wells_regional_analysis = regional_pctl_analysis(all_wells_individual_analysis, stat='median')

os.makedirs('../../Data/Processed/groundwater/', exist_ok=True)
all_wells_individual_analysis.to_csv('../../Data/Processed/groundwater/state_wells_individual_analysis.csv')
all_wells_regional_analysis.to_csv('../../Data/Processed/groundwater/state_wells_regional_analysis.csv')
