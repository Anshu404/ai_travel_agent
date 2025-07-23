# travel_agent_backend.py

# Step 1: All necessary imports
# ==================================
import os
import requests


import smtplib
from email.message import EmailMessage
import re

from twilio.twiml.messaging_response import MessagingResponse
from langchain_core.output_parsers import JsonOutputParser
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import MessagesPlaceholder
# The new import
from pydantic import BaseModel, Field
from flask import Flask, request, jsonify
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import tool

from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import AgentExecutor
from flask_cors import CORS
from datetime import datetime
import json

# ==================================
# THE ONLY CHANGE IS HERE
# Add these two lines to fix the error
import google.auth
import google.auth.transport.requests
# ==================================


# Add this line in your config section
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "json file location"

# os.environ["GOOGLE_API_KEY"] = "key here"

# os.environ["OPENWEATHERMAP_API_KEY"] = "key here"

# Step 1: Get today's date dynamically
today_str = datetime.today().strftime("%B %d, %Y")  # e.g., "July 21, 2025"


# os.environ["GMAIL_ADDRESS"] = "mail@gmail.com"
# os.environ["GMAIL_APP_PASSWORD"] = "pass word" # <-- Paste your 16-digit password here without spaces


# os.environ["GOOGLE_CSE_ID"] = "id here "


# The new, single-response structure
class ConversationalResponse(BaseModel):
    response: str = Field(description="A single, friendly, and conversational response to the user.")

# ---
# Step 2: Configuration & API Keys
# ==================================

# --- Step 2: Configuration & API Keys ---
# ... (other keys) ...
# Add your new key if it's different, or you can reuse the one above.
# Add this line in your config section



# ---
# Step 3: Define Your Tools (APIs)
# ==================================
# In-memory store for temporary conversation histories
session_histories = {}


def get_lat_lon(city_name):
    """Helper function to get latitude and longitude for a city."""
    # This uses the Geocoding API, which should be enabled with your key.
    api_key = os.getenv("GOOGLE_API_KEY") # Uses the key from your config
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={city_name}&key={api_key}"
    try:
        response = requests.get(url).json()
        if response['status'] == 'OK':
            location = response['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        print(f"Geocoding failed: {e}")
    return None, None


###################################################################################################


# Add this block after your imports
import sqlite3
import threading

# Use a lock to make database writes from different requests thread-safe
db_lock = threading.Lock()

def init_db():
    with db_lock:
        conn = sqlite3.connect('agent_logs.db', check_same_thread=False)
        cursor = conn.cursor()
        # Create the table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                channel TEXT,
                user_query TEXT,
                tool_used TEXT,
                agent_response TEXT,
                error_message TEXT
            )
        ''')
        conn.commit()
        conn.close()

def log_interaction(session_id, channel, user_query, tool_used, agent_response, error_message=None):
    with db_lock:
        conn = sqlite3.connect('agent_logs.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO interactions (session_id, channel, user_query, tool_used, agent_response, error_message) VALUES (?, ?, ?, ?, ?, ?)',
            (session_id, channel, user_query, str(tool_used), agent_response, error_message)
        )
        conn.commit()
        conn.close()

# Initialize the database when the app starts
init_db()






















#not updated 

# @tool
# def search_flights(departure_code: str, arrival_code: str, outbound_date: str) -> dict:
#     """
#     Performs a flight search using IATA codes and a specific date.
#     The AI model is responsible for converting city names and relative
#     dates into the required 'YYYY-MM-DD' format before calling this tool.

#     Args:
#         departure_code: The 3-letter IATA code for the departure airport (e.g., "GOI").
#         arrival_code: The 3-letter IATA code for the arrival airport (e.g., "DEL").
#         outbound_date: The specific date of the flight in "YYYY-MM-DD" format.
#     """
#     if not SERPAPI_KEY:
#         return {"status": "error", "message": "SERPAPI_KEY is not set."}

#     print(f"--- Calling Google Flights API for {departure_code} to {arrival_code} on {outbound_date} ---")

#     params = {
#         "engine": "Google Flights",
#         "departure_id": departure_code,
#         "arrival_id": arrival_code,
#         "outbound_date": outbound_date,
#         "api_key": SERPAPI_KEY,
#         "currency": "INR",
#         "hl": "en"
#     }

#     try:
#         response = requests.get("https://serpapi.com/search", params=params)
#         response.raise_for_status()
#         results = response.json()

#         # Process the structured flight results
#         processed_flights = []
#         flight_list = results.get('best_flights', []) + results.get('other_flights', [])

#         if not flight_list:
#             return {"status": "success", "flights": [], "summary": "No direct flights found for this route on the specified date."}

#         for flight in flight_list:
#             first_leg = flight.get('flights', [{}])[0]
#             processed_flights.append({
#                 "price": f"{flight.get('price')} {params['currency']}",
#                 "airline": first_leg.get('airline', 'N/A'),
#                 "duration": f"{flight.get('total_duration') // 60}h {flight.get('total_duration') % 60}m",
#                 "stops": len(flight.get('layovers', [])),
#                 "flight_number": first_leg.get('flight_number', 'N/A')
#             })

#         return {
#             "status": "success",
#             "flights": processed_flights[:5] # Return top 5 results
#         }

#     except requests.exceptions.RequestException as e:
#         print(f"Error calling SerpApi Google Flights engine: {e}")
#         return {"status": "error", "message": "Failed to retrieve flight information."}




@tool
def Google_Hotels(city: str) -> str:
    """
    Searches for top-rated hotels in a given city using the Google Places API.
    This tool finds places and provides ratings, but does not handle booking,
    pricing, or availability for specific dates. It returns a summarized list.
    """
    print(f"--- Calling Google Places API to find hotels in {city} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Google API key is not configured."

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = f"top rated hotels in {city}"
    params = {
        'query': query,
        'key': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK' and 'results' in data and len(data['results']) > 0:
            # Get the top 3 results for a concise answer
            top_results = data['results'][:3]
            
            summary_lines = [f"I found some highly-rated hotels in {city}:"]
            for place in top_results:
                name = place.get('name', 'N/A')
                rating = place.get('rating', 'No rating')
                # Include the number of reviews for more context
                num_ratings = place.get('user_ratings_total', 0)
                
                summary_lines.append(
                    f"- {name} has a great rating of {rating} out of 5 from over {num_ratings} reviews."
                )
            
            summary_lines.append("For prices and availability for your specific dates, I recommend checking a booking website like Booking.com or Agoda.")
            return " ".join(summary_lines)
        else:
            return f"I'm sorry, I could not find any well-rated hotels in {city} at the moment."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Places API: {e}")
        return "I'm sorry, I encountered an error while searching for hotels."



@tool
def find_restaurants_for_occasion(city: str, occasion_description: str) -> str:
    """
    Finds restaurants in a city based on a specific occasion, mood, or company.
    For example, 'a romantic dinner for two', 'a casual lunch with friends',
    or 'a family-friendly restaurant with outdoor seating'.
    """
    print(f"--- Calling Google Places API for: '{occasion_description}' in {city} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Google API key is not configured."

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    # The query is now dynamic based on the user's description
    query = f"{occasion_description} in {city}"
    params = {'query': query, 'key': api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            top_results = data['results'][:3]
            
            summary_lines = [f"Based on your request for '{occasion_description}', here are a few great options I found in {city}:"]
            for place in top_results:
                name = place.get('name', 'N/A')
                rating = place.get('rating', 'No rating')
                num_ratings = place.get('user_ratings_total', 0)
                summary_lines.append(
                    f"- {name}, which has a solid rating of {rating} from over {num_ratings} reviews."
                )
            
            summary_lines.append("You might want to check their website or call ahead for reservations and specific details.")
            return " ".join(summary_lines)
        else:
            return f"I'm sorry, I couldn't find specific restaurants matching '{occasion_description}' in {city} right now."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Places API: {e}")
        return "I'm sorry, I encountered an error while searching for restaurants."
    


@tool
def find_places_to_visit(city: str, interest_and_time: str) -> str:
    """
    Finds places to visit, like tourist attractions, museums, or parks,
    based on a user's interest and time constraints. For example,
    'museums I can visit for 2 hours' or 'parks to see in the morning'.
    """
    print(f"--- Calling Google Places API for: '{interest_and_time}' in {city} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Google API key is not configured."

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    # The query combines the interest and the city for a natural search
    query = f"{interest_and_time} in {city}"
    params = {'query': query, 'key': api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            top_results = data['results'][:3]
            
            summary_lines = [f"Considering you're interested in '{interest_and_time}', here are some popular spots in {city}:"]
            for place in top_results:
                name = place.get('name', 'N/A')
                address = place.get('formatted_address', 'Address not available')
                summary_lines.append(
                    f"- {name}, located at {address}."
                )
            
            summary_lines.append("I'd recommend checking their official website for opening hours and ticket information.")
            return " ".join(summary_lines)
        else:
            return f"I couldn't find any specific places matching your request for '{interest_and_time}' in {city}."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Places API: {e}")
        return "I'm sorry, I encountered an error while searching for places to visit."



@tool
def get_weather_forecast(city: str, num_days: int = 1) -> str:
    """
    Gets the weather forecast for a city.
    For up to 5 days, it provides a real forecast using an API.
    For requests longer than 5 days, it provides a general, seasonal outlook without calling an API.
    """
    print(f"--- Weather tool called for {city} for {num_days} days ---")

    # The new hybrid logic starts here
    if num_days <= 5:
        # --- API-BASED FORECAST FOR 5 DAYS OR LESS ---
        print(f"--- Calling OpenWeatherMap for {num_days}-day forecast ---")
        lat, lon = get_lat_lon(city)
        if not lat or not lon:
            return f"I'm sorry, I couldn't find the location for {city}."

        try:
            api_key = os.getenv("OPENWEATHERMAP_API_KEY")
            # This is the correct URL for the standard free plan's 5-day forecast
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Process the response to create a simplified daily forecast
            daily_forecasts = {}
            for forecast in data.get('list', []):
                date = datetime.fromtimestamp(forecast['dt']).strftime('%Y-%m-%d')
                if date not in daily_forecasts:
                    daily_forecasts[date] = { "temps": [], "conditions": [] }
                daily_forecasts[date]['temps'].append(forecast['main']['temp'])
                daily_forecasts[date]['conditions'].append(forecast['weather'][0]['description'])

            # Summarize the data into a readable string
            summary_lines = [f"Here is the weather forecast for {city}:"]
            for date, values in list(daily_forecasts.items())[:num_days]:
                high_temp = max(values['temps'])
                low_temp = min(values['temps'])
                condition = max(set(values['conditions']), key=values['conditions'].count)
                # Format the date to be more friendly, e.g., "Tuesday, Jul 22"
                friendly_date = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %b %d')
                summary_lines.append(f"On {friendly_date}: Expect {condition}, with a high of {high_temp:.0f}°C and a low of {low_temp:.0f}°C.")
            
            return " ".join(summary_lines)

        except Exception as e:
            print(f"Error calling OpenWeatherMap API: {e}")
            return "I'm sorry, I encountered an error while trying to get the weather forecast."
            
    else:
        # --- GENERALIZED RESPONSE FOR MORE THAN 5 DAYS ---
        print("--- Request is > 5 days. Providing a general outlook. ---")
        # Since the current time is late July in Jharkhand, we can assume monsoon season.
        return (f"For a forecast more than 5 days out in {city}, I can provide a general outlook. "
                f"Being July, it is peak monsoon season in the region. You can typically expect hot and humid conditions "
                f"with a high chance of afternoon thunderstorms or heavy rain. For a precise forecast, it's best to check again closer to the date.")


@tool
def get_directions(origin: str, destination: str, travel_mode: str = "driving") -> str:
    """
    Calculates the travel time, distance, and a summary of step-by-step directions
    between an origin and a destination.
    Args:
        origin: The starting point (e.g., "Delhi Airport", "Eiffel Tower").
        destination: The end point (e.g., "ibis New Delhi Aerocity", "Louvre Museum").
        travel_mode: The method of travel. Can be 'driving', 'walking', 'bicycling', or 'transit'. Defaults to 'driving'.
    """
    print(f"--- Calling Google Directions API for {origin} to {destination} via {travel_mode} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Google API key is not configured."

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        'origin': origin,
        'destination': destination,
        'mode': travel_mode,
        'key': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK' and data.get('routes'):
            # Get the first and most optimal route
            route = data['routes'][0]
            leg = route['legs'][0]

            distance = leg['distance']['text']
            duration = leg['duration']['text']
            
            summary_lines = [f"Getting from {origin} to {destination} by {travel_mode} will take about {duration} and cover a distance of {distance}."]
            
            # Add a few key steps from the directions for context
            summary_lines.append("Here are the main steps:")
            for i, step in enumerate(leg.get('steps', [])[:3]): # Get first 3 steps
                # The step instructions are in HTML, so we need to clean them
                import re
                clean_step = re.sub(r'<.*?>', '', step['html_instructions'])
                summary_lines.append(f"{i+1}. {clean_step} ({step['distance']['text']})")

            return " ".join(summary_lines)
        else:
            return f"I'm sorry, I could not find a {travel_mode} route from {origin} to {destination}."

    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Directions API: {e}")
        return "I'm sorry, I encountered an error while trying to get directions."


@tool
def compare_travel_times(origin: str, destinations: list[str]) -> str:
    """
    Calculates and compares the travel time from a single origin to multiple destinations.
    Useful for answering questions like "Which is closer, A or B?".
    Args:
        origin: The single starting point.
        destinations: A list of potential destination names.
    """
    print(f"--- Calling Google Distance Matrix API for {origin} to {destinations} ---")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: Google API key is not configured."
        
    # The API expects destinations to be separated by a pipe character '|'
    destinations_str = "|".join(destinations)

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        'origins': origin,
        'destinations': destinations_str,
        'key': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK':
            summary_lines = [f"Here is the travel time comparison from {origin}:"]
            
            # The API returns a list of results in the same order as the destinations
            for i, element in enumerate(data['rows'][0]['elements']):
                destination_name = data['destination_addresses'][i]
                if element['status'] == 'OK':
                    duration = element['duration']['text']
                    summary_lines.append(f"- To {destination_name}: It's about a {duration} drive.")
                else:
                    summary_lines.append(f"- To {destination_name}: I couldn't calculate the travel time.")
            
            return " ".join(summary_lines)
        else:
            return f"I'm sorry, I couldn't calculate the travel times. The API returned: {data.get('status')}"

    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Distance Matrix API: {e}")
        return "I'm sorry, I encountered an error while comparing travel times."


@tool
def official_Google_Search(query: str) -> str:
    """
    Performs a Google search using the official Google Custom Search API.
    Use this to find real-time information, current events, or any topic
    the agent does not have knowledge about.
    """
    print(f"--- Calling Official Google Custom Search API for query: {query} ---")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return "Error: Google API Key or Custom Search Engine ID is not configured."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()

        if "items" in results:
            summary = "Here are the top search results:\n"
            for item in results["items"][:3]: # Get top 3
                title = item.get("title", "No Title")
                snippet = item.get("snippet", "No Snippet")
                summary += f"- Title: {title}\n  Snippet: {snippet}\n"
            return summary
        else:
            return "Sorry, I could not find any relevant information for that search."

    except Exception as e:
        print(f"Error calling Google Custom Search API: {e}")
        return "I'm sorry, I encountered an error while trying to search."






# @tool
# def search_flights(origin: str, destination: str, date: str) -> str:
#     """
#     Searches for flight information using Google Search to get real-time results.
#     This is the primary tool for all flight-related queries.
#     It constructs a detailed query and returns the most relevant search snippets.
#     """
#     # Construct a detailed query for Google Search
#     query = f"flights from {origin} to {destination} on {date} prices and availability"
    
#     print(f"--- Calling Google Custom Search API for flight query: {query} ---")
    
#     api_key = os.getenv("GOOGLE_API_KEY")
#     cse_id = os.getenv("GOOGLE_CSE_ID")
    
#     if not api_key or not cse_id:
#         return "Error: Google API Key or Custom Search Engine ID is not configured."

#     url = "https://www.googleapis.com/customsearch/v1"
#     params = {
#         'key': api_key,
#         'cx': cse_id,
#         'q': query
#     }

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         results = response.json()

#         if "items" in results and len(results["items"]) > 0:
#             summary = f"Here are the top Google search results for flights from {origin} to {destination}:\n"
#             for item in results["items"][:3]: # Get top 3 results
#                 title = item.get("title", "No Title")
#                 snippet = item.get("snippet", "No Snippet").replace('\n', ' ')
#                 summary += f"- Title: {title}\n  Snippet: {snippet}\n"
            
#             summary += "\nBased on these results, I recommend checking the official airline or a major booking website for the most accurate prices and to book your ticket."
#             return summary
#         else:
#             return "Sorry, my Google search did not return any direct flight information for that query. You may want to try a broader search."

#     except Exception as e:
#         print(f"Error calling Google Custom Search API for flights: {e}")
#         return "I'm sorry, I encountered an error while searching for flight information."

@tool
def search_flights(origin: str, destination: str, date: str, airline: str = None) -> str:
    """
    Searches for flight information using Google Search. Can be filtered by a specific airline if provided.
    This is the primary tool for all flight-related queries.
    It constructs a detailed query and returns the most relevant search snippets.
    Args:
        origin: The starting city or airport code.
        destination: The destination city or airport code.
        date: The specific date for the flight.
        airline: (Optional) The specific airline to search for.
    """
    # If an airline is mentioned, add it to the query to get more specific results
    if airline:
        query = f"{airline} flights from {origin} to {destination} on {date} prices and availability"
    else:
        query = f"flights from {origin} to {destination} on {date} prices and availability"
    
    print(f"--- Calling Google Custom Search API for flight query: {query} ---")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return "Error: Google API Key or Custom Search Engine ID is not configured."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cse_id, 'q': query}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()

        if "items" in results and len(results["items"]) > 0:
            summary = f"Here are the top Google search results for your query:\n"
            for item in results["items"][:3]:
                title = item.get("title", "No Title")
                snippet = item.get("snippet", "No Snippet").replace('\n', ' ')
                summary += f"- Title: {title}\n  Snippet: {snippet}\n"
            
            summary += "\nBased on these results, I recommend checking the official airline or a major booking website for the most accurate prices."
            return summary
        else:
            return "Sorry, my Google search did not return any specific flight information for that query."

    except Exception as e:
        print(f"Error calling Google Custom Search API for flights: {e}")
        return "I'm sorry, I encountered an error while searching for flight information."


# @tool
# def search_flights(origin: str, destination: str, date: str, airline: str = None) -> str:
#     """
#     Searches for flight information using Google Search. Can be filtered by a specific airline if provided.
#     This is the primary tool for all flight-related queries.
#     It constructs a detailed query and returns the most relevant search snippets.
#     """
#     query = f"{airline + ' ' if airline else ''}flights from {origin} to {destination} on {date}"
#     print(f"--- Calling Google Custom Search API for flight query: {query} ---")
    
#     api_key = os.getenv("GOOGLE_API_KEY")
#     cse_id = os.getenv("GOOGLE_CSE_ID")
#     if not api_key or not cse_id:
#         return "Error: Google API Key or Custom Search Engine ID is not configured."

#     url = "https://www.googleapis.com/customsearch/v1"
#     params = {'key': api_key, 'cx': cse_id, 'q': query}

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         results = response.json()

#         if "items" in results and len(results["items"]) > 0:
#             snippets = [item.get("snippet", "").lower() for item in results["items"]]
            
#             # --- NEW QUALITY CHECK ---
#             # Check if the search results are actually about flights.
#             flight_keywords = ['flight', 'airline', 'ticket', 'fare', 'inr', 'usd', '₹', '$']
#             relevant_snippets = [s for s in snippets if any(key in s for key in flight_keywords)]
            
#             if not relevant_snippets:
#                 print("--- Search results found, but they are not relevant to flights. Rejecting. ---")
#                 return "No relevant flight information was found in the search results."
#             # --- END OF QUALITY CHECK ---

#             summary = f"Here are the top Google search results for your query:\n"
#             for item in results["items"][:3]:
#                 title = item.get("title", "No Title")
#                 snippet = item.get("snippet", "No Snippet").replace('\n', ' ')
#                 summary += f"- Title: {title}\n  Snippet: {snippet}\n"
            
#             summary += "\nBased on these results, I recommend checking the official airline or a major booking website for the most accurate prices."
#             return summary
#         else:
#             return "No flight information was found in the search results."

#     except Exception as e:
#         print(f"Error calling Google Custom Search API for flights: {e}")
#         return "I'm sorry, I encountered an error while searching for flight information."






@tool
def search_trains(origin_station_code: str, destination_station_code: str, date: str) -> str:
    """
    Searches for Indian railway information using Google Search.
    The agent should know or find the station codes (e.g., Ranchi is RNC, Delhi is NDLS).
    Date should be in 'YYYY-MM-DD' format.
    """
    # Construct a specific query for Google Search
    query = f"Indian Railways trains from {origin_station_code} to {destination_station_code} on {date}"
    
    print(f"--- Calling Google Custom Search API for train query: {query} ---")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return "Error: Google API Key or Custom Search Engine ID is not configured."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()

        if "items" in results and len(results["items"]) > 0:
            summary = f"Here are the top Google search results for trains from {origin_station_code} to {destination_station_code}:\n"
            for item in results["items"][:3]: # Get top 3 results
                title = item.get("title", "No Title")
                snippet = item.get("snippet", "No Snippet").replace('\n', ' ')
                summary += f"- Title: {title}\n  Snippet: {snippet}\n"
            
            # summary += "\nBased on these results, I recommend checking the official IRCTC website for the most accurate timings and availability."
            return summary
        else:
            return "Sorry, my Google search did not return any specific train information for that query."

    except Exception as e:
        print(f"Error calling Google Custom Search API for trains: {e}")
        return "I'm sorry, I encountered an error while searching for train information."









@tool
def send_plan_by_email(recipient_email: str, trip_summary: str) -> str:
    """
    Sends a travel plan summary to a specified email address.
    The agent should first create a detailed summary of the entire conversation,
    including flights, hotels, and activities, and then pass that summary to this tool.
    """
    print(f"--- Email Tool Called: Sending plan to {recipient_email} ---")

    # Get credentials from environment variables
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        return "Error: Gmail credentials are not configured. Cannot send email."

    # Create the email message
    msg = EmailMessage()
    msg.set_content(trip_summary)
    msg['Subject'] = f"Your Travel Plan Summary"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        # Connect to Gmail's SMTP server and send the email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print("--- Email sent successfully! ---")
        return f"The travel plan has been successfully sent to {recipient_email}."

    except Exception as e:
        print(f"Error sending email: {e}")
        return "Sorry, I encountered an error and could not send the email."






# Change it to this
tools = [ Google_Hotels, get_weather_forecast, find_places_to_visit , find_restaurants_for_occasion , get_directions , compare_travel_times , send_plan_by_email , official_Google_Search , search_flights , search_trains]



# ---
# Step 4: Langchain & Gemini Setup
# ==================================
os.environ["GROQ_API_KEY"] = "key here"
llm = ChatGroq(model="llama3-8b-8192", temperature=0)
llm_with_tools = llm.bind_tools(tools)



# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             f"""You are Anshu's Travel Agent, an expert AI assistant.

#             Your Core Mission:
#             Your goal is to provide accurate, helpful, and very concise answers. Keep your responses short and conversational, like you're talking to a friend. Always use Indian Currency (₹) for prices. Assume today's date is {today_str}.

#             How You Should Behave:
#             - Be an Intelligent Summarizer: When a tool gives you information, your main job is to summarize it. Read the search results and pick out the single most important fact (like the price or the airline).
#             - Be natural and short answer: until asked for just give the answer not any addup.
#             - Be Confident, But Honest: If you find strong evidence, like a recent price, state it confidently (e.g., "I found a flight on Expedia starting at ₹5,700."). Always end by recommending the user check the official website for the final booking.
#             - Do Not Hallucinate: Never invent information. If your tools cannot find an answer, simply say that and suggest an alternative.
#             - DO NOT ADD EXTRA WARNINGS (NEW RULE): Do not add repetitive disclaimers like "Please note that prices may vary..." or "I recommend checking the official website...". State the fact you found, and that's it. Only recommend checking the website if you could not find the information at all.
#             - Plan Smart: For complex trips, use your tools in a logical order. First find the main transport (like a train), then find the local directions from the station to the final destination.
#             """
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("user", "{input}"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )



prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""You are Anshu's Travel Agent, an expert AI assistant.

            **Your Core Mission:**
            Your goal is to provide accurate, helpful, and very concise answers. Keep your responses short and conversational, like you're talking to a friend. Always use Indian Currency (₹) for prices. Assume today's date is {today_str}.

            **How You Should Behave:**
            - **Keep all answers to one or two sentences maximum.**
#           - **Do not explain your steps unless the user asks for details.**
            - **Be an Intelligent Summarizer:** When a tool gives you information, your main job is to summarize it. Read the search results and pick out the single most important fact (like the price or the airline).
            - **Be natural and short answer:** until asked for just give the answer not any addup.
            - **Be Confident, But Honest:** If you find strong evidence, like a recent price, state it confidently (e.g., "I found a flight on Expedia starting at ₹5,700."). Always end by recommending the user check the official website for the final booking.
            - **Do Not Hallucinate:** Never invent information. If your tools cannot find an answer, simply say that and suggest an alternative.
            - **DO NOT ADD EXTRA WARNINGS (NEW RULE):** Do not add repetitive disclaimers like "Please note that prices may vary..." or "I recommend checking the official website...". State the fact you found, and that's it. Only recommend checking the website if you could not find the information at all.
            - **Plan Smart:** For complex trips, use your tools in a logical order. First find the main transport (like a train), then find the local directions from the station to the final destination.

            **CRITICAL RULE:** Your final response to the user MUST be a plain, conversational sentence. NEVER include any internal formatting like '<tool-use>' or '```json' in your final answer.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)
# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             f"""You are an expert travel agent. Your name is Anshu's travel agent.

#             **Your Core Mission:**
#             Your goal is to be an accurate, helpful, and concise assistant. Keep your responses short, conversational, and directly answer the user's question. Assume today's date is {today_str}.

#             **Your Most Important Rules:**

#             1.  **ALWAYS USE YOUR TOOLS:** You **MUST** use your tools for any questions about flights, trains, hotels, weather, directions, or real-time information. Do **NOT** answer these from your own memory.

#             2.  **BE AN INTELLIGENT SUMMARIZER:** When you get results from a tool, do not just dump all the data. Your primary job is to be an intelligent summarizer.
#                 - Read the search snippets and tool outputs carefully.
#                 - Pick the most important details (like the cheapest price, the main weather condition, or the top-rated hotel).
#                 - For example, if a snippet mentions a price like 'Fares @ ₹5700', you should report that specific price.
#                 - Present the key information clearly and concisely.

#             3.  **DO NOT INVENT (NO HALLUCINATING):** Do **NOT** make up information. If a tool fails or if the search results do not contain a clear answer, you must state that you could not find the specific information and recommend the user check official websites.

#             4.  **PLAN MULTI-STEP JOURNEYS:** For complex trips (like from one city to another far away), you must use your tools in a logical sequence.
#                 - First, try to find a major transport link (like a flight or train) to the nearest major city/hub.
#                 - Second, use the directions tool to find the route from that hub to the final destination.
#                 - Combine these real results into a complete travel plan.
#             """
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("user", "{input}"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )


# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             f"""You are a travel agent who gives very short, direct answers.

#             **Your Core Mission:**
#             - Your goal is to answer the user's immediate question with the single most important fact.
#             - Keep all answers to one or two sentences maximum.
#             - Do not explain your steps unless the user asks for details.
#             - Assume today's date is {today_str}.

#             **Your Rules:**
#             1.  **USE TOOLS, BUT BE BRIEF:** Use your tools to find information, but only state the final, most important piece of information (e.g., the final price, the main travel method, the weather condition).
#             2.  **ONE FACT AT A TIME:** For a travel plan, just give the main mode of transport and the total time. Wait for the user to ask for step-by-step directions.
#             3.  **DO NOT HALLUCINATE:** Never invent information. If your tools don't find an answer, say so.
#             """
#         ),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("user", "{input}"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )







# The new, correct agent definition
agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(x["intermediate_steps"]),
        "chat_history": lambda x: x["chat_history"], # <-- ADD THIS LINE
    }
    | prompt
    | llm.bind_tools(tools)
    | OpenAIToolsAgentOutputParser()
)


agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)



# ---
# Step 5: Flask Web Server Setup
# ==================================
app = Flask(__name__)
# The more explicit version
CORS(app, resources={r"/process_command": {"origins": "*"}})

VOICE_SERVICE_URL = "http://localhost:5001"

























# # Replace your entire old function with this new one
# @app.route('/process_command', methods=['POST'])
# def process_command():
#     data = request.json
#     if not data or 'query' not in data or 'session_id' not in data:
#         return jsonify({"error": "Invalid request. 'query' and 'session_id' are required."}), 400

#     user_query = data['query']
#     session_id = data['session_id']
#     print(f"\n[Session: {session_id}] Received query: {user_query}")

#     if session_id not in session_histories:
#         session_histories[session_id] = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
     
#     memory = session_histories[session_id]
#     agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

#     try:
#         result = agent_executor.invoke({
#             "input": user_query,
#             "chat_history": memory.load_memory_variables({})['chat_history']
#         })
         
#         if not result.get('intermediate_steps'):
#             # CASE 1: No tool was used. Agent is asking a question.
#             response_text = result.get('output')
#             response_data = {"response": response_text}
#             memory.save_context({"input": user_query}, {"output": response_text})
#         else:
#             # CASE 2: A tool was used. Format the output.
#             tool_output = result.get('output')
#             memory.save_context({"input": user_query}, {"output": tool_output})

#             # Use the new ConversationalResponse parser
#             parser = JsonOutputParser(pydantic_object=ConversationalResponse)
             
#             format_prompt_template = """
#             Based on the tool's output, formulate a very brief and conversational response.
#             Your goal is to be a quick inquiry agent. Do not write a long paragraph.
#             Pick one key piece of information and present it as a suggestion.
#             For example: 'I found a flight for you on IndiGo, it costs about ₹2,500.' OR 'It looks like it will be partly cloudy in Bhagalpur.'

#             Original Query: {query}
#             Tool Output: {tool_output}

#             {format_instructions}
#             """
             
#             format_prompt = ChatPromptTemplate.from_template(format_prompt_template, partial_variables={"format_instructions": parser.get_format_instructions()})
#             formatting_llm = ChatGroq(model="llama3-8b-8192", temperature=0.1)
#             formatting_chain = format_prompt | formatting_llm | parser
#             response_data = formatting_chain.invoke({"query": user_query, "tool_output": tool_output})
         
#         return jsonify(response_data)

#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return jsonify({"error": "Failed to process the request."}), 500
     
# # Replace your entire old function with this new one
# @app.route('/process_command', methods=['POST'])
# def process_command():
#     data = request.json
#     user_query = data.get('query')
#     session_id = data.get('session_id')
#     print(f"\n[Session: {session_id}] Received query: {user_query}")

#     if session_id not in session_histories:
#         session_histories[session_id] = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
    
#     memory = session_histories[session_id]

#     try:
#         result = agent_executor.invoke({
#             "input": user_query,
#             "chat_history": memory.load_memory_variables({}).get('chat_history', [])
#         })
        
#         response_text = result.get('output')
#         memory.save_context({"input": user_query}, {"output": response_text})
        
#         # --- ADD THIS LOGGING CALL for SUCCESS ---
#         tool_steps = result.get('intermediate_steps', [])
#         tool_used = tool_steps[0][0].tool if tool_steps else "None"
#         log_interaction(session_id, "WebApp", user_query, tool_used, response_text)
        
#         return jsonify({"response": response_text})

#     except Exception as e:
#         # --- ADD THIS LOGGING CALL for ERRORS ---
#         log_interaction(session_id, "WebApp", user_query, "Error", "", str(e))
        
#         print(f"An error occurred in process_command: {e}")
#         return jsonify({"error": "Failed to process the request."}), 500



# The fully corrected and simplified function
@app.route('/process_command', methods=['POST'])
def process_command():
    data = request.json
    if not data or 'query' not in data or 'session_id' not in data:
        return jsonify({"error": "Invalid request. 'query' and 'session_id' are required."}), 400

    user_query = data['query']
    session_id = data['session_id']
    print(f"\n[Session: {session_id}] Received query: {user_query}")

    if session_id not in session_histories:
        session_histories[session_id] = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
     
    memory = session_histories[session_id]

    try:
        # 1. Invoke the agent to get the result
        result = agent_executor.invoke({
            "input": user_query,
            "chat_history": memory.load_memory_variables({}).get('chat_history', [])
        })
        
        # 2. Get the final, user-facing response text
        response_text = result.get('output')
        
        # 3. Save the conversation context to memory
        memory.save_context({"input": user_query}, {"output": response_text})
        
        # 4. Correctly determine which tool was used (if any)
        # This works for both cases:
        # - If a tool was used, it gets the name.
        # - If no tool was used, 'intermediate_steps' is empty, and it correctly becomes "None".
        tool_steps = result.get('intermediate_steps', [])
        tool_used = tool_steps[0][0].tool if tool_steps else "None"
        
        # 5. Log the interaction with the CORRECT tool name
        log_interaction(session_id, "WebApp", user_query, tool_used, response_text)
        
        # 6. Return the response to the user
        return jsonify({"response": response_text})

    except Exception as e:
        # This part for error logging remains the same
        log_interaction(session_id, "WebApp", user_query, "Error", "", str(e))
        print(f"An error occurred in process_command: {e}")
        return jsonify({"error": "Failed to process the request."}), 500










# The fully integrated and corrected function
# @app.route('/process_command', methods=['POST'])
# def process_command():
#     data = request.json
#     if not data or 'query' not in data or 'session_id' not in data:
#         return jsonify({"error": "Invalid request. 'query' and 'session_id' are required."}), 400

#     user_query = data['query']
#     session_id = data['session_id']
#     print(f"\n[Session: {session_id}] Received query: {user_query}")

#     if session_id not in session_histories:
#         session_histories[session_id] = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
     
#     memory = session_histories[session_id]
    
    
    # This agent_executor is defined outside, so we just use it
    # agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # try:
    #     result = agent_executor.invoke({
    #         "input": user_query,
    #         "chat_history": memory.load_memory_variables({}).get('chat_history', [])
    #     })
         
    #     # CASE 1: No tool was used by the agent.
    #     if not result.get('intermediate_steps'):
    #         response_text = result.get('output')
    #         response_data = {"response": response_text}
    #         memory.save_context({"input": user_query}, {"output": response_text})
            
    #         # --- LOGGING for SUCCESS (No Tool) ---
    #         log_interaction(session_id, "WebApp", user_query, "None", response_text)

    #     # CASE 2: A tool was used, so we format the output to be conversational.
    #     else:
    #         tool_output = result.get('output')
    #         memory.save_context({"input": user_query}, {"output": tool_output})

    #         # This logic determines which tool was used for the log
    #         tool_steps = result.get('intermediate_steps', [])
    #         tool_used = tool_steps[0][0].tool if tool_steps else "None"

    #         # Use the ConversationalResponse parser for a friendly final response
    #         parser = JsonOutputParser(pydantic_object=ConversationalResponse)
             
    #         format_prompt_template = """
    #         # Based on the tool's output, formulate a very brief and conversational response.
    #         Your goal is to be a quick inquiry agent. Do not write a long paragraph.
    #         Pick one key piece of information and present it as a suggestion.
    #         For example: 'I found a flight for you on IndiGo, it costs about ₹2,500.' OR 'It looks like it will be partly cloudy in Bhagalpur.'

    #         Original Query: {query}
    #         Tool Output: {tool_output}

    #         {format_instructions}
    #         """
             
    #         format_prompt = ChatPromptTemplate.from_template(format_prompt_template, partial_variables={"format_instructions": parser.get_format_instructions()})
    #         formatting_llm = ChatGroq(model="llama3-8b-8192", temperature=0.1)
    #         formatting_chain = format_prompt | formatting_llm | parser
            
    #         # This invokes the formatting chain to get the final, user-facing response
    #         response_data = formatting_chain.invoke({"query": user_query, "tool_output": tool_output})
            
    #         # --- LOGGING for SUCCESS (Tool Used) ---
    #         # We log the *final formatted response* that the user actually sees
    #         log_interaction(session_id, "WebApp", user_query, tool_used, response_data['response'])
         
    #     return jsonify(response_data)

    # except Exception as e:
    #     # --- LOGGING for ERRORS ---
    #     log_interaction(session_id, "WebApp", user_query, "Error", "", str(e))

    #     print(f"An error occurred in process_command: {e}")
    #     return jsonify({"error": "Failed to process the request."}), 500
        


# # --- ADD THIS ENTIRE WHATSAPP HANDLER ---
# @app.route("/whatsapp", methods=['POST'])
# def handle_whatsapp():
#     """Handles incoming messages from Twilio WhatsApp."""
#     incoming_msg = request.values.get('Body', '').lower()
#     from_number = request.values.get('From', '') # Format: whatsapp:+14155238886
#     print(f"--- WhatsApp Message Received from {from_number}: {incoming_msg} ---")

#     # Use the phone number as a unique session ID
#     session_id = from_number

#     # Initialize memory for new users
#     if session_id not in session_histories:
#         session_histories[session_id] = ConversationBufferWindowMemory(
#             k=5, memory_key="chat_history", return_messages=True
#         )
#     memory = session_histories[session_id]

#     try:
#         # Get a response from your LangChain agent
#         result = agent_executor.invoke({
#             "input": incoming_msg,
#             "chat_history": memory.load_memory_variables({})['chat_history']
#         })
#         agent_response = result.get('output', "Sorry, I had trouble processing that.")

#         # Save context to memory
#         memory.save_context({"input": incoming_msg}, {"output": agent_response})
#         print(f"--- Agent Response: {agent_response} ---")

#         # Create a TwiML response to send back to WhatsApp
#         twiml_response = MessagingResponse()
#         twiml_response.message(agent_response)

#         return str(twiml_response), 200, {'Content-Type': 'text/xml'}

#     except Exception as e:
#         print(f"!!! An Error Occurred: {e} !!!")
#         twiml_response = MessagingResponse()
#         twiml_response.message("Apologies, an error occurred. Please try again.")
#         return str(twiml_response), 200, {'Content-Type': 'text/xml'}


@app.route("/whatsapp", methods=['POST'])
def handle_whatsapp():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    print(f"--- WhatsApp Message Received from {from_number}: {incoming_msg} ---")
    session_id = from_number

    if session_id not in session_histories:
        session_histories[session_id] = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
    memory = session_histories[session_id]

    try:
        result = agent_executor.invoke({
            "input": incoming_msg,
            "chat_history": memory.load_memory_variables({}).get('chat_history', [])
        })
        agent_response = result.get('output', "Sorry, I had trouble processing that.")
        memory.save_context({"input": incoming_msg}, {"output": agent_response})
        
        # --- ADD THIS LOGGING CALL for SUCCESS ---
        tool_steps = result.get('intermediate_steps', [])
        tool_used = tool_steps[0][0].tool if tool_steps else "None"
        log_interaction(session_id, "WhatsApp", incoming_msg, tool_used, agent_response)
        
        print(f"--- Agent Response: {agent_response} ---")
        twiml_response = MessagingResponse()
        twiml_response.message(agent_response)
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}

    except Exception as e:
        # --- ADD THIS LOGGING CALL for ERRORS ---
        log_interaction(session_id, "WhatsApp", incoming_msg, "Error", "", str(e))
        
        print(f"!!! An Error Occurred in WhatsApp handler: {e} !!!")
        twiml_response = MessagingResponse()
        twiml_response.message("Apologies, an error occurred. Please try again.")
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}










# --- This should be the last part of your file ---
# CORRECT: Only one of these blocks at the very end.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
