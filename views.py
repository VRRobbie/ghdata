from django.shortcuts import render
from django.http import HttpResponse
import requests
import mysql.connector

def index(request):
    
    #Connect to the database and create two cursors.  At one point we will 
    #need to use a second cursor while still using SELECT data from the first.
    cnx = mysql.connector.connect(user='root', password='example_password',
                                  host='127.0.0.1',
                                  database='github')								  
    cursor = cnx.cursor(buffered=True)
    cursor2 = cnx.cursor(buffered=True)
    
    #Get the github api's events.
    response = requests.get('https://api.github.com/events')
    eventData = response.json()
	
    #Create a list with the total for each event for this page load
    #and a SQL query which will be used later to determine UPDATE vs INSERT 
    #when adding the events to the database.
    getMatchingEventsSQL = ("SELECT * FROM githubevents WHERE 1 = 1")	
    eventsWithTotals = []
    needParen = False
    for thisEvent in eventData:
        if thisEvent['type'] in eventsWithTotals:
            eventIndex = eventsWithTotals.index(thisEvent['type'])
            eventsWithTotals[eventIndex - 1] += 1
        else:
            if not eventsWithTotals:
                getMatchingEventsSQL = getMatchingEventsSQL + " AND ("
            else:
                getMatchingEventsSQL = getMatchingEventsSQL + " OR "
            eventsWithTotals = eventsWithTotals + [1, thisEvent['type']]
            getMatchingEventsSQL = (getMatchingEventsSQL + "eventName = '" 
                                    + thisEvent['type'] + "'")
            needParen = True
    if needParen:
        getMatchingEventsSQL = getMatchingEventsSQL + ")"
    
    #If none of the new events match events already in the database, INSERT
    #all of them.  If some of them match, UPDATE the ones that do and add to
    #their total, then INSERT the ones that were not already in the database.
    cursor.execute(getMatchingEventsSQL)
    eventsAlreadyInserted = []
    if not cursor.rowcount:
        if eventsWithTotals:
            for key, value in enumerate(eventsWithTotals):
                if key % 2 == 0:
                    addEventSQL = ("INSERT INTO githubevents "
                                   "EventTotal, EventName) VALUES "
                                   "({},'{}')".format(eventsWithTotals[key], 
                                   eventsWithTotals[key + 1]))	
                    cursor2.execute(addEventSQL)
                    cnx.commit()
    else:
        if eventsWithTotals:
            for(gitHubEvent) in cursor:
                for key, value in enumerate(eventsWithTotals):
                    if key % 2 == 1:
                        if gitHubEvent[1] == value:
                            addEventSQL = ("UPDATE githubevents SET "
                                           "EventTotal = EventTotal + {} "
                                           "WHERE EventName = '{}'"
                                           .format(eventsWithTotals[key-1], 
                                           eventsWithTotals[key]))
                            eventsAlreadyInserted = (eventsAlreadyInserted 
                                                     + [value])
                            cursor2.execute(addEventSQL)
                            cnx.commit()
                            break
            for key, value in enumerate(eventsWithTotals):
                if key % 2 == 1:
                    if value not in eventsAlreadyInserted:
                        addEventSQL = ("INSERT INTO githubevents (EventTotal,"
                                       "EventName) VALUES ({},'{}')"
                                       .format(eventsWithTotals[key - 1], 
                                       eventsWithTotals[key]))
                        cursor2.execute(addEventSQL)
                        cnx.commit()
						
    #Construct the HTML output for event totals in the current page load.
    myHTMLOutput = "<h1>Welcome to the GitHub Events Page!</h1>"
    myHTMLOutput = (myHTMLOutput + "<h3>These are the events from the current "
                    "page load:</h3>")
    myHTMLOutput = (myHTMLOutput + "<table><tr><th>Event Type</th><th>Total "
                    "for this Page Load</th></tr>")
    for key,value in enumerate(eventsWithTotals):
        if key % 2 == 0:
            myHTMLOutput = (myHTMLOutput + "<tr><td>" 
                            + str(eventsWithTotals[key + 1]) 
                            + "</td><td>" 
                            + str(eventsWithTotals[key]) + "</td></tr>")
    myHTMLOutput = myHTMLOutput + "</table>"

    #Construct the HTML output for the event totals of past page loads.
    getEventOutputSQL = ("SELECT * from githubevents")
    cursor2.execute(getEventOutputSQL)	
    myHTMLOutput = (myHTMLOutput + "<h3>These are the events from the database"
                    " (the sum of all page loads):</h3>")
    myHTMLOutput = (myHTMLOutput + "<table><tr><th>Event Type</th><th>Total "
                    "for all Page Loads</th></tr>")	
    for(gitHubEvent) in cursor2:
        myHTMLOutput = (myHTMLOutput + "<tr><td>" + str(gitHubEvent[1]) 
                        + "</td><td>" + str(gitHubEvent[2]) + "</td></tr>")
    myHTMLOutput = myHTMLOutput + "</table>"
	
    #Close the cursors and the database connection.
    cursor2.close()
    cursor.close()
    cnx.close()
    
    #Show the HTML output.
    return HttpResponse(myHTMLOutput)