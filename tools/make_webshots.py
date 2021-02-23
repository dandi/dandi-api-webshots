#!/usr/bin/env python3

import sys
import time

import yaml

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium import webdriver

from pathlib import Path


def get_dandisets():
    """Return a list of known dandisets"""
    from dandi.dandiapi import DandiAPIClient
    client = DandiAPIClient('https://api.dandiarchive.org/api')
    dandisets = client.get('/dandisets', parameters={'page_size': 10000})
    return sorted(x['identifier'] for x in dandisets['results'])


def process_dandiset(ds):
    driver = webdriver.Chrome()

    def wait_no_progressbar():
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "v-progress-circular")))

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
        ('', 'landing', wait_no_progressbar, None),
        # without login I cannot edit metadata, so let it not be used for now
        # (None, 'edit-metadata', None, click_edit),
        ('/draft/files', 'view-data', None, None)]:

        page_name = dspath / page

        t0 = time.monotonic()
        if urlsuf is not None:
            driver.get(f'https://gui-beta-dandiarchive-org.netlify.app/#/dandiset/{ds}{urlsuf}')
        if act:
            act()
        if wait:
            wait()
        times[page] = time.monotonic() - t0
        page_name.with_suffix('.html').write_text(driver.page_source)
        driver.save_screenshot(str(page_name.with_suffix('.png')))

    with (dspath / 'info.yaml').open('w') as f:
        yaml.safe_dump(info, f)

    driver.quit()
    # quick and dirty for now, although should just come from the above "structure"
    return f"""
### {ds}

| t={times['landing']:.2f} | t={times['view-data']:.2f} |
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
    for ds in dandisets:
        readme += process_dandiset(ds)

    if doreadme:
        Path('README.md').write_text(readme)

