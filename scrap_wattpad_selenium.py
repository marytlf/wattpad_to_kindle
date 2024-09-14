from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os
import requests

# User-Agent to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

session = requests.Session()
session.headers.update(headers)

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (optional)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set up the Chrome driver
#service = Service('/path/to/chromedriver')  # Replace with the path to your ChromeDriver
driver = webdriver.Chrome(options=chrome_options)

# Wattpad login credentials
username = ''  # Replace with your Wattpad username or email
password = ''  # Replace with your Wattpad password

# Wattpad login URL
login_url = 'https://www.wattpad.com/login'

# Open the login page
driver.get(login_url)

# Click the login button
login_email_bt = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[3]/div/div[2]/main/div/div/div/div/div/button")
login_email_bt.click()

# Wait for the username and password fields to be present
WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'username')))
WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'password')))

print("here1")
# Enter username
username_field = driver.find_element(By.NAME, 'username')
username_field.send_keys(username)

# Enter password
password_field = driver.find_element(By.NAME, 'password')
password_field.send_keys(password)

# Click the login button
login_button = driver.find_element(By.CSS_SELECTOR, ".footer-button-margin")
login_button.click()


def save_chapter(url):
    # URL of the Wattpad story
    story_url = url
    # Open the story page
    driver.get(story_url)

    # Scroll to load dynamically loaded pages
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break

        last_height = new_height

    # Get page source after fully loading the page
    html = driver.page_source

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Remove the element with class 'num-comment'
    for tag in soup.find_all(class_='num-comment'):
        tag.decompose()  # Remove the tag from the tree

    pre_tags = soup.find_all('pre',class_=lambda x: x != 'text-body-sm' and x != 'num-comment')

    return pre_tags


def get_all_chapters(url):
    # URL of the Wattpad story table of contents
    toc_url = url
    # Fetch the table of contents page
    toc_page = session.get(toc_url)
    soup = BeautifulSoup(toc_page.content, 'html.parser')


    works_name = soup.find(class_='story-info__title')
    print("works name :: "+str(works_name.get_text(strip=True)))

    author_name = soup.find(class_='author-info__username')
    print("author name :: "+str(author_name.get_text(strip=True)))

    works_author_dir_name = str(works_name.get_text(strip=True))+"_"+str(author_name.get_text(strip=True))
    print("--------------------:: "+str(works_author_dir_name))


    # Directory to save chapters
    os.makedirs(works_author_dir_name, exist_ok=True)

    # Find all chapter links in the table of contents
    chapter_links = soup.find_all('a', class_='story-parts__part')
    #print("chapter Links :: "+str(chapter_links))

    # Loop through each chapter link, get the content, and save it
    for index, link in enumerate(chapter_links):
        chapter_url = f"https://www.wattpad.com{link['href']}"
        print("URL :: "+str(chapter_url))
        pre_tags = save_chapter(chapter_url)
        #time.sleep(2)
        pre_text=""
        for index2,pre_tag in enumerate(pre_tags):
            #pre_text.append(pre_tag.get_text(separator="\n", strip=True))
            pre_text = pre_text + pre_tag.get_text(separator="\n", strip=True) + "\n"
        
        # Save to file
        with open(f'{works_author_dir_name}/chapter_{index + 1}.txt', 'w', encoding='utf-8') as file:
            file.write(str(pre_text))

        print(f'Saved: chapter_{index + 1}.txt')

    # Close the driver
    driver.quit()


url="<url>"
get_all_chapters(url)