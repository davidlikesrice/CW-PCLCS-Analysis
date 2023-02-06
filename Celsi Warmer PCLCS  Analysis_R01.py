#Import the required Libraries
from tkinter import *
from tkinter import ttk
import tkinter as tk
import os
import csv
import pandas as pd
from tkinter import filedialog
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go

#Create an instance of Tkinter frame
win = Tk()
#Set the geometry of Tkinter frame
win.geometry("750x270")

def AnalyzeLog():
    #variables to change- csv to read and name of the test
    csv = filedialog.askopenfilename()
    print (csv)
    #create folder for test if doesn't already exist
    directory = os.path.dirname(csv)
    print (directory)
    testName = str(testID.get())
    #create folder for test if doesn't already exist
    if os.path.exists(directory + '\\' + testName):
        pass
    else:
        os.mkdir(directory + '\\' + testName)
    #Name columns
    columnNames = ['Boot','Elapsed Time',"Baby Temp","Heater 1",'Heater 2','Est. Mattress','Ambient','Goal','Interlock','Heater Output (%)','Mode']

    #create dataFrame from the CSV
    df = pd.read_csv(csv, names = columnNames, on_bad_lines='warn')
    #drop the rows that don't contain data and delete the first row that contains text headers
    df = df.dropna()
    df= df.iloc[1:,:]
    #convert from object to float64
    i = 0
    for col in df:
        (df[df.columns[i]]) = (df[df.columns[i]]).astype(np.float64)
        i+=1
    #find boot numbers, boots less than 60s are not counted
    bootOnly= df.Boot.unique() 
    i=0
    #display all boots and the boot length
    for unique in bootOnly:
        print('Boot #' + str(bootOnly[i].round(0)) + ' Length of Test: ' + str(((df['Boot'].value_counts()[bootOnly[i]])/60).round(2))+ ' hrs.')
        i+=1
    boot = float(input('Select boot number: '))
    #create dataframe with the selected boot number
    df = df.loc[df['Boot']== boot]

    #delete Mode rows that don't contain values: 2 (baby mode) or 3 (limbo mode)  or 4 (manual mode)
    options = [2,3,4]
    df = df.loc[df['Mode'].isin(options)]

    #delete Baby Temp rows that don't contain realistic values -> If testing invloves intentional modes with alarm, it may be good to keep comment this out
    df = df.loc[df['Baby Temp']> 31.9]

    #create new column: Max Heater
    df['Max Heater'] = df[["Heater 1", "Heater 2"]].values.max(axis = 1)

    #calcuate data for table
    commandVariable = 36.5
    #Calculate Start Temp from the second data point -- minimizes chance of error from the first data point
    startTemp =df['Baby Temp'].iloc[1] 

    #graphs only modes 2 and 3
    graph_options = [2,3]
    df_graph = df.loc[df['Mode'].isin(graph_options)]
    #transform elapsed column from seconds to hours
    df["Elapsed Time"] = (df['Elapsed Time']-df['Elapsed Time'].iloc[0])/3600
    df_graph["Elapsed Time"] = df['Elapsed Time']

    df_ResponseTime = df.loc[df['Baby Temp']>= (0.9*(commandVariable-startTemp))+startTemp] #creates data frame during the final 10% of the data
    if df_ResponseTime.empty == False:
        ResponseTime = df_ResponseTime['Elapsed Time'].iloc[0] #Time when 90% of the command Variable is reached-> calculate (Command-Start)*90%
        ResponseTemp = df_ResponseTime['Baby Temp'].iloc[0]
    else: #the baby did not reach within 90% of the command variable 
        ResponseTime = 0
        ResponseTemp = 0
    #steady state is defined as < 0.1 C change in baby temperature during the course of 60 minutes or less than a 0.068% change in temperature over 15 minutes
    #review
    steadyState= 0.00068 #units are C -> in this code it is not multiplying by 100 therefore 0.068% = 0.00068C
    df['Percent Change'] = (df['Baby Temp'].pct_change(periods=15)) #less than ~0.1C change in 1 hour and this is the last instance of steady state  
    df.loc[df['Percent Change']> steadyState, 'Steady State'] = 1  #creates a steady state column. This could be used in the future to verify this is the last steady state time that was reached
    df_steadyState = df.loc[(df['Percent Change'] < steadyState)]

    #identify the row number where all remaining data is steady state - this removes any early data that might also be changing slow enough that it is considered steady state
    df['cumSum'] = df['Steady State'].cumsum()
    df_steadyState= df.iloc[df['cumSum'].idxmax():len(df['cumSum'])]
    df_steadyState = df.loc[(abs(df['Percent Change'] )< steadyState)]
    #determine the steady state baby temp
    steadyStateValue = df_steadyState['Baby Temp'].mean()

    #Calculate the relative overshoot amount above 95% of the command variable
    relativeOvershoot = df['Baby Temp'].max() - (0.95*commandVariable)
    commandOvershoot = df['Baby Temp'].max() - commandVariable

    #calculate the steady state deviation
    upDev =df_steadyState['Baby Temp'].max() - commandVariable
    loDev =df_steadyState['Baby Temp'].min() - commandVariable
    if abs(upDev) > abs(loDev):
        dev = upDev
    else:
        dev =loDev

    #calculate the warming rate:
    if df_ResponseTime.empty == False:
        warmingRate = (ResponseTemp-startTemp)/ResponseTime #time rate until 90% of command variable is reached
    else: 
        warmingRate = 0

    #generate  full graph
    fig, ax = plt.subplots()
    ax.scatter(df_graph['Elapsed Time'], df_graph['Baby Temp'], color = 'blue', linewidths=0.5, label = 'physiological variable')
    ax.plot(df_graph['Elapsed Time'], df_graph['Goal'], color = 'black',label = 'command variable')
    ax.plot(df_graph['Elapsed Time'], df_graph['Max Heater'], color = 'grey', label = 'Heater')
    ax.plot(df_steadyState['Elapsed Time'], df_steadyState['Baby Temp'], color = 'red', label = 'steady state')
    ax.plot(df_graph['Elapsed Time'], df_graph['Est. Mattress'], color = 'yellow', label ='Estimated Mattress Temp')
    ax.plot(df_graph['Elapsed Time'], df_graph['Ambient'], color = 'lightblue', label = 'Ambient Temp' )
    plt.ylim(18,42), plt.legend(bbox_to_anchor = (1.05, 1.15), ncol = 2), plt.title(testName), plt.xlabel('Time (hours)'), plt.ylabel('Temperature (°C)')
    #add second axis for the power
    plt.grid(True)
    ax2 = ax.twinx()
    ax2.plot(df_graph['Elapsed Time'], df_graph['Heater Output (%)'], color = 'green', label = 'Power')
    ax2.set_ylabel('Power (watts)', color = 'green')
    ax2.set_ylim(0,100)
    ax2.legend(bbox_to_anchor =(0.9, 1.05), ncol =1)
    f = plt.gcf()
    f.set_size_inches(24,12)

    plt.draw()

    #save graphs
    plt.savefig(directory + '\\' + testName +'\\'+ testName + '_Full_Graph.png')

    #generate plot for the PCLCS Report
    fig, ax = plt.subplots()
    ax.scatter(df_graph['Elapsed Time'], df_graph['Baby Temp'], color = 'blue', linewidths=0.5, label = 'physiological variable')
    ax.plot(df_graph['Elapsed Time'], df_graph['Goal'], color = 'black',label = 'command variable')
    plt.ylim(31,39), plt.legend(loc = 'lower right'), plt.title(testName), plt.xlabel('Time (hours)'), plt.ylabel('Temperature (°C)')
    f = plt.gcf()
    plt.grid(True)
    f.set_size_inches(24,12)
    plt.draw()
    plt.savefig(directory + '\\' + testName +'\\'+ testName + '_Graph.png')

    #Create dataframe of results
    results = {'Parameter':['Command Variable','Response Time', 'Settling Time', 'Physiologic Variable', 'Initial Value of Physiologic Variable','Average Steady State Value of Physiologic Variable', 'Relative Overshoot', 'Command Overshoot', 'Steady State Deviation', 'Warming Rate'],
                'Value': [round(commandVariable,1),round(ResponseTime, 2), 'N/A', 'Baby Temp', round(startTemp, 1), round(steadyStateValue,1), round(relativeOvershoot,1), round(commandOvershoot,1), round(dev,1), round(warmingRate,1)],
                'Units': ['°C','hrs.','N/A','°C','°C','°C','°C','°C','°C','°C/hr.']}
    df_results = pd.DataFrame(results) # create a data frame of the results:

    #create table of the results results
    headerColor = 'lightblue'
    rowEvenColor = 'lightgrey'
    rowOddColor = 'white'
    lineColor = 'darkslategray'

    fig = go.Figure(data=[go.Table(
        columnorder = [1,2,3],
        columnwidth = [275,75,50],
        header=dict(values=list(df_results.columns),
                    line_color =lineColor,
                    fill_color=headerColor,
                    align=['left','center']),
        cells=dict(values=[df_results.Parameter, df_results.Value, df_results.Units],
                    line_color = lineColor,
                fill_color=[[rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,]*10],
                align=['left','center']))                    
    ])
    fig.update_layout(width = 700, height = 800)
    #save the table
    fig.write_image(directory + '\\' + testName +'\\'+ testName + '_Table.png')

    #Export data frame to excel sheet with 3 tabs: total, steady state, summary
    with pd.ExcelWriter(directory + '\\' + testName +'\\'+ testName + 'Compiled.xlsx') as writer:
        # use to_excel function and specify the sheet_name and index
        # to store the dataframe in specified sheet
        df_results.to_excel(writer, sheet_name="Summary of Results", index=False)
        df.to_excel(writer, sheet_name="Data", index=False)
        df_steadyState .to_excel(writer, sheet_name="Steady State", index=False)
    open_popup()

def AnalyzeStream():
    #variables to change- csv to read and name of the test
    csv = filedialog.askopenfilename()
    #create folder for test if doesn't already exist
    directory = os.path.dirname(csv)
    print (directory)
    testName = str(testID.get())
    if os.path.exists(directory + '\\'+ testName):
        pass
    else:
        os.mkdir(directory + '\\'+ testName)
    #Name columns
    columnNames= ['Time Stamp','Sample Count', 'Baby Temp', 'Heater 1', 'Heater 2', 'Est. Mattress', 'Ambient', 'Goal', 'P','I','D','Heat Flag', 'PID', 'Mode', 'Actual 1','Actual 2']  
    #define saving location

    #create dataFrame from the CSV
    df = pd.read_csv(csv, names = columnNames, on_bad_lines='warn')

    #split timestamp with mulitple delimiters: [, space , colon:, decimal. , bracket ]
    #append columns for log output, hour, minute, & second
    TimeStampSplit = df['Time Stamp'].str.split('[| |:|.|]',expand=True)
    df['logOutput'] = TimeStampSplit[5]
    df['Hour'] = TimeStampSplit[1].astype(np.float64)
    df['Minute'] = TimeStampSplit[2].astype(np.float64)
    df['Second'] = TimeStampSplit[3].astype(np.float64)
    startTime_df= df['Hour'].iloc[0] +df['Minute'].iloc[0]/60 + df['Second'].iloc[0]/3600
    df['Absolute Elapsed Time']= (df['Hour'] +df['Minute']/60 + df['Second']/3600) - startTime_df
    df_allData = df
    #delete log output rows that contain any value except for CTL
    df = df.loc[df['logOutput'].isin(['CTL'])]

    #ensure all columns except TimeStamp are data type: float64 (usually it imports correctly, but occasionaly imports as an object)

    #delete Mode rows that don't contain values: 2 (baby mode) or 3 (limbo mode)  or 4 (manual mode)
    options = [2,3,4,5]
    df = df.loc[df['Mode'].isin(options)]

    i = 0
    for col in df:
        if i != df.columns.get_loc('Time Stamp') and i !=df.columns.get_loc('logOutput'): #skip column 0 (Timestamp) and coloumn 16(log output) becasue they are strings
            (df[df.columns[i]]) = (df[df.columns[i]]).astype(np.float64)
        i+=1
    #print(df.dtypes)


    #delete Baby Temp rows that don't contain realistic values -> If testing invloves intentional modes with alarm, it may be good to keep comment this out
    #df = df.loc[df['Baby Temp']> 31.9]
    df = df.loc[abs(df['Baby Temp'].pct_change(1))<0.03]
    # create new columns: Elapsed Time

    startTime= df['Hour'].iloc[0] +df['Minute'].iloc[0]/60 + df['Second'].iloc[0]/3600
    df['Elapsed Time']= (df['Hour'] +df['Minute']/60 + df['Second']/3600) - startTime
    df_allData['Elapsed Time'] = df['Elapsed Time']
    #deletes first 15 seconds that may have outliers
    df= df.loc[df['Elapsed Time']>=(0.0000001)]

    #create new column: Max Heater
    df['Max Heater'] = df[["Heater 1", "Heater 2"]].values.max(axis = 1)

    #create new column: Average Power
    df['Power: 5 min rolling'] = df['PID'].rolling(300).mean()

    #calcuate data for table
    commandVariable = 36.5
    #Calculate Start Temp
    startTemp =np.average((df.loc[(df['Elapsed Time']<(1/60)) & (df['Baby Temp']>32)])['Baby Temp']) #takes average during first 1 minute data AND where Baby Temp is greater than 32C (to avoid outliers)

    #Determine response time and temperature
    df_ResponseTime = df.loc[df['Baby Temp']>= (0.9*(commandVariable-startTemp))+startTemp] #creates data frame during the final 10% of the data
    if df_ResponseTime.empty == False:
        ResponseTime = df_ResponseTime['Elapsed Time'].iloc[0] #Time when 90% of the command Variable is reached-> calculate (Command-Start)*90%
        ResponseTemp = df_ResponseTime['Baby Temp'].iloc[0]
    else: #the baby did not reach within 90% of the command variable 
        ResponseTime = 0
        ResponseTemp = 0
    #steady state is defined as < 0.1 C change in baby temperature during the course of 60 minutes or less than a 0.068% change in temperature over 15 minutes
    steadyState= 0.00068 #units are C
    df['Percent Change'] = (df['Baby Temp'].pct_change(periods=900)) #less than ~0.1C change in 1 hour and this is the last instance of steady state  
    df.loc[abs(df['Percent Change'])> steadyState, 'Steady State'] = 1  #creates a steady state column. This could be used in the future to verify this is the last steady state time that was reached
    #identify the row number where all remaining data is steady state - this removes any early data that might also be changing slow enough that it is considered steady state
    df['cumSum'] = df['Steady State'].cumsum()
    df_steadyState= df.iloc[df['cumSum'].idxmax():len(df['Baby Temp'])]
    
    print(df['cumSum'].idxmax())
    print(len(df['cumSum']))

    #determine the steady state baby temp
    steadyStateValue = df_steadyState['Baby Temp'].mean()

    #Calculate the relative overshoot amount above 95% of the command variable
    relativeOvershoot = df['Baby Temp'].max() - (0.95*commandVariable)
    commandOvershoot = df['Baby Temp'].max() - commandVariable

    #calculate the steady state deviation
    upDev =df_steadyState['Baby Temp'].max() - commandVariable
    loDev =df_steadyState['Baby Temp'].min() - commandVariable
    if abs(upDev) > abs(loDev):
        dev = upDev
    else:
        dev =loDev

    #calculate the warming rate:
    if df_ResponseTime.empty == False:
        warmingRate = (ResponseTemp-startTemp)/ResponseTime #time rate until 90% of command variable is reached
    else: 
        warmingRate = 0

    #graphs only modes 2 and 3
    graph_options = [2,3,4,5]
    df_graph = df.loc[df['Mode'].isin(graph_options)]

    #generate  full graph
    fig, ax = plt.subplots()
    ax.scatter(df_graph['Elapsed Time'], df_graph['Baby Temp'], color = 'blue', linewidths=0.5, label = 'physiological variable')
    ax.scatter(df_graph['Elapsed Time'], df_graph['Goal'], color = 'black',label = 'command variable', s = 5)
    ax.scatter(df_graph['Elapsed Time'], df_graph['Max Heater'], color = 'grey', label = 'Heater')
    ax.scatter(df_steadyState['Elapsed Time'], df_steadyState['Baby Temp'], color = 'red', label = 'steady state')
    ax.scatter(df_graph['Elapsed Time'], df_graph['Est. Mattress'], color = 'yellow', label ='Estimated Mattress Temp')
    ax.scatter(df_graph['Elapsed Time'], df_graph['Ambient'], color = 'lightblue', label = 'Ambient Temp' )
    plt.ylim(8,42), plt.legend(bbox_to_anchor = (1.05, 1.15), ncol = 2), plt.title(testName, fontsize = 20), plt.xlabel('Time (hours)', fontsize = 20), plt.ylabel('Temperature (°C)',fontsize =20)
    ax.tick_params(labelsize = 25)
    ax.tick_params(axis = 'both', which = 'major', labelsize =20)
    #add second axis for the power
    plt.grid(True)
    ax2 = ax.twinx()
    ax2.scatter(df_graph['Elapsed Time'], df_graph['Power: 5 min rolling'], color = 'green', label = 'Power', s =5)
    ax2.set_ylabel('Power (watts)', color = 'black', fontsize = 20)
    ax2.set_ylim(0,100)
    ax2.tick_params(labelsize=25)
    ax2.legend(bbox_to_anchor =(0.9, 1.05), ncol =1)
    f = plt.gcf()
    f.set_size_inches(24,12)
    plt.draw()

    #save graphs
    plt.savefig(directory +'\\' + testName +'\\'+ testName + '_Full_Graph.png')

    #generate plot for the PCLCS Report
    plt.rcParams.update({'font.size': 20})
    fig, ax = plt.subplots()
    ax.scatter(df_graph['Elapsed Time'], df_graph['Baby Temp'], color = 'blue', linewidths=0.5, label = 'physiological variable')
    ax.scatter(df_graph['Elapsed Time'], df_graph['Goal'], color = 'black',label = 'command variable', s = 5)
    ax.tick_params(labelsize=25)
    plt.ylim(31,39), plt.legend(loc = 'lower right'), plt.title(testName), plt.xlabel('Time (hours)'), plt.ylabel('Temperature (°C)')
    f = plt.gcf()
    plt.grid(True)
    f.set_size_inches(20,10)
    plt.draw()


    #save graphs
    plt.savefig(directory +'\\' + testName +'\\'+ testName + '_Graph.png', bbox_inches = 'tight')

    #Create dataframe of results
    results = {'Parameter':['Command Variable','Response Time', 'Settling Time', 'Physiologic Variable', 'Initial Value of Physiologic Variable','Average Steady State Value of Physiologic Variable', 'Relative Overshoot', 'Command Overshoot', 'Steady State Deviation', 'Warming Rate'],
                'Value': [round(commandVariable,1),round(ResponseTime, 2), 'N/A', 'Baby Temp', round(startTemp, 1), round(steadyStateValue,1), round(relativeOvershoot,1), round(commandOvershoot,1), round(dev,1), round(warmingRate,1)],
                'Units': ['°C','hrs.','N/A','°C','°C','°C','°C','°C','°C','°C/hr.']}
    df_results = pd.DataFrame(results) # create a data frame of the results:

    #create table of the results results
    headerColor = 'lightblue'
    rowEvenColor = 'lightgrey'
    rowOddColor = 'white'
    lineColor = 'darkslategray'

    fig = go.Figure(data=[go.Table(
        columnorder = [1,2,3],
        columnwidth = [275,75,50],
        header=dict(values=list(df_results.columns),
                    line_color =lineColor,
                    fill_color=headerColor,
                    align=['left','center']),
        cells=dict(values=[df_results.Parameter, df_results.Value, df_results.Units],
                    line_color = lineColor,
                fill_color=[[rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,rowOddColor,rowEvenColor,]*10],
                align=['left','center']))
                        
    ])
    fig.update_layout(width = 700, height = 800)
    #save the table
    fig.write_image(directory +'\\' + testName +'\\'+ testName + '_Table.png')

    #Export data frame to excel sheet with 3 tabs: total, steady state, summary
    with pd.ExcelWriter(directory +'\\' + testName +'\\'+ testName + 'Compiled.xlsx') as writer:
        # use to_excel function and specify the sheet_name and index
        # to store the dataframe in specified sheet
        df_results.to_excel(writer, sheet_name="Summary of Results", index=False)
        df_allData.to_excel(writer, sheet_name = 'All Data', index = False)
        df.to_excel(writer, sheet_name="Baby Mode", index=False)
        df_steadyState .to_excel(writer, sheet_name="Steady State", index=False)

    #show the graph
    #plt.show()
    open_popup()

def setName():
    testName = testID.get()
    print(testName)

def open_popup():
   top= Toplevel(win)
   top.geometry("750x250")
   top.title("Child Window")
   Label(top, text= "Analysis Complete", font=('Mistral 18 bold')).place(x=150,y= 80)

Label(win, text=" Enter Test Name then click button to select data", font=('Helvetica 14 bold')).pack(pady=20)
testLabel = Label(win, text = 'Type Test Name:', font=("Arial", 12)).pack()
#testLabel.place(x=20, y = 130).pack()

testID=Entry(win, bd = 5, width = 50)
testID.pack()
#testID.place(x=240, y=130).pack()

#ID_Enter = Button(win, text="Okay", command= setName).pack()
#ID_Enter.place(x =550, y = 130)

#Create a button in the main Window to open the popup
ttk.Button(win, text= "Select Stream Data", command= AnalyzeStream).pack()
ttk.Button(win, text = 'Select Log Data', command = AnalyzeLog).pack()

win.mainloop()