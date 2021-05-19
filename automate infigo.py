from bs4 import BeautifulSoup as get_soup
import requests
from webdriver_manager.chrome import ChromeDriverManager #https://github.com/SergeyPirogov/webdriver_manager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.select import Select # good for options
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from multiprocessing import Pool # multiprocessing
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from credentials import Credentials
import re, os, logging
from time import sleep
from datetime import datetime
from scraper import file_manager
import json
import re
import threading
"""
Code adapted from "Project article by Michael Haephrati" alexa.py
** List comprehension example https://www.geeksforgeeks.org/python-list-comprehension/
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
logger = logging.getLogger("THISISNOTASITE")
formatter = logging.Formatter("%(asctime)s; %(levelname)s    %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
file_handler = logging.FileHandler(filename="bg-town product.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)

class WindowsInhibitor:
  ES_CONTINUOUS = 0x80000000
  ES_SYSTEM_REQUIRED = 0x00000001

  def __init__(self):
    pass

  def inhibit(self):
    import ctypes
    logger.info("Preventing Windows from going to sleep.")
    ctypes.windll.kernel32.SetThreadExecutionState(
      WindowsInhibitor.ES_CONTINUOUS | \
      WindowsInhibitor.ES_SYSTEM_REQUIRED)

  def uninhibit(self):
    import ctypes
    logger.info("Allowing Windows to go to sleep.")
    ctypes.windll.kernel32.SetThreadExecutionState(WindowsInhibitor.ES_CONTINUOUS)

def init_driver():
  logger.info("Starting chromedriver")
  chrome_options = Options()
  # use local data directory
  # headless mode can't be enabled since then amazon shows captcha
  # headless mode increases speed
  # chrome_options.add_argument('--headless')
  chrome_options.add_argument("user-data-dir=selenium")
  chrome_options.add_argument("start-maximized")
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
  """
  Takes in driver and a url

  """
  start = datetime.now()
  driver.implicitly_wait(5)
  logger.info(f"GET test 1 {url}")
  # get main page
  driver.get(url)
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
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'LoginEmail')))
    email_field = driver.find_element_by_id('LoginEmail')
    email_field.clear()
    # type email
    email_field.send_keys(Credentials.email)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'LoginPassword')))
    # find password field
    password_field = driver.find_element_by_id('LoginPassword')
    password_field.clear()
    # type password
    password_field.send_keys(Credentials.password)
    # find submit button, submit
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'loginbutton')))
    submit = driver.find_element_by_class_name('loginbutton')
    submit.click()
    logger.info(f'Login Successful, {datetime.now() - start}')

def open_json(file_name):
  
  with open(file_name, 'r+') as json_file:
    data = json.load(json_file)                                                                                                                                                               
  return data
  

def get_available_products(driver):
  start = datetime.now()
  product_object_dict = {}
  if os.path.isfile('bg-products.json'):
    logger.info(f'JSON FILE FOUND!')
  logger.info('Getting products and their IDs...')
  WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'ProductVariants')))
  product_selector = driver.find_elements_by_css_selector('#ProductVariants option')
  
  for web_element in product_selector:
    value = web_element.get_attribute('value') #get attribute value
    product_name = web_element.get_attribute('textContent') #get innerhtml text
    product_object = {
      'name': product_name
    }
    product_object_dict[value] = product_object
  logger.info(f'Done. Got list containing product objects. get_available_products(driver) took {datetime.now() - start}')

  return product_object_dict

def get_catgeory(driver,url, product_dict):
  start = datetime.now()
  url_login(driver, url)
  changes_made = False
  file_dict = open_json('bg-products.json')
  dirName = os.getcwd()
    
  for key, val in product_dict.items():
    try:
      if key not in file_dict:
        logger.info('FOUND PRODUCT ID NOT IN JSON FILE')
        logger.info(f'https://THISISNOTASITE.com/Admin/Product/Edit/{key}')
        driver.get(f'https://THISISNOTASITE.com/Admin/Product/Edit/{key}')
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit ul li')))

        category_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[3] # category tab
        category_tab_selector.click() #clicking ensures page is loaded enough to have entire category list, so it avoid issues discussed below about StaleElementReferenceException

        check_failed = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit-4 #productcategories-grid tbody tr td'))) 
        designer_selector = driver.find_elements_by_css_selector('#product-edit-4 #productcategories-grid tbody tr td') 
        #allows webdriver to wait for all elements, there was an issue where there would  only be 1 td loaded so indexing would not work to avoid StaleElementReferenceException
        
        for index in range(len(designer_selector)):
          # catch cases where designer is not first in the table
          category = designer_selector[index].get_attribute("textContent") #textContent is a better method, took care of "Themes >> Party Backdrops" special case
        #                                                                           https://blog.cloudboost.io/why-textcontent-is-better-than-innerhtml-and-innertext-9f8073eb9061
          if 'Designer >>' not in category and 'ACI Collection' not in category:
            continue
          else:
            category = re.sub('Designer >> ', '', category) 
            category = re.sub('ACI Collection', 'ACI', category)
            designer = category
        product_dict[key].update({'designer' : designer}) #combine dictionary
        file_dict[key] = product_dict[key]
        changes_made = True
        
      else: 
        continue
    except (KeyboardInterrupt, TimeoutException):
      fm = file_manager(dirName, '', 'bg-products.json', file_dict, 'w')
      fm.createFile()
      # driver.quit()
  if changes_made == True:
    # make changes to file, if changes is has been added
    fm = file_manager(dirName, '', 'bg-products.json', file_dict, 'w')
    fm.createFile()
    logger.info(f'Done. File has been updated in {dirName} get_category(driver, url, product_dict) took: {datetime.now()-start}')
    # driver.quit()
  else:
    logger.info(f'Done. No changes made to file in {dirName} get_category(driver, url, product_dict) took: {datetime.now()-start}')

    # driver.quit()

def check_production_folder():
  """
  Check \\\\\work\\production\\THISISNOTASITE images\\{designer} to see if files containing
    the same name exists.
  """
  now = datetime.now()
  product_dict = open_json('bg-products.json')
  production = '\\\\work\\production\\THISISNOTASITE images\\'
  marketing = '\\\\work\\marketing\\THISISNOTASITE\\backgrounds to add to the web\\'
  os.chdir(production)
  count = 0
  not_found = ''
  
  
  for key, value in product_dict.items():
    # logger.info(os.getcwd())
    cur_dir = os.chdir(f'{production}{value["designer"]}')
    prod_name = re.sub(' RubberMat Floor', '', value["name"])
    # prod_name = re.sub('[^(]+', ' ', page_title)
    # logger.info(f'Directory changed to {cur_dir}')
    if os.path.isfile(f'{prod_name}.jpg'):
      # logger.info(f'Product image found! {os.getcwd()}\\{prod_name}.jpg')
      # logger.info(f'Found these files in Production folder {key}: {value}')
      count += 1
    elif os.path.isfile(f'{marketing}{value["designer"]}\\{prod_name}.jpg'):
      # logger.info(f'Found these files in Designer folder instead {key}: {value}')
      count += 1
    else:
      not_found += f'{key}: {value}\n'
      # if value['designer'].lower() == 'Molly Long'.lower():
      #   logger.info(value['name'])
  logger.info(f'Total files found => {count}/{len(product_dict)} \t\t Files missing: {len(product_dict) - count}\t\t {datetime.now() - now} seconds')
  os.chdir('C:\\Users\\h.feahn\\Documents\\Machine Learning\\novel collector')
  with open('failed prod.txt', 'w') as file:
    file.write(not_found)
  # return ['50','53', '59', '1103', '2102']
  return ['53']

def convert_to_img_buggy(driver, url, product_list):
  """
  1. Update Specification Attribute tab then click "add attribute"
  2. Reference DP2 Products in Product Variants tab
  """
  # main_window_handle = None

  combination_fail_list = []
  exit_case = True


  product_dict = open_json('dp2 product reference.json')


  try:
    for id in product_list:
      logger.info(f'TRY  {url}{id}')
      driver.get(f'{url}{id}')

      WebDriverWait(driver, 30).until(  EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#product-edit ul li')))

      product_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[0]
      variants_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[2]
      category_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[3] # category tab
      pictures_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[6]
      specification_tab_selector = driver.find_elements_by_css_selector('#product-edit ul li')[7]
      
      specification_tab_selector.click() #clicking ensures page is loaded enough to have entire category list, so it avoid issues discussed below about StaleElementReferenceException
      check_failed = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'specificationattributes-grid'))) 
      attribute_table_selector = driver.find_element_by_css_selector('#product-edit-8 #specificationattributes-grid tbody tr td') 
      if 'no records' in attribute_table_selector.get_attribute('textContent').lower():
        logger.info('No Specification Attribute set yet')
        hide_from_selector = driver.find_element_by_id('AddSpecificationAttributeModel_HideFromCustomer')
        hide_from_selector.click()
        add_attribute_button_selector = driver.find_element_by_css_selector('#product-edit-8 .adminContent button#addProductSpec')
         # assuming it is not checked
        add_attribute_button_selector.click()
      else:
        logger.info('Specification attribute already exits')
        
      # Product Variants Tab
      variants_tab_selector.click()
      check_failed = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#product-variants tbody tr td.t-last'))) 
      add_attribute_button_selector = driver.find_element_by_css_selector('#product-variants tbody tr td.t-last a.button')
      add_attribute_button_selector.click()

      add_combinations(driver, url, product_dict, combination_fail_list)
  except KeyboardInterrupt:
    driver.quit()

def add_combinations(driver, url, product_dict, combination_fail_list):
  check_failed = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#productvariant-edit ul li')))
  product_sku_selector = driver.find_element_by_id('Sku')
  logger.info(f'SKU ELEMENT VALUE {product_sku_selector.get_attribute("value")}')
  if product_sku_selector.get_attribute('value') == '27111114':
    """ Still need to find a way to pass a new value in for the else statement """
    variants_attributes_tab_selector = driver.find_elements_by_css_selector('#productvariant-edit ul li a')[2]
    variants_attributes_tab_selector.click()

    available_size_selector = driver.find_elements_by_css_selector('.table-wrapper td a')[0] # assumes first row contains canvasSize
    available_size = available_size_selector.get_attribute('textContent')
    size = int(re.sub('[^0-9]','', available_size))
    logger.info(f'AVAILABLE SIZES FOUND {size}')

    variants_attributes_combin_selector = driver.find_elements_by_css_selector('#productattribute-edit ul li a')[1]
    variants_attributes_combin_selector.click()
  else:
    logger.info(f'SKU NOT 27111114 ELEMENT VALUE {product_sku_selector.get_attribute("value")}')

  for rows in range(size): # probably a slow way to do this
    foo = driver.find_elements_by_css_selector('#attributecombinations-grid tbody tr') #good to check within this loop to avoid staleelement or missing element from happening at random times
    WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#attributecombinations-grid tbody tr td')))
    variants_attributes_selector = driver.find_element_by_css_selector('#attributecombinations-grid tbody tr')
    html = driver.page_source
    soup = get_soup(html, 'html.parser')
    # logger.info(soup.prettify)
    test = soup.select('#attributecombinations-grid tbody tr td')

    logger.info('this is the loop with html')
    test2 = [name for name in test]
    # logger.info(f'ROW LENGTH [{test2}')
    try:
      dp2_sku = foo[rows].find_elements_by_tag_name('td')[3].get_attribute('textContent') # Check sku name
    except (IndexError, StaleElementReferenceException):
      dp2_sku = False
    try:
      first_row = variants_attributes_selector.find_element_by_tag_name('td').get_attribute('textContent')
    except StaleElementReferenceException:
      logger.info(f'StaleElementReferenceException: First_row no longer only has one element')
      first_row = ''
    

    if 'no records to display' in first_row.lower() or len(foo) < size: 
      # Second condition to check if more combination needs to be added
      # add new attributes
      logger.info('No attribute combination found.... Adding')
      variants_button_selector = driver.find_element_by_id('btnAddNewCombination')
      main_window_handle = driver.window_handles # number of windows should be 1
      logger.info(f'Current Window handle {main_window_handle}')
      variants_button_selector.click()
      
      wait_for_window(driver, main_window_handle, variants_button_selector,  url, product_dict, combination_fail_list)
      
      """
        Issue presents itself as a new popup window is opened selenium needs to be told to switch to it to find the necessary elemnets and change dropdown options
        Consider making this section a class with methods such as has_attributes, attribute_count
        https://stackoverflow.com/questions/17676036/python-webdriver-to-handle-pop-up-browser-windows-which-is-not-an-alert

        To resolve issues with original window not being found when switching back to it
        https://stackoverflow.com/questions/51775122/nosuchwindowexception-no-such-window-window-was-already-closed-while-switchi

        ***************** Above url had issues where if a window did not open after the button was clicked, and infinite loop would occur, here is a better implementation
        https://stackoverflow.com/questions/41571217/python-3-5-selenium-how-to-handle-a-new-window-and-wait-until-it-is-fully-lo
      """
      
      logger.critical(f'switching to new window 1, popup window has been set back to none  {driver.window_handles}')
      
      WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.ID, 'add-attribute-combination')))
      logger.info('combination button found')

      variant_popup_window_size_drop_selector = driver.find_element_by_css_selector('select.select-element')
      combination_popup_window_button = driver.find_element_by_id('add-attribute-combination')
      dp2_sku_selector = driver.find_element_by_id('Sku') # sku field
      
      logger.info('waiting for add combination button')
      select = Select(variant_popup_window_size_drop_selector) # instantiate class
      logger.info(f'Total sizes available to add => {len(select.options)}')
      select.select_by_index(rows) # select which size
      selected_size = select.options[rows].get_attribute("textContent")
      selected_size = re.sub('["]', '', selected_size)
      logger.info(f'size option {rows} {selected_size}')
      
      if selected_size in product_dict:
        logger.info(f'Select {selected_size} = {product_dict[selected_size]}')
        dp2_sku_selector.send_keys(product_dict[selected_size])
      else:
        logger.critical(f'Size not in dictionary: {selected_size}')
        # break
      combination_popup_window_button.click() # add once done
      
      driver.switch_to_window(main_window_handle[0])
      # driver.window_handles
    elif len(foo) > size:
      logger.critical(f'TOO MANY COMBINATIONS {url}')
      combination_fail_list.append(url)
      continue
    # elif len(dp2_sku) <= 1:
    elif dp2_sku != False and len(dp2_sku) <= 1:
      
      try:
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#attributecombinations-grid tbody tr td input')))
        size_attribute = foo[rows].find_elements_by_tag_name('td')[0].get_attribute('textContent')
        dp2_sku = foo[rows].find_elements_by_tag_name('td')[3].get_attribute('textContent') # Check sku name
    
        attribute_edit = foo[rows].find_element_by_css_selector('td input') # Check sku name
      except StaleElementReferenceException:
        logger.critical('stale element exception occurred for combination edit button refreshing page starting recursion')
        driver.refresh()
        add_combinations(driver, url, product_dict, combination_fail_list)
      size_attribute = re.sub('Canvas: ', '', size_attribute)
      size_attribute = re.sub('CanvasSize: ', '', size_attribute)
      main_window_handle = driver.window_handles
      if len(dp2_sku) <= 1:
        logger.info(f'SKU is missing  before button clicked windows{driver.window_handles}')
        # if len(main_window_handle) > 1:
        #   logger.critical('TOO MANY WINDOWS EXISTS BEFORE CHANGES')
        #   main_window_handle.pop[-1]
        try:
          attribute_edit.click() #send button to  wait_for_window() in case popup window was not triggered
        except StaleElementReferenceException:
          logger.critical('stale element exception occurred for dshfbsdlfdsfhdf refreshing page starting recursion')
          driver.refresh()
          add_combinations(driver, url, product_dict, combination_fail_list)
        wait_for_window(driver, main_window_handle, attribute_edit, url, product_dict, combination_fail_list)

        logger.info('switching to new window 2nd')
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.ID, 'update-attribute-combination')))
        dp2_sku_selector = driver.find_element_by_id('Sku') # sku field

        update_popup_window_button = driver.find_element_by_id('update-attribute-combination')
        
        size_attribute = re.sub('["]', '', size_attribute)
        # strip out characters
        if 'RubberMat' in size_attribute:
          size_attribute = re.sub('Canvas: ', '', size_attribute)
          size_attribute = re.sub('CanvasSize: ', '', size_attribute)
          size_attribute = re.sub('[?<=F].*', '', size_attribute) # gets rid of everything after the letter F so Flooring
          size_attribute = re.sub(' $', '', size_attribute) # gets rid of empty last character

        else:
          size_attribute = re.sub('Canvas: ', '', size_attribute)
          size_attribute = re.sub('CanvasSize: ', '', size_attribute)
          size_attribute = re.sub('[?<=M].*', '', size_attribute) # gets rid of everything after the letter M

          #Ex: "CanvasSize: 8'x6' UltraClothMentor Collection: 82100832"
        if size_attribute in product_dict:
          logger.info(f'Select {size_attribute} = {product_dict[size_attribute]}')
          dp2_sku_selector.send_keys(product_dict[size_attribute])
        else:
          logger.critical(f'Size: {size_attribute} not in dictionary')
        update_popup_window_button.click() # add once done
        driver.switch_to_window(main_window_handle[0])
          
          # Selecting dropdown options https://stackoverflow.com/questions/7867537/how-to-select-a-drop-down-menu-value-with-selenium-using-python
      else:
        logger.critical('made it to final else')
        break
    else:
      logger.critical(f'made it to else statement for combinations {foo[rows].find_elements_by_tag_name("td")[0].get_attribute("textContent")}')

    """
      Page for adding new sizes
      # Get product sizes
      variant_attributes_selector = driver.find_element_by_css_selector('#productvariantattributes-grid tbody tr td a')
      variant_attributes_selector.click()

      check_failed = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#productvariantattribute-form .table-wrapper tbody tr')))
      variant_size_selector = driver.find_elements_by_css_selector('#productvariantattribute-form .table-wrapper tbody tr')
      variant_size_selector = driver.find_elements_by_css_selector('#productvariantattribute-form .table-wrapper tbody tr')

      size_list = []
      for size_row in variant_size_selector:
        
        # if size_row.get_attribute('textContent') == 'No records to display.':
        #   logger.info(f'Variant Sizes: {size_row.get_attribute("textContent")}')
        sleep(2) #try to wait for fields to be populated
        product_size = size_row.find_elements_by_tag_name('td')[0].get_attribute('textContent')
        size_list.append(product_size)
      logger.info(size_list)
    """ 
  logger.info('DONE WITH TEST CASE')
def wait_for_window(driver, main_window_handle, button,  url, product_dict, combination_fail_list):
  """
  waits for popup windows
  needs button that will create a second window when clicked
  """
  logger.info(f'main window {main_window_handle}  total windows {driver.window_handles}')
  # WebDriverWait(driver, 3).until(EC.number_of_windows_to_be(2)) # wait until number of windows is 2
  if len(driver.window_handles) < 2: 
    logger.critical('second window did not open, trying again')
    try:
      button.click() #try to open button again
    except StaleElementReferenceException:
      logger.critical('ABSOLUTE CRITICAL!!!! REFRESHING PAGE AND STARTING OVER')
      driver.refresh()
      add_combinations(driver, url, product_dict, combination_fail_list)
    logger.info('button clicked')
    WebDriverWait(driver, 3).until(EC.number_of_windows_to_be(2)) 
    logger.info(f'finally worked, sdfhsdlfsdflsdf {driver.window_handles}')
  logger.info(f'second window found {driver.window_handles}')
  try:
    new_window = [window for window in driver.window_handles if window != main_window_handle]
    logger.info(f'new windows available {new_window}')
    new_window = new_window[1]
  except IndexError:
    logger.critical('Index error for new window exists in wait_for_window() only 1 option available in list, however it is the new window\n switching to index 0')
    new_window = [window for window in driver.window_handles if window != main_window_handle]
    logger.info(f'new windows available {new_window}')
    new_window = new_window[0]
  logger.info(f'going to switch to new window {new_window}')
  driver.switch_to.window(new_window)

def main():
  start_time = datetime.now()
  sys_sleep = None
  sys_sleep = WindowsInhibitor()
  logger.info('System inhibited')
  sys_sleep.inhibit()
  
  url = 'https://THISISNOTASITE.com/Admin/Product/Edit/50'
  normal_product_url_info = 'https://THISISNOTASITE.com/CA/Admin/StaticPDFProduct/Create'
  #start driver
  driver = init_driver()
  
  while True:
    try:
      url_login(driver, normal_product_url_info)
      # first function following url does not need a url
      product_dict = get_available_products(driver) 
      get_catgeory(driver, url, product_dict)
      products_list = check_production_folder()
      convert_to_img_buggy(driver, f'https://THISISNOTASITE.com/Admin/Product/Edit/',products_list)
      # thread = threading.Thread(target = check_production_folder)
      # thread.start()
      # thread.join()
      break
    except TimeoutException:
      # catch broken connection
      logger.critical("Timeout exception. No internet connection? "
      "Retrying...")
      sleep(10)
      continue
  logger.info(f'Program duration: {datetime.now() - start_time}')
if __name__ == '__main__':
  
  main()
