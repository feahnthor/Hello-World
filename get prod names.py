from bs4 import BeautifulSoup as get_soup
import requests
from webdriver_manager.chrome import ChromeDriverManager #https://github.com/SergeyPirogov/webdriver_manager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from credentials import Credentials
import re, os, logging
from time import sleep
from datetime import datetime
from scraper import file_manager
import json
import threading
"""
Code adapted from "Project article by Michael Haephrati" alexa.py
1. selecting an element using driver 
    https://stackoverflow.com/questions/25580569/get-value-of-an-input-box-using-selenium-python
2. Webdriver commands/methods https://selenium-python.readthedocs.io/api.html
Issues with td tag returning blank text solved https://stackoverflow.com/questions/48363539/selenium-python-scrape-td-element-returns-blank-text
Issues: requests does not get the entire dom for imagebuggy admin, so we need to get using selenium

* Python 3 fastest dict key check https://www.tutorialspoint.com/python3/dictionary_has_key.htm
* Merging dictionaries https://thispointer.com/how-to-merge-two-or-more-dictionaries-in-python/
* Webddriver commands https://www.toolsqa.com/selenium-webdriver/webelement-commands/
* Webdriver getattribute https://blog.cloudboost.io/why-textcontent-is-better-than-innerhtml-and-innertext-9f8073eb9061
Goals 
1. Get Product names and ids
2. Get designer names
"""
start_time = datetime.now()
logger = logging.getLogger("backgroundtown")
formatter = logging.Formatter("%(asctime)s; %(levelname)s    %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
file_handler = logging.FileHandler(filename="bg-town product.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


# url = 'https://backgroundtown.com/backgroundtown/CA/Admin/StaticPDFProduct/Create'

class WindowsInhibitor:
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def __init__(self):
        pass

    def inhibit(self):
        import ctypes
        print("Preventing Windows from going to sleep.")
        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS | \
            WindowsInhibitor.ES_SYSTEM_REQUIRED)

    def uninhibit(self):
        import ctypes
        print("Allowing Windows to go to sleep.")
        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS)

# submit = driver.find_element_by_class_name('loginbutton')
# submit.click()

def init_driver():
  logger.info("Starting chromedriver")
  chrome_options = Options()
  # use local data directory
  # headless mode can't be enabled since then amazon shows captcha
  # headless mode increases speed
  chrome_options.add_argument('--headless')
  chrome_options.add_argument("user-data-dir=selenium")
  # chrome_options.add_argument("start-maximized")
  chrome_options.add_argument("--disable-infobars")
  chrome_options.add_argument('--disable-gpu')
  # chrome_options.add_argument('user-data-dir=selenium')  
  chrome_options.add_argument('--remote-debugging-port=4444')
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  chrome_options.add_argument("--mute-audio")
  
  try:
    driver = webdriver.Chrome(ChromeDriverManager().install(),
      options = chrome_options, service_log_path='NUL')
  except ValueError:
    logger.critical("Error opening Chrome. Chrome is not installed?")
    exit(1)
  driver.implicitly_wait(10)
  return driver

def url_login(driver,url):
  driver.implicitly_wait(5)
  logger.info(f"GET test 1 {url}")
  # get main page
  driver.get(url)
  # sleep(4)
  url = driver.current_url
  # if site asks for signin, it will redirect to a page with signin in url
  if 'login' in url:
    logger.info("Got login page: logging in...")
    # find email field
    # WebDriverWait waits until elements appear on the page
    # so it prevents script from failing in case page is still being loaded
    # Also if script fails to find the elements (which should not happen
    # but happens if your internet connection fails)
    # it is possible to catch TimeOutError and loop the script, so it will
    # repeat.
    check_field = WebDriverWait(driver, 30).until(
      EC.presence_of_element_located((By.ID, 'LoginEmail')))
    email_field = driver.find_element_by_id('LoginEmail')
    email_field.clear()
    # type email
    email_field.send_keys(Credentials.email)
    check_field = WebDriverWait(driver, 30).until(
      EC.presence_of_element_located((By.ID, 'LoginPassword')))
    # find password field
    password_field = driver.find_element_by_id('LoginPassword')
    password_field.clear()
    # type password
    password_field.send_keys(Credentials.password)
    # find submit button, submit
    check_field = WebDriverWait(driver, 30).until(
      EC.presence_of_element_located((By.CLASS_NAME, 'loginbutton')))
    submit = driver.find_element_by_class_name('loginbutton')
    submit.click()
    logger.info('Login Successful')

def open_json(file_name):
  with open(file_name, 'r+') as json_file:
    data = json.load(json_file)
  return data

def get_available_products(driver):
  product_object_dict = {}
  # json_id = False
  # json_name = False
  if os.path.isfile('bg-products.json'):
    logger.info(f'JSON FILE FOUND!')
  logger.info('Getting products and their IDs...')
  WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'ProductVariants')))
  product_selector = driver.find_elements_by_css_selector('#ProductVariants option')

  for web_element in product_selector:
    value = web_element.get_attribute('value') #get attribute value
    product_name = web_element.get_attribute('textContent') #get innerhtml text
    product_object = {
      'name': product_name
    }
    product_object_dict[value] = product_object
  logger.info('Done. Got list containing product objects')
  return product_object_dict

def get_catgeory(driver,url, product_dict):
  url_login(driver, url)
  changes_made = False
  file_dict = open_json('bg-products.json')
  dirName = os.getcwd()
    
  for key, val in product_dict.items():
    try:
      if key not in file_dict:
        logger.info('FOUND PRODUCT ID NOT IN JSON FILE')
        logger.info(f'https://backgroundtown.com/Admin/Product/Edit/{key}')
        driver.get(f'https://backgroundtown.com/Admin/Product/Edit/{key}')
        check_field = WebDriverWait(driver, 30).until(
          EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit ul li')))

        category_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[3] # category tab
        category_tab_selector.click() #clicking ensures page is loaded enough to have entire category list, so it avoid issues discussed below about StaleElementReferenceException

        check_failed = WebDriverWait(driver, 30).until(
          EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit-4 #productcategories-grid tbody tr td'))) 
        designer_selector = driver.find_elements_by_css_selector('#product-edit-4 #productcategories-grid tbody tr td') 
        #allows webdriver to wait for all elements, there was an issue where there would  only be 1 td loaded so indexing would not work to avoid StaleElementReferenceException
        
        for index in range(len(designer_selector)):
          # catch cases where designer is not first in the table
          category = designer_selector[index].get_attribute("textContent") #textContent is a better method, took care of "Themes >> Party Backdrops" special case
        #                                                                           https://blog.cloudboost.io/why-textcontent-is-better-than-innerhtml-and-innertext-9f8073eb9061
          if 'Designer >>' not in category and 'ACI Collection' not in category:
            continue
          else:
            designer = category
        product_dict[key].update({'designer' : designer}) #combine dictionary
        file_dict[key] = product_dict[key]
        changes_made = True
        
      else: 
        continue
    except (KeyboardInterrupt, TimeoutException):
      fm = file_manager(dirName, '', 'bg-products.json', file_dict, 'w')
      fm.createFile()
      driver.quit()
  if changes_made == True:
    # make changes to file, if changes is has been added
    fm = file_manager(dirName, '', 'bg-products.json', file_dict, 'w')
    fm.createFile()
    logger.info(f'Done. File has been updated in {dirName}')
    driver.quit()
  else:
    logger.info(f'Done. No changes made to file in {dirName}')
    driver.quit()

def check_production_folder():
  """
  Check \\\\\work\\production\\backgroundtown images\\{designer} to see if files containing
    the same name exists.
  """
  now = datetime.now()
  product_dict = open_json('bg-products.json')
  production = '\\\\work\\production\\backgroundtown images\\'
  marketing = '\\\\work\\marketing\\backgroundtown\\backgrounds to add to the web\\'
  os.chdir(production)
  count = 0
  
  for key, value in product_dict.items():
    # logger.info(os.getcwd())
    cur_dir = os.chdir(f'{production}{value["designer"]}')
    # logger.info(f'Directory changed to {cur_dir}')
    if os.path.isfile(f'{value["name"]}.jpg'):
      # logger.info(f'Product image found! {os.getcwd()}\\{value["name"]}.jpg')
      count += 1
    elif os.path.isfile(f'{marketing}{value["designer"]}\\{value["name"]}.jpg'):
      logger.info(f'Found these files in Designer folder instead {key}: {value}')
      count += 1
    else:
      logger.info(f'Did not find these product {key}: {value}')
  logger.info(f'Total files found => {count}/{len(product_dict)} \t\t {datetime.now() - now} seconds')

def main():
  sys_sleep = None
  sys_sleep = WindowsInhibitor()
  logger.info('System inhibited')
  sys_sleep.inhibit()

  
  # fm = file_manager(dirName, False, 'bg-products.json', False, False)
  
  url = 'https://backgroundtown.com/Admin/Product/Edit/50'
  normal_product_url_info = 'https://backgroundtown.com/CA/Admin/StaticPDFProduct/Create'
  #start driver
  driver = init_driver()

  while True:
    try:
      url_login(driver, normal_product_url_info)
      # first function following url does not need a url
      product_dict = get_available_products(driver) 
      get_catgeory(driver, url, product_dict)
      # check_production_folder()
      thread = threading.Thread(target = check_production_folder)
      thread.start()
      thread.join()
      break
    except TimeoutException:
      # catch broken connection
      logger.critical("Timeout exception. No internet connection? "
      "Retrying...")
      sleep(10)
      continue
if __name__ == '__main__':
  
  main()
