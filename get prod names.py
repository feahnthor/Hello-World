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
"""
Code adapted from "Project article by Michael Haephrati" alexa.py
1. selecting an element using driver 
    https://stackoverflow.com/questions/25580569/get-value-of-an-input-box-using-selenium-python
2. Webdriver commands/methods https://selenium-python.readthedocs.io/api.html
Issues with td tag returning blank text solved https://stackoverflow.com/questions/48363539/selenium-python-scrape-td-element-returns-blank-text
Issues: requests does not get the entire dom for imagebuggy admin, so we need to get using selenium

Goals 
1. Get Product names and ids
2. Get designer names
"""
start_time = datetime.now()
logger = logging.getLogger("backgroundtown")
formatter = logging.Formatter("%(asctime)s;%(levelname)s    %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
file_object_handler = logging.file_objectHandler(file_objectname="alexa.log")
file_object_handler.setFormatter(formatter)
logger.addHandler(file_object_handler)
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
  
  chrome_options.add_argument("user-data-dir=selenium") 
  chrome_options.add_argument("start-maximized")
  chrome_options.add_argument("--disable-infobars")
  chrome_options.add_argument('--disable-gpu')  
  # chrome_options.add_argument('user-data-dir=selenium')  
  chrome_options.add_argument('--remote-debugging-port=4444')
  # chrome_options.add_argument('--no-sandbox')
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

def get_catgeory(driver):
  product_list = []
  with open('product list.txt', 'r') as product_file_object:
    #https://www.toolsqa.com/selenium-webdriver/webelement-commands/
    for product_id in product_file_object:
      print(f'https://backgroundtown.com/Admin/Product/Edit/{product_id}')
      driver.get(f'https://backgroundtown.com/Admin/Product/Edit/{product_id}')
      check_field = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit ul li')))

      category = driver.find_elements_by_css_selector('#product-edit ul li')[3] # category tab




      category.click() #clicking ensures page is loaded enough to have entire category list, so it avoid issues discussed below about StaleElementReferenceException


      check_failed = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit-4 #productcategories-grid tbody tr td'))) 
      designer_selector = driver.find_elements_by_css_selector('#product-edit-4 #productcategories-grid tbody tr td') 
      #allows webdriver to wait for all elements, there was an issue where there would  only be 1 td loaded so indexing would not work to avoid StaleElementReferenceException
      # soup = get_soup(designer, 'html.parser')
      logger.info(f'Designer Found: {designer_selector[0].get_attribute("textContent")}') #textContent is a better method, took care of "Themes >> Party Backdrops" special case
      #                                                                           https://blog.cloudboost.io/why-textcontent-is-better-than-innerhtml-and-innertext-9f8073eb9061
      designer = designer[0].get_attribute("textContent")
      product_list.append() #Need to get product name
        


  # fetchData(driver)
# def fetchData(driver):
#   count = 0
#   # product_id = ''
#   # product_url = 'https://backgroundtown.com/Admin/Product/Edit/'
#   product_list = driver.find_elements_by_css_selector('#ProductVariants option')

#   cookies = driver.get_cookies()
#   # print(cookies)
#   ses = requests.Session()
#   ses.headers = {'User-Agent':
#   'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#   '(KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}

#   # pass the cookies generated dfrom the browser to the session
#   c = [ses.cookies.set(c['name'], c['value']) for c in cookies]

  
#   for foo in product_list:
#     product_id = foo.get_attribute('value')
#     product_url = f'https://backgroundtown.com/Admin/Product/Edit/{product_id}'
#     # print(foo.text, foo.get_attribute('value'))
#     count +=1
#     # logger.info(f'TOTAL: {count}')
#     # print(product_url)
#     res = ses.get(product_url)
#     status = res.status_code
#     soup = get_soup(res.content, 'html.parser')
#     # logger.info(f'STATUS CODE: {status}')
#     copy_btn = soup.select('#copyproduct')
    
#     designer = soup.select('#product-edit tbody tr td')
    
#     ##prduct-edit tbody tr td
#     title = soup.title.text
#     # if status == 200:
#     #   logger.info(f'Title: {title}   Button: {copy_btn}  De: {designer}')
  
def main():
  sys_sleep = None
  sys_sleep = WindowsInhibitor()
  logger.info('System inhibited')
  sys_sleep.inhibit()
  
  url = 'https://backgroundtown.com/Admin/Product/Edit/34'
  normal_product_url_info = 'https://backgroundtown.com/CA/Admin/StaticPDFProduct/Create'
  #start driver
  driver = init_driver()

  while True:
    try:
      url_login(driver, url)
      get_catgeory(driver)
      break
    except TimeoutException:
      # catch broken connection
      logger.critical("Timeout exception. No internet connection? "
      "Retrying...")
      sleep(10)
      continue
if __name__ == '__main__':
  
  main()
