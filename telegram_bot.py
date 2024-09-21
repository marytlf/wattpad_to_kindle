from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from ebooklib import epub
import time
import os
import requests

from fpdf import FPDF

# Define conversation states
STATE_EXPECTING_URL = 1
STATE_EXPECTING_EMAIL = 2

sender_email = '<>@gmail.com'
sender_password = '<app pass>'  # or app password
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

# Function to read text file and format it for EPUB with HTML and CSS
def format_chapter_content(text):
    formatted_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 20px;
            }}
            h1 {{
                text-align: center;
                font-size: 2em;
                margin-bottom: 20px;
            }}
            p {{
                text-indent: 2em;
                margin-bottom: 1.5em;
            }}
            blockquote {{
                margin-left: 20px;
                font-style: italic;
                color: #555;
            }}
        </style>
    </head>
    <body>
        <h1>Chapter Title</h1>
        <p>{text}</p>
    </body>
    </html>
    """
    return formatted_content

# Convert BeautifulSoup Tag to string if it's a Tag object
def safe_get_text(tag):
    if isinstance(tag, str):
        return tag  # It's already a string
    else:
        return tag.get_text()  # Extract text if it's a BeautifulSoup Tag
    
def send_email_after_input(update, context):
    kindle_email = update.message.text  # Capture the Kindle email from user input
    pdf_file_path = context.user_data.get('pdf_file_path')
    epub_file_path = context.user_data.get('epub_file_path')

    if not kindle_email:
        update.message.reply_text(f"Kindle email not provided.")
        return

    if not pdf_file_path and epub_file_path:
        update.message.reply_text(f"No PDF file to send.")
        return

    # Example usage of sending email
    subject = "Your Wattpad Chapters PDF"
    body = 'Hello, here is your requested PDF!'
    attachment_file_path_pdf = pdf_file_path
    attachment_file_path_epub = epub_file_path

    send_email_to_kindle(sender_email, sender_password, kindle_email, subject, body, attachment_file_path_pdf)
    update.message.reply_text(f"PDF :: Email sent to {kindle_email} successfully.")
    send_email_to_kindle(sender_email, sender_password, kindle_email, subject, body, attachment_file_path_epub)
    update.message.reply_text(f"EPUB :: Email sent to {kindle_email} successfully.")

    # Close the driver
    driver.quit()

def send_email_to_kindle(sender_email, sender_password, kindle_email, subject, body, attachment_file_path=None):
    try:
        # Set up the server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()

        # Log in to the server
        server.login(sender_email, sender_password)

        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = kindle_email
        msg['Subject'] = subject

        # Attach the body text
        msg.attach(MIMEText(body, 'plain'))

        # Attach a file (e.g., .pdf, .mobi)
        if attachment_file_path:
            filename = os.path.basename(attachment_file_path)
            attachment = open(attachment_file_path, "rb")

            # Create the attachment
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')

            # Attach the file to the email
            msg.attach(part)
            attachment.close()

        # Send the email
        server.sendmail(sender_email, kindle_email, msg.as_string())
        
        # Close the connection
        server.quit()

        print("Email sent successfully to Kindle!")
    except Exception as e:
        print(f"Error: {e}")

# Define a function to send a file
def send_file(update, context, path_to_pdf):
    # Path to the file you want to send
    file_path = path_to_pdf

    # Send the file
    context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, 'rb'))

def create_epub_with_chapters(update, context, title, author, chapters, output_epub):
    # Create a new EPUB book
    book = epub.EpubBook()

    # Set metadata for the EPUB book
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)

    # List to store chapters (for table of contents and spine)
    epub_chapters = []

    # Loop through chapters and add them to the book
    for i, chapter_content in enumerate(chapters):

        chapter_content = safe_get_text(chapter_content)

        # Format the chapter content with HTML and CSS
        formatted_content = format_chapter_content(chapter_content)

        # Create a new chapter for each text in the list
        chapter_title = f'Chapter {i + 1}'
        chapter_file_name = f'chapter_{i + 1}.xhtml'
        chapter = epub.EpubHtml(title=chapter_title, file_name=chapter_file_name, lang='en')

        # Add chapter content (HTML format)
        #chapter.content = f'<h1>{chapter_title}</h1><p>{chapter_content}</p>'
        chapter.content = formatted_content

        # Add the chapter to the book
        book.add_item(chapter)

        # Add the chapter to the list for TOC and spine
        epub_chapters.append(chapter)

    # Define the table of contents (TOC)
    book.toc = tuple(epub_chapters)  # Automatically creates TOC with chapters

    # Define the spine (order of content)
    book.spine = ['nav'] + epub_chapters  # 'nav' is for the navigation page (Table of Contents)

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Write the EPUB file
    epub.write_epub(output_epub, book, {})

    print(f'EPUB file with multiple chapters created: {output_epub}')
    send_file(update, context, output_epub)


def txt_to_pdf(update, context, directory, output_pdf):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=16)

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

def get_chapters_from_directory(directory):
    chapters = []
    if not os.path.isdir(directory):
        return chapters
    
    for filename in sorted(os.listdir(directory)):  # Ensure files are in correct order
        if filename.endswith(".txt"):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:
                chapters.append(file.read())
    return chapters

def check_if_chapter_exist(directory,chapter_number):

    if not os.path.isdir(directory):
        return False

    if chapter_number in os.listdir(directory):
            return True
    return False

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

    chapters=get_chapters_from_directory(works_author_dir_name)

    #chapters=[]
    # Directory to save chapters
    os.makedirs(works_author_dir_name, exist_ok=True)

    # Find all chapter links in the table of contents
    chapter_links = soup.find_all('a', class_='story-parts__part')
    #print("chapter Links :: "+str(chapter_links))

    update.message.reply_text("Wait while we download the chapters.")

    # Loop through each chapter link, get the content, and save it
    for index, link in enumerate(chapter_links):
        if (not check_if_chapter_exist(works_author_dir_name,f'chapter_{index + 1}.txt')):
            chapter_url = f"https://www.wattpad.com{link['href']}"
            print("URL :: "+str(chapter_url))
            pre_tags = save_chapter(chapter_url)
            #time.sleep(2)
            pre_text=""
            for index2,pre_tag in enumerate(pre_tags):
                pre_text = pre_text + pre_tag.get_text(separator="\n", strip=True) +"\n\n"
                #pre_text = pre_text + pre_tag.get_text(strip=True) +"\n"
            # Save to file
            with open(f'{works_author_dir_name}/chapter_{index + 1}.txt', 'w', encoding='utf-8') as file:
                file.write(str(pre_text))
                #chapters.append(str(pre_text))
                print(f'Saved: chapter_{index + 1}.txt')
                update.message.reply_text(f'Saved: chapter_{index + 1}.txt')

    update.message.reply_text(f'Saved all chapters.')
    update.message.reply_text(f'We`re transforming all chapters in one PDF file, wait a minute...')
    txt_to_pdf(update, context, works_author_dir_name, works_author_dir_name+str(".pdf"))
    update.message.reply_text(f'File created.')
    update.message.reply_text(f'We`re transforming all chapters in one EPUB file, wait a minute...')
    create_epub_with_chapters(update, context, str(works_name.get_text(strip=True)), str(author_name.get_text(strip=True)), chapters, works_author_dir_name+str(".epub"))

    # Save the PDF file path in context.user_data
    context.user_data['pdf_file_path'] = works_author_dir_name+str(".pdf")
    context.user_data['epub_file_path'] = works_author_dir_name+str(".epub")

    # Set the state to expecting email
    context.user_data['state'] = STATE_EXPECTING_EMAIL

    # Now ask for the Kindle email
    update.message.reply_text(f'What is your Kindle email?')

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

    # Set the conversation state to expecting URL
    context.user_data['state'] = STATE_EXPECTING_URL



# Define the echo function that repeats user messages
def echo(update, context):
    # Get the current state from user data
    state = context.user_data.get('state')

    # Check if we're expecting a Wattpad URL
    if state == STATE_EXPECTING_URL:
        # Treat the input as a Wattpad URL and fetch chapters
        wattpad_url = update.message.text
        if not wattpad_url.startswith('http'):
            update.message.reply_text("Please provide a valid Wattpad URL.")
            return

        # Call the function to get all chapters
        get_all_chapters(wattpad_url, update, context)

    # Check if we're expecting a Kindle email
    elif state == STATE_EXPECTING_EMAIL:
        kindle_email = update.message.text
        if "@" not in kindle_email:
            update.message.reply_text("Please provide a valid email address.")
            return

        # Now send the email with the previously generated PDF
        send_email_after_input(update, context)

    else:
        update.message.reply_text("I'm not sure what you're asking for. Please send a valid command.")

# Define a function for unknown commands
def unknown(update, context):
    update.message.reply_text("Sorry, I didn't understand that command.")

def begin_again(update, context):
    STATE_EXPECTING_URL = 1
    STATE_EXPECTING_EMAIL = 2
    update.message.reply_text("Let`s download a new fic today. Send me the link...")

    login_wattpad(update, context)
    # Set the conversation state to expecting URL
    context.user_data['state'] = STATE_EXPECTING_URL


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
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, send_email_after_input))

    dp.add_handler(CommandHandler('begin_again', begin_again))

    # Handle unknown commands
    dp.add_handler(MessageHandler(Filters.command, unknown))

    # Start the bot
    updater.start_polling()

    
    # Run the bot until you stop it with Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
