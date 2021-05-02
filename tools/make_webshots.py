#!/usr/bin/env python3
from functools import partial
import os
from pathlib import Path
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import yaml

ARCHIVE_GUI = "https://gui-beta-dandiarchive-org.netlify.app"


def get_dandisets():
    """Return a list of known dandisets"""
    from dandi.dandiapi import DandiAPIClient
    client = DandiAPIClient('https://api.dandiarchive.org/api')
    dandisets = client.get('/dandisets', parameters={'page_size': 10000})
    return sorted(x['identifier'] for x in dandisets['results'])


def login(driver, username, password):

    driver.get("https://github.com/login")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.NAME, "commit")))
    try:
        driver.find_element_by_id("login_field").clear()
        driver.find_element_by_id("login_field").send_keys(username)
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys(password)
        driver.find_element_by_name("commit").click()
    except Exception:
        driver.save_screenshot("github-failure.png")
        raise
    else:
        driver.save_screenshot("github-logged.png")

    driver.get(ARCHIVE_GUI)
    wait_no_progressbar(driver, "v-progress-circular")
    try:
        login_el = driver.find_elements_by_class_name('mx-1').pop()
        login_el.click()
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "allow"))
            )
        except TimeoutException:
            pass
        else:
            element.click()
    except Exception:
        driver.save_screenshot("dandi-failure.png")
        raise
    else:
        driver.save_screenshot("dandi-logged.png")


def wait_no_progressbar(driver, cls):
    WebDriverWait(driver, 30).until(
        EC.invisibility_of_element_located((By.CLASS_NAME, cls)))


def process_dandiset(driver, ds):

    def click_edit():
        submit_button = driver.find_elements_by_xpath(
            '//*[@id="app"]/div/main/div/div/div/div/div[1]/div/div[2]/div[1]/div[3]/button[1]'
            )[0]
        submit_button.click()

    dspath = Path(ds)
    if not dspath.exists():
        dspath.mkdir(parents=True)

    info = {'times': {}}
    times = info['times']


    # TODO: do not do draft unless there is one
    # TODO: do for a released version
    for urlsuf, page, wait, act in [
        ('', 'landing', partial(wait_no_progressbar, driver, "v-progress-circular"), None),
        # without login I cannot edit metadata, so let it not be used for now
        # (None, 'edit-metadata', None, click_edit),
        ('/draft/files', 'view-data', partial(wait_no_progressbar, driver, "v-progress-linear"), None)]:

        page_name = dspath / page

        t0 = time.monotonic()
        if urlsuf is not None:
            driver.get(f'{ARCHIVE_GUI}/#/dandiset/{ds}{urlsuf}')
        if act:
            act()
        if wait:
            wait()
        times[page] = time.monotonic() - t0
        page_name.with_suffix('.html').write_text(driver.page_source)
        driver.save_screenshot(str(page_name.with_suffix('.png')))


    with (dspath / 'info.yaml').open('w') as f:
        yaml.safe_dump(info, f)

    # quick and dirty for now, although should just come from the above "structure"
    return f"""
### {ds}

| t={times['landing']:.2f} [Go to page]({ARCHIVE_GUI}/#/dandiset/{ds}) | t={times['view-data']:.2f} [Go to page]({ARCHIVE_GUI}/#/dandiset/{ds}/draft/files) |
| --- | --- |
| ![]({ds}/landing.png) | ![]({ds}/view-data.png) |

"""


if __name__ == '__main__':
    if len(sys.argv) > 1:
        dandisets = sys.argv[1:]
        doreadme = False
    else:
        dandisets = get_dandisets()
        doreadme = True

    readme = ''
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920, 1200")
    driver = webdriver.Chrome()
    # warm up
    login(driver, os.environ["DANDI_USERNAME"], os.environ["DANDI_PASSWORD"])
    for ds in dandisets:
        readme += process_dandiset(driver, ds)
    driver.quit()

    if doreadme:
        Path('README.md').write_text(readme)
