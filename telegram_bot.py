from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
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
from fpdf import FPDF

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


# Define a function to send a file
def send_file(update, context, path_to_pdf):
    # Path to the file you want to send
    file_path = path_to_pdf

    # Send the file
    context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, 'rb'))


def txt_to_pdf(update, context, directory, output_pdf):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Loop through all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r') as file:
                pdf.multi_cell(0, 10, txt=f"--- {filename} ---")  # Optional: Add file name to PDF
                for line in file:
                    pdf.multi_cell(0, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'))

    # Output the single PDF
    pdf.output(output_pdf)
    send_file(update, context,"./"+output_pdf)


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


def get_all_chapters(url, update, context):
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

    update.message.reply_text("Wait while we download the chapters.")

    # Loop through each chapter link, get the content, and save it
    for index, link in enumerate(chapter_links):
        chapter_url = f"https://www.wattpad.com{link['href']}"
        print("URL :: "+str(chapter_url))
        pre_tags = save_chapter(chapter_url)
        #time.sleep(2)
        pre_text=""
        for index2,pre_tag in enumerate(pre_tags):
            pre_text = pre_text + pre_tag.get_text(separator="\n", strip=True) + "\n"
        
        # Save to file
        with open(f'{works_author_dir_name}/chapter_{index + 1}.txt', 'w', encoding='utf-8') as file:
            file.write(str(pre_text))

        print(f'Saved: chapter_{index + 1}.txt')
        update.message.reply_text(f'Saved: chapter_{index + 1}.txt')

    update.message.reply_text(f'Saved all chapters.')
    update.message.reply_text(f'We`re transforming all chapters in one PDF file, wait a minute...')
    txt_to_pdf(update, context, works_author_dir_name, works_author_dir_name+str(".pdf"))
    update.message.reply_text(f'File created.')
    
    # Close the driver
    driver.quit()


def login_wattpad(update, context):
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

    # Enter username
    username_field = driver.find_element(By.NAME, 'username')
    username_field.send_keys(username)

    # Enter password
    password_field = driver.find_element(By.NAME, 'password')
    password_field.send_keys(password)

    # Click the login button
    login_button = driver.find_element(By.CSS_SELECTOR, ".footer-button-margin")
    login_button.click()

    update.message.reply_text("Login succesfully.")


# Define the start command function
def start(update, context):
    update.message.reply_text("Hello! I'm a simple Telegram bot. How can I assist you?")
    update.message.reply_text("Hello! Wait a little bit, we`re logging in you on wattpad")
    
    login_wattpad(update, context)


# Define the echo function that repeats user messages
def echo(update, context):
    update.message.reply_text(update.message.text)
    #url="https://www.wattpad.com/story/294122158-control-dark-romance"
    get_all_chapters(update.message.text,update, context )


# Define a function for unknown commands
def unknown(update, context):
    update.message.reply_text("Sorry, I didn't understand that command.")

def main():
    # Your bot token
    TOKEN = ''

    # Create an updater object with the bot token
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register start command handler
    dp.add_handler(CommandHandler('start', start))

    # Register a handler for echoing text messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Handle unknown commands
    dp.add_handler(MessageHandler(Filters.command, unknown))

    # Start the bot
    updater.start_polling()

    
    # Run the bot until you stop it with Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
