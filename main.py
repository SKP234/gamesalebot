import discord
import os
import requests
import random
from replit import db #uses replit's database
from discord.ext import commands, tasks #to be able to loop the reminder every 24 hours
from datetime import datetime, time, timezone, timedelta #to get time and date
import asyncio

# Initialize the client
client = discord.Client()




@tasks.loop(hours=24)  #loops the message every 24 hours
async def daily_reminder():
    await daily_message() 

@daily_reminder.before_loop #does this before the main loop
async def before_daily_task():
    await client.wait_until_ready() #makes sure the bot is initialized before this
    now = datetime.now(timezone.utc) #gets current time in utc
    target_time = time(hour=19, minute=0, second=0, tzinfo=timezone.utc) #noon(12pm) pst is target_time
    next_time = datetime.combine(now.date(), target_time) #combines now.date() which is the day and target_time which is the hours, minutes, seconds into next_time which is the next date(today) and time(at noon) at which the loop will start running
    delay = (next_time - now).total_seconds() #calculates time until next noon
    if delay < 0: #will be negative if bot starts after noon
      delay = 86400 + delay
    print(delay) #just to know how many seconds until it loops next when i start the bot
    await asyncio.sleep(delay) #waits until noon

async def daily_message():
  channel = client.get_channel(778661231639789579) 
  for discord_id in db["Opt_List"]: #for those who optted in
    if discord_id in db["User_List"]: #and for those who have added games
      discord_id = str(discord_id)
      user = await client.fetch_user(int(discord_id))
      result = await get_disc_list(db[f"User{discord_id}"])
      await user.send(result) #sends the discounted games to user
      await channel.send(f"Message sent to {user.name}, {discord_id}") #will output to my channel server who is being messaged
    





async def search_game_id(game_name): #returns deal game id using search api
      response = requests.get(f'https://www.cheapshark.com/api/1.0/games?title={game_name}') #returns list of games with the name
      data = response.json()

      if len(data) > 0:
        game_id = data[0].get("cheapestDealID") #takes first game's id
        return game_id
  
async def get_formatted_list(disc_list): #gets information from the list of deal game ids and returns a formatted string of information from all the ids
  info_list = []
  for id in disc_list:
    deal_info = requests.get(f'https://www.cheapshark.com/api/1.0/deals?id={id}') #uses id from list to get information on the game and it's discount
    deal_data = deal_info.json()
    game_info = [f"Game: {deal_data['gameInfo']['name']}",
                 f"Base price: {deal_data['gameInfo']['salePrice']}",
                 f"Lowest price: {deal_data['gameInfo']['retailPrice']}",
                 f"Store link: https://www.cheapshark.com/redirect?dealID={id}"]
    info_list.append('\n'.join(game_info)) 
  formatted_list = ('\n\n'.join(info_list)) #combines the super long list into 1 formatted string
  return formatted_list

async def get_disc_list(list): #from the list associated to a user id, returns a list of game that are on discount
  game_list = list
  disc_list = []
  for games in game_list:
    game_id = await search_game_id(games)
    if game_id:
      deal_info = requests.get(f'https://www.cheapshark.com/api/1.0/deals?id={game_id}')
      deal_data = deal_info.json()
      if deal_data['gameInfo']['retailPrice'] != deal_data['gameInfo']['salePrice']: #compares the base price and the lowest found price to see if it has a discount
        disc_list.append(game_id) #adds discounted game id to list if it is on sale
  return await get_formatted_list(disc_list)


@client.event
async def on_ready():
    print('We have logged in as Client {0.user}'.format(client))
    daily_reminder.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
      
#############################################################################################      
    if message.content.startswith('!link'): #links discord id and steam id with the discord id as the key and the steam id as the value
      try:
        steam_id = int(message.content.split("!link",1)[1]) #checks if input is an int
      except:
        await message.channel.send("invalid input")
        return
      #changes steamid to a string
      steam_id = str(steam_id)
      discord_id = str(message.author.id)
      response = requests.get(f'https://store.steampowered.com/wishlist/profiles/{steam_id}/wishlistdata/?p=0')
      data = response.json()
      if response.status_code == 200: #checks for a successful steam id hopefully
        if discord_id in db.keys(): #checks if discord id is already linked
          await message.channel.send("This discord id is already linked to a steam id, !unlink to unlink.")
        else: #saves discord_id as a key and steam_id as a value
          db[discord_id] = steam_id
          await message.channel.send(steam_id + "(steam_id) linked to " + discord_id + "(discord_id)")
      else:
        await message.channel.send('No wishlist was found for this Steam ID, wishlist is private, or this Steam ID input is invalid.')
        
#############################################################################################        
    if message.content.startswith('!unlink'): #deletes the discord id key of the user from the database if it exists
      discord_id = str(message.author.id)
      if discord_id in db.keys(): #if there is a discord_id in database
        steam_id = db[discord_id]
        await message.channel.send(steam_id + "(steam_id) unlinked from " + discord_id + "(discord_id)")
        del db[discord_id]
      else:
        await message.channel.send('Your discord id is not linked to a steam id.')
        
#############################################################################################                  
    if message.content.startswith('!check'): #send a message to the channel if you linked your discord id and steam id
      discord_id = str(message.author.id)
      if discord_id in db.keys():
        await message.channel.send(discord_id + "(discord id) is linked to " + db[discord_id] + "(steam id)")
        
#############################################################################################      
    if message.content.startswith('!list'): #sends users entire steam wishlist's game's names
      try:
        page = int(message.content.split("!list",1)[1])
      except:
        await message.channel.send("invalid input, !list <page>")
        return
      discord_id = str(message.author.id)
      steam_id = db[discord_id]
      page_index = 0
      response = requests.get(f'https://store.steampowered.com/wishlist/profiles/{steam_id}/wishlistdata/?p={page_index}') #gets steam wishlist
      data = response.json()
      
      game_list = []
      while len(data) > 0: #while there are games on the current page of the wishlist
        page_index += 1 #increments through the pages of the wishlist
        game_index = 0 
        for name, game in data.items():
          game_list.append(game['name']) #appends all the names of the games on the current page to the list
        response = requests.get(f'https://store.steampowered.com/wishlist/profiles/{steam_id}/wishlistdata/?p={page_index}') #goes to next page
        data = response.json()
      max_index = len(game_list)/50 
      max_index = int(max_index) + 1 if max_index > 0 else int(max_index) #calculates how many pages there are in the whole wishlist
      if page > 0 and page <= max_index:
        page_games = game_list[(page-1)*50:(page)*50] #only prints 50 games per page for the user inputted index
        formatted_list = '\n'.join(page_games)
        await message.channel.send("Page " + str(page) + " out of " + str(max_index))
        await message.channel.send("----------------")
        await message.channel.send(formatted_list)
      else:
        await message.channel.send("please choose an index between 1 and " + str(max_index))
        
#############################################################################################  
    if message.content.startswith('!search'): #looks up the game and messages back the name, base price, sale price, and sale link
      try:
        game_title = message.content.split("!search ",1)[1]
      except:
        await message.channel.send("invalid input, !search <name>")
      response = requests.get(f'https://www.cheapshark.com/api/1.0/games?title={game_title}') #returns list of games with the name
      data = response.json()

      if len(data) > 0:
        game = data[0]
        deal_id = game['cheapestDealID']
        
        deal_info = requests.get(f'https://www.cheapshark.com/api/1.0/deals?id={deal_id}')
        deal_data = deal_info.json()
        store_link = f'https://www.cheapshark.com/redirect?dealID={deal_id}'
        response_text = (f"Game: {deal_data['gameInfo']['name']}\n"
                         f"Base price: ${deal_data['gameInfo']['retailPrice']}\n"
                         f"Lowest price: ${deal_data['gameInfo']['salePrice']}\n"
                         f"Store link: {store_link}")
        await message.channel.send(response_text)
      else:
        await message.channel.send(f"'{game_title}' could not be found.")
        
#############################################################################################        
    if message.content.startswith('!optin'): #user can opt in if they want daily messages
      if "Opt_List" in db.keys():
        if message.author.id in db["Opt_List"]:
          await message.channel.send(f"{message.author.id} is already optted in.")
        else:
          db["Opt_List"].append(message.author.id)
          await message.channel.send(f"{message.author.id} is optted in.")
      else:
        db["Opt_List"] = [message.author.id]
        
#############################################################################################      
    if message.content.startswith('!optout'): #user can opt out
      if "Opt_List" in db.keys():
        if message.author.id in db["Opt_List"]:
          db["Opt_List"].remove(message.author.id)
          await message.channel.send(f"{message.author.id} is optted out.")
        else:
          await message.channel.send(f"{message.author.id} is not optted in.")
      else:
        db["Opt_List"] = []
        await message.channel.send(f"{message.author.id} is not optted in.")
        
#############################################################################################
    if message.content.startswith('!add'): #user can add games to their list at a max of 10
      try:
        game_title = message.content.split("!add ",1)[1]
      except:
        await message.channel.send("invalid input, !add <name>")
      if "User_List" in db.keys(): #checks if there is a list and creates one if not
        pass
      else:
        db["User_List"] = []
      if message.author.id in db["User_List"]: #checks if the user is already in this list and adds their discord id if not
        pass
      else:
        db["User_List"].append(message.author.id)
      #
      response = requests.get(f'https://www.cheapshark.com/api/1.0/games?title={game_title}') #returns list of games with the name
      data = response.json()
      game = data[0] #takes first game in the list
      if len(game) == 0: #if the search finds a game it will add it to the database with the user id as the key
        await message.channel.send(f"{game_title} was not found")
        return
      else:
        game_name = game["external"]
        if f"User{message.author.id}" in db.keys(): #checks if the individual user id has a list in the database else makes one
          pass
        else:
          db[f"User{message.author.id}"] = []
        if len(db[f"User{message.author.id}"]) > 10:
          await message.channel.send("You have reached the max of your list of 10. Use !delete to delete some games.")
          return
        else:
          db[f"User{message.author.id}"].append(game_name)
        await message.channel.send(f"{game_name} was added to your list. \nHere is your current game list:")
        await message.channel.send(db[f"User{message.author.id}"].value)
        
#############################################################################################
    if message.content.startswith('!delete'): #deletes game at given index
      try: #checks if the message was an int
        index = int(message.content.split("!delete",1)[1])
      except:
        await message.channel.send("invalid input, !delete <index>.")
        if f"User{message.author.id}" in db.keys():
          await message.channel.send("Here is your current game list:")
          await message.channel.send(db[f"User{message.author.id}.value"])
      if f"User{message.author.id}" in db.keys(): #checks if the individual user id has a list in the database
        if len(db[f"User{message.author.id}"]) >= (index + 1): #checks if the given index fits in the list
          delete_name = db[f"User{message.author.id}"][index]
          del db[f"User{message.author.id}"][index]
          await message.channel.send(f"{delete_name} has been removed from your list.")
      else:
        await message.channel.send(f"{message.author.id} is not found in the database. Use !add first")
        #############################################################################################    
    if message.content.startswith('!info'): #information
      response_text = (f"!link <steam id> to link with your discord account, !unlink to unlink\n"
                       f"!check to check what steam id is linked to your discord id\n"
                       f"!list <page index starting from 1> will send 50 games from your wishlist per page\n"
                       f"!search <game> will return information on the game of its base price and sale price\n"
                       f"!optin and !optout to use the daily reminder function\n"
                       f"!add <game> to add a game to the list to check for discounts for the daily reminder function\n"
                       f"!delete <index of list starting from 0> to delete a game from the list\n"
                       "The daily reminder function will check the list from !add for any sales and will message the user at 12 pm pst daily if any games on the list are on sale.\n")
      await message.channel.send(response_text)
    
        

client.run(os.getenv("TOKEN"))

