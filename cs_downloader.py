import os
import time
import uuid
import typer
import sys

from bs4 import BeautifulSoup
from selenium import webdriver
from PyPDF2 import PdfFileMerger
from pydantic import BaseSettings
from webdriver_manager.chrome import ChromeDriverManager
import shutil 


class Settings(BaseSettings):
    USER_DATA_DIR: str = ''
    PROFILE_DIR: str = 'Default'
    DISABLE: bool = False

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


config = Settings()

#Copied from https://stackoverflow.com/a/58602365
def print_progress_bar(index, total, label):
    n_bar = 50  # Progress bar width
    progress = index / total
    sys.stdout.write('\r')
    sys.stdout.write(f"[{'=' * int(n_bar * progress):{n_bar}s}] {int(100 * progress)}%  {label}")
    sys.stdout.flush()


def main(url: str, filename: str):
    temp_path = os.path.join(os.getcwd(), 'temp', str(uuid.uuid4()))

    options = webdriver.ChromeOptions()
    if not (config.USER_DATA_DIR == '' or config.DISABLE):
        options.add_argument("user-data-dir=" + config.USER_DATA_DIR)
        options.add_argument("profile-directory=" + config.PROFILE_DIR)
    prefs = {
        "profile.default_content_settings.popups": 0,
        "download.default_directory": temp_path,
        "download.prompt_for_download": False
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)
    driver.get(url)

    html = driver.page_source

    if "Shibboleth" in html:
        input("Press enter when logged in")
        html = driver.page_source

    soup = BeautifulSoup(html, 'html.parser')
    print_list = soup.find(id="printList").find('ul')

    chapter_links = []

    for li in print_list.find_all('li'):
        a_tag = li.find('a')
        chapter_links.append(a_tag.attrs['href'])

    if not os.path.exists('temp'):
        os.mkdir('temp')
    os.mkdir(temp_path)

    l=len(chapter_links)

    for i, cl in enumerate(chapter_links,start=1):
        print_progress_bar(i,l,"Downloading Parts...")
        driver.get('https://content-select.com' + cl)

    print_progress_bar(l,l,"Waiting for Downloads to finish")
    while any(file.endswith('.crdownload') for file in os.listdir(temp_path)):
        time.sleep(0.1)
    #print_progress_bar(l,l,"Waiting for Downloads to finish")
    print_progress_bar(l,l,"Downloading Complete           ")
    driver.quit()

    merger = PdfFileMerger()

    files = sorted([os.path.join(temp_path, file) for file in os.listdir(temp_path)], key=lambda t: os.stat(t).st_mtime)

    print("")
    for i,file in enumerate(files,start=1):
        print_progress_bar(i,l,"Buidling PDF")
        merger.append(file)
    print("\nSaving... This may take a while.")
    merger.write(filename)
    merger.close()
    print("Finished. Removing temp files..")
    shutil.rmtree(temp_path)


if __name__ == "__main__":
    typer.run(main)
