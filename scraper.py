#! python 3
# scraper.py
"""
Code adapted from "Project article by Michael Haephrati" alexa.py
Author: r/YourDaree
Description: Program to store local copies of a novel in order to test out scraping. 
              End goal is to have chapters be added to my reading list in @Voice aloud Reader
Should start at chapter 1 and end once a chapter has been reached where there is no content
VERSION: .1
Future update plans:
  *1. Make it so program automatically checks folders for last completed chapter and set that as the starting location
      this can either be done by checking 'failed_links.txt' or the chapters folder (sort may be needed.)
  2. Let users be able to enter a list of novels they want from wuxiaworld so program can loop through each
  *3. Make it more open to accepting other sites, may need to test if a second chapter can be reach if user enters a first one
  *4. Save file as html to see if reader will pick it up.
  *5. Upload to Google drive folder to allow @Voice Aloud Reader to open chapters on my phone to listen to
  6. Automate entire process to check each novel for updates
  7. Try multithreading
  8. For royal road novels you need to index to 2 for next chapter button since all three <a> elements
    have the same class names

"""

import ctypes
import sys
import os
from pathlib import Path #used to get home directory and works on all platforms
# https://stackoverflow.com/questions/4028904/how-to-get-the-home-directory-in-python
import logging
from natsort import natsorted 
import datetime
from time import sleep
import re #literally only to take care of special characters in file names
import json # used for getting json data for each novel
import sched, time # event scheduler to make the run at certain times

keep_looping = True
script_dir = os.getcwd()
startTime = datetime.datetime.now()
logger = logging.getLogger("novel collector")
formatter = logging.Formatter("%(asctime)s;%(levelname)s    %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
file_handler = logging.FileHandler(filename="novel scrapper.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


try:
  #i honestly just like using this import method for when i have to switch pcs to keep working as i do not know how to use git correctly
  import requests
  import bs4
  
  from bs4 import BeautifulSoup as get_soup
except ModuleNotFoundError:
  import subprocess
  subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
  subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'bs4'])
  import requests
  import bs4
  from bs4 import BeautifulSoup as get_soup


class WindowsInhibitor:
  # Prevent Windows from going to sleep
  ES_CONTINUOUS = 0x80000000
  ES_SYSTEM_REQUIRED = 0x00000001

  def __init__(self):
    pass

  def inhibit(self):
    print("Preventing Windows from going to sleep.")
    ctypes.windll.kernel32.SetThreadExecutionState(
      WindowsInhibitor.ES_CONTINUOUS | \
      WindowsInhibitor.ES_SYSTEM_REQUIRED)

  def uninhibit(self):
    print("Allowing Windows to go to sleep.")
    ctypes.windll.kernel32.SetThreadExecutionState(
      WindowsInhibitor.ES_CONTINUOUS)
 
def fetch(url, chapter_content_tag, next_chapter_tag, dirName):
  global keep_looping
  attempt = 0
  now = datetime.datetime.now()
   #https://www.wuxiaworld.com/novel/keyboard-immortal/ki-chapter-
  # url = f'{url}{chapter}'
  
  chapter_content = ''
  while True:
    
    headers = {'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.63'}
    #user agent gotten from running 'navigator.userAgent' in browser console
    
    while True:
      try:
        print(f'Get {url}')
        ses = requests.Session()
        ses.headers = {'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.63'}
        #user agent gotten from running 'navigator.userAgent' in browser console
        res = ses.get(url)
        status = res.status_code
        soup = get_soup(res.content, 'html.parser')
        #only takes tags that are part of the chapter content
        # p_tag = soup.select('#chapter-content p')
        p_tag = soup.select(chapter_content_tag)
        try: 
          # next_chapter = soup.select('.section-content .next a.btn-link')[0]['href'] 
          next_chapter_url = soup.select(next_chapter_tag)[0]['href'] 
          logger.info(f'NEXT CHAPTER FOUND {next_chapter_url}')
        except IndexError: #Happens once a value can no longer be retrieved
          # next_chapter_url = ''
          logger.critical('NO MORE CHAPTERS')
        #way to check for new chapter
        #because soup select returns a list, i must index into it to get the value of the href value
        
        # print(f'Chapter P_Length = {len(p_tag)}\n\nReturned Status: {status}')
        # Extract title of page
        # add .text to get the string within the container
        page_title = soup.title.text
        page_title_text = soup.title
        print(page_title)
        chapter_content += f'{page_title_text}\n\n'
        break
      except requests.exceptions.RequestException as e:
        # If Internet connection fails, keep trying until success.
        print('Connection unsuccessful\n\nRetrying...')
        sleep(5)
        continue
    if status == 200:
      ## checks if link is valid
      if len(p_tag) > 12: #greater than 10 takes ignores teaser chapters on wuxiaworld
        # print(f'{page_title}\n\n <p> length = {len(p_tag)}')
        page_title = re.sub('[^A-Za-z0-9]+', ' ', page_title) #remove special characters
        for i in range(len(p_tag)):
          chapter_content += f'{p_tag[i]}\n'
          # chapter_content += f'{p_tag[i].text}\n' #gets rid of tags for txt files
          # print(f'{i}). {p_tag[i].text}')
        try:
          file_manager(dirName,'Chapters', f'{page_title}.html', chapter_content , 'w')
          return next_chapter_url
        except (OSError, UnboundLocalError): 
          #Unbound Error handling to take care of issue where there is no next chapter found
            #instead of erroring out, "variable next_chapter_url referenced before assignment"
          logger.critical('FILE CREATION ERROR MAY BE A SPECIAL CHARACTER')
          file_manager(dirName,'Errors', 'failed_links.txt', f'{now}\t{page_title}\n', 'a+')
          keep_looping = False
          return url # returns last successful url, put here for when no other url can be found next_chapter_url 
      else:
        logger.critical('Response of chapter with no content')
        #send to function to create file, by joining directory with file name
        file_manager(dirName,'Errors', 'failed_links.txt', f'{now}\t{url}\n', 'a+')
        logger.info('Written the link to "failed_links.txt" file.\n')
        logger.info(now - startTime)
        keep_looping = False
        return url
        
    else:
    
      logger.critical(f'Attempt to reach site failed\nResponse code: {status}')
      #send to function to create file, by joining directory with file name
      file_manager(dirName,'Errors', f'{status}_failed.txt', f'{now}\t{url}\n', 'a+')
      logger.info(f'Written the link to "{status}_failed.txt" file.\n')
      # if response code is not 200, something is either wrong with 
      # retry 5 times, then quit the program
      if attempt <= 5:
        logger.info(f'Retrying. Attempt #{attempt}')
        sleep(5)
        attempt += 1
        continue
      else:
        logger.critical('Failed all attempts to reach site')
        keep_looping = False
        # return
class file_manager(): 
  """Manages file
    filemode must be letters i.e. 'a, w, r, wb' or any other file methods to open
    set new instance of current directory to use
  """
  def __init__(self, dirName, subFolderName, filename, fileContent, filemode):
      self.dirName = dirName
      self.subFolderName = subFolderName
      self.fileName = filename
      self.fileContent = fileContent
      self.fileMode = filemode

  # def createFile(dirName, subfolderName,  fileName, fileContent, filemode):
  def createFile(self):
    
    #filemode must be letters i.e. 'a, w, r, wb' or any other file methods to open
    #set new instance of current directory to use
    os.chdir(self.dirName)
    #concatenate
    if '.json' in self.fileName:
      self.fileContent = json.dumps(self.fileContent)
    complete_file_name = os.path.join(f'{os.getcwd()}\\{self.subFolderName}\\',self.fileName)
    with open(complete_file_name, self.fileMode, encoding='utf-8') as append_file:
      #need to encode utf-8 to avoid "UnicodeEncodeError: 'charmap'..."
      append_file.write(self.fileContent)
    # os.chdir(self.dirName)
    # #concatenate
    
    # complete_file_name = os.path.join(f'{os.getcwd()}\\{self.subFolderName}\\',self.fileName)
    # with open(complete_file_name, self.fileMode, encoding='utf-8') as append_file:
    #   #need to encode utf-8 to avoid "UnicodeEncodeError: 'charmap'..."
    #   append_file.write(self.fileContent)

def readJsonFile(url, time, make_changes):
  print(f'CURRENT DIRECTORY {os.getcwd()}\n')
  'https://stackoverflow.com/questions/13949637/how-to-update-json-file-with-python'
  with open('novel url start.json', 'r+') as json_file: #currently json name is static
    data = json.load(json_file)
    print(data[0].keys())
    # key = data[0].keys()
    
    novel_object = data[0]['wuxiaworld'][1]
    novel_name = novel_object['name']
    first_chapter = novel_object['first_chapter']
    cur_chapter = novel_object['current_chapter']
    next_chapter_tag = novel_object['next-chapter']
    chapter_content_tag = novel_object['chapter-content']
    base_url = novel_object['base_url']
    print(novel_name,first_chapter,cur_chapter,next_chapter_tag,chapter_content_tag)

    if make_changes == True: #write changes
      novel_object['current_chapter'] = url
      novel_object['time'] = time
      json_file.seek(0) #start back at the beginning of file
      json.dump(data, json_file)
      json_file.truncate()
  print(datetime.datetime.now(), 'finally done writing count = 0')
  return novel_name, first_chapter, cur_chapter, next_chapter_tag, chapter_content_tag, base_url
  
def main():
  
  homeDir = str(Path.home())
  logger.debug(f'USER HOME DIR IS {homeDir}')
  novel_name, first_chapter, cur_chapter, next_chapter_tag, chapter_content_tag, base_url = readJsonFile(False, str(datetime.datetime.now()), False)
  # dirName = f'{homeDir}\\Documents\\{site_folder}\\{novel_folder}'
  dirName = f'{homeDir}\\Documents\\Wuxiaworld\\{novel_name}'
  # cur_chapter = 191
  # cur_chapter = first_chapter
  # url = f'https://www.{site_name}.com/{site_dir}/{novel_name}/{novel_initials}-chapter-'
  # url = f'https://www.{site_name}.com/{site_dir}/36735/{novel_name}/chapter/636351/'
  if cur_chapter == False:
    url = first_chapter
    print('THERE ARE NO CURRENT CHAPTERS RECORDED')
  else:
    url = cur_chapter
  
  sys_sleep = None
  sys_sleep = WindowsInhibitor()
  sys_sleep.inhibit()
  logging.getLogger().setLevel(logging.INFO)
  global keep_looping #references variable outside of this scope
  global script_dir
  # Create target directory & all intermediate directories if don't exists
  try:
    os.makedirs(dirName)
    os.makedirs(f'{dirName}\\Errors')
    os.makedirs(f'{dirName}\\Chapters')
    os.makedirs(f'{dirName}\\Uploaded')
    os.chdir(dirName)
    print(f'Directory {dirName} Created \n\n')  
  except FileExistsError:
    print(f'Directory {dirName} already exists\n\n')

  try:
    while keep_looping == True:
      #need to find a way to end loop once
      # url = f'https://wuxiaworld.com/{fetch(url, chapter_content_tag, next_chapter_tag, dirName)}'
      
      if base_url != False and 'https://' not in url:
        url = fetch(f'{base_url}{url}', chapter_content_tag, next_chapter_tag, dirName)
        
      else:
        url = fetch(url, chapter_content_tag, next_chapter_tag, dirName)
  except KeyboardInterrupt:
    logger.critical('KEYBOARD INTERRUPT TRIGGERED UPDATING JSON....')
    os.chdir(script_dir)
    readJsonFile(url, str(datetime.datetime.now()), True) # 
  print(f'last chapter {url}')
  # change directory back to write out the json
  
  os.chdir(script_dir)
  readJsonFile(url, str(datetime.datetime.now()), True) # 
    # cur_chapter += 1
    
    # sleep(3) 

if __name__ == '__main__':
  
  # main('Wuxiaworld', 'Warlock of the Magus World', 'wuxiaworld', 'novel', 'warlock-of-the-magus-world', 'wmw')
  # def main(site_folder, novel_folder,site_name, site_dir, novel_name, novel_initials):
  
  main()
  # main('Wuxiaworld', 'Keyboard Immortal', 'wuxiaworld' , 'novel', 'keyboard-immortal', 'ki')
  
  
  # main('Wuxiaworld', 'The Perfect Run', 'Royalroad', 'chapter', 'the-perfect-run','ki')
  program_runtime = datetime.datetime.now() - startTime
  logger.info(f'Program execution time: {program_runtime}')
  #main('Wuxiaworld', 'Overgeared', 'overgeared', 'og')